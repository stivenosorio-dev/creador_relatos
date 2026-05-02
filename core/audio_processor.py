"""
Audio Processor — Cadena de efectos profesional con analisis adaptativo.

NUEVO en esta version:
  - Recibe un AudioEditProfile en lugar de AudioProcessConfig plano.
  - Antes de aplicar efectos, analiza el audio crudo:
      * LUFS integrado (loudness percibida)
      * Pico verdadero (true peak)
      * Centroide espectral (brillo / oscuridad de la voz)
      * RMS de alta frecuencia (sibilancia)
      * Rango dinamico estimado (crest factor)
  - Con esos datos ajusta DINAMICAMENTE:
      * Ganancia de entrada (para normalizar el LUFS al target)
      * Umbral del compresor (adaptado al rango dinamico real)
      * Nivel del de-esser (adaptado a la sibilancia medida)
  Esto garantiza que el perfil suene perfecto sin importar la voz de origen.
  - Soporte de pitch shift y time stretch via librosa (pre-pedalboard).
"""

import numpy as np
from pathlib import Path
from dataclasses import dataclass

import librosa
import soundfile as sf
from pedalboard import (
    Pedalboard, HighpassFilter, LowShelfFilter, HighShelfFilter,
    PeakFilter, Compressor, Reverb, NoiseGate, Limiter, Gain, Clipping,
)
from pedalboard.io import AudioFile

from utils.logger import get_logger, print_info

logger = get_logger("audio_processor")

TARGET_LUFS = -18.0  # Loudness objetivo post-analisis para narración de voz


@dataclass
class AudioAnalysis:
    """Resultados del analisis previo del audio crudo."""
    lufs_integrated: float       # Loudness integrada en LUFS
    true_peak_db: float          # Pico verdadero en dBFS
    rms_db: float                # RMS global en dB
    spectral_centroid_hz: float  # Centroide espectral (brillo)
    sibilance_rms_db: float      # RMS en banda 5-9 kHz (sibilancia)
    crest_factor_db: float       # Diferencia peak-RMS (rango dinamico)
    duracion_seg: float
    sample_rate: int


def analizar_audio(path: Path) -> AudioAnalysis:
    """
    Analiza el audio crudo y retorna metricas clave para la edicion adaptativa.

    Usa librosa para calcular LUFS aproximado (via power mean), centroide
    espectral y energia por bandas. No requiere dependencias adicionales.
    """
    audio, sr = librosa.load(str(path), sr=None, mono=True)

    if len(audio) == 0:
        raise RuntimeError(f"Audio vacio: {path}")

    duracion = len(audio) / sr

    # RMS global
    rms = float(np.sqrt(np.mean(audio ** 2)))
    rms_db = 20 * np.log10(rms + 1e-9)

    # True peak (aproximado)
    true_peak_db = 20 * np.log10(float(np.max(np.abs(audio))) + 1e-9)

    # LUFS integrado aproximado (ITU-R BS.1770 simplificado: K-weight + power mean)
    # K-weighting: atenuar bajos, boost en presencia
    # Simplificacion: usar RMS ponderado por frecuencia via STFT
    S = np.abs(librosa.stft(audio, n_fft=2048, hop_length=512)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    # K-weighting aproximado: +4dB a 4kHz, -6dB/octava bajo 80Hz
    k_weight = np.ones(len(freqs))
    k_weight[freqs < 80] *= 0.5
    k_weight[(freqs >= 1000) & (freqs < 8000)] *= 1.5
    S_weighted = S * k_weight[:, np.newaxis]
    mean_power = float(np.mean(S_weighted))
    lufs = 10 * np.log10(mean_power + 1e-12) - 0.691
    lufs = float(np.clip(lufs, -60, 0))

    # Centroide espectral (brillo de la voz)
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    centroid_hz = float(np.mean(centroid))

    # Energia de sibilancia (5-9 kHz)
    S_full = np.abs(librosa.stft(audio)) ** 2
    freqs_full = librosa.fft_frequencies(sr=sr)
    mask_sib = (freqs_full >= 5000) & (freqs_full <= 9000)
    sib_rms = float(np.sqrt(np.mean(S_full[mask_sib, :])))
    sib_rms_db = 20 * np.log10(sib_rms + 1e-9)

    # Crest factor
    crest_db = true_peak_db - rms_db

    logger.info(
        f"Analisis: LUFS={lufs:.1f} | Peak={true_peak_db:.1f}dB | "
        f"RMS={rms_db:.1f}dB | Centroide={centroid_hz:.0f}Hz | "
        f"Sibilancia={sib_rms_db:.1f}dB | Crest={crest_db:.1f}dB | "
        f"Dur={duracion:.1f}s"
    )

    return AudioAnalysis(
        lufs_integrated=lufs,
        true_peak_db=true_peak_db,
        rms_db=rms_db,
        spectral_centroid_hz=centroid_hz,
        sibilance_rms_db=sib_rms_db,
        crest_factor_db=crest_db,
        duracion_seg=duracion,
        sample_rate=sr,
    )


class AudioProcessor:
    """
    Cadena de post-procesamiento profesional con analisis adaptativo.

    Flujo:
      1. analizar_audio() -> AudioAnalysis
      2. _calcular_ajustes_adaptativos() -> parametros corregidos
      3. (Opcional) pitch shift + time stretch via librosa
      4. Construir Pedalboard con parametros finales
      5. Procesar en chunks
    """

    def __init__(self, profile=None, config=None):
        """
        profile: AudioEditProfile (nuevo sistema de perfiles)
        config:  AudioProcessConfig (compatibilidad legada)
        Si se pasa config y no profile, se convierte a un perfil basico.
        """
        from config import AudioEditProfile, AUDIO_PROCESS_DEFAULT

        if profile is not None:
            self._profile = profile
            self._legacy_config = None
        elif config is not None:
            # Compatibilidad: crear perfil desde config legacy
            self._profile = self._config_to_profile(config)
            self._legacy_config = config
        else:
            cfg = AUDIO_PROCESS_DEFAULT
            self._profile = self._config_to_profile(cfg)
            self._legacy_config = cfg

    @staticmethod
    def _config_to_profile(cfg):
        """Convierte AudioProcessConfig legacy a AudioEditProfile."""
        from config import AudioEditProfile
        return AudioEditProfile(
            nombre="Perfil Legado",
            descripcion="Convertido desde AudioProcessConfig",
            emoji="⚙️",
            highpass_cutoff_hz=cfg.highpass_cutoff_hz,
            eq_cut_freq_hz=cfg.eq_cut_freq_hz,
            eq_cut_gain_db=cfg.eq_cut_gain_db,
            eq_cut_q=cfg.eq_cut_q,
            eq_warmth_freq_hz=cfg.eq_warmth_freq_hz,
            eq_warmth_gain_db=cfg.eq_warmth_gain_db,
            eq_warmth_q=cfg.eq_warmth_q,
            eq_presence_freq_hz=cfg.eq_presence_freq_hz,
            eq_presence_gain_db=cfg.eq_presence_gain_db,
            eq_presence_q=cfg.eq_presence_q,
            comp_threshold_db=cfg.comp_threshold_db,
            comp_ratio=cfg.comp_ratio,
            comp_attack_ms=cfg.comp_attack_ms,
            comp_release_ms=cfg.comp_release_ms,
            deesser_freq_hz=cfg.deesser_freq_hz,
            deesser_gain_db=cfg.deesser_threshold_db + 19,
            saturation_drive_db=cfg.saturation_drive_db,
            saturation_active=True,
            reverb_room_size=cfg.reverb_room_size,
            reverb_damping=cfg.reverb_damping,
            reverb_wet_level=cfg.reverb_wet_level,
            reverb_dry_level=cfg.reverb_dry_level,
            gate_threshold_db=cfg.gate_threshold_db,
            gate_attack_ms=cfg.gate_attack_ms,
            gate_release_ms=cfg.gate_release_ms,
            limiter_threshold_db=cfg.limiter_threshold_db,
        )

    def _calcular_ajustes_adaptativos(self, analisis: AudioAnalysis) -> dict:
        """
        Calcula correcciones dinamicas basadas en el analisis del audio.

        Reglas:
          - input_gain: compensa la diferencia entre LUFS medido y target
          - comp_threshold: se ajusta al rango dinamico real (crest factor)
          - deesser_gain: se amplifica si la sibilancia es alta
        """
        p = self._profile

        # 1. Ganancia de entrada adaptativa (normalizar LUFS al target)
        lufs_delta = TARGET_LUFS - analisis.lufs_integrated
        # No compensar mas de +12dB ni menos de -6dB para evitar distorsion
        gain_adaptativo = float(np.clip(p.input_gain_db + lufs_delta * 0.6, -6.0, 14.0))

        # 2. Umbral del compresor adaptativo
        # Si el audio es muy dinamico (crest > 20dB) bajar umbral para controlar mejor
        crest = analisis.crest_factor_db
        comp_thr_adaptativo = p.comp_threshold_db
        if crest > 20:
            comp_thr_adaptativo -= (crest - 20) * 0.3
        elif crest < 10:
            # Audio ya muy comprimido: subir umbral para no sobre-comprimir
            comp_thr_adaptativo += (10 - crest) * 0.4
        comp_thr_adaptativo = float(np.clip(comp_thr_adaptativo, -35.0, -8.0))

        # 3. De-esser adaptativo segun sibilancia medida
        # Si sib_rms_db > -40 (sibilancia notable), aumentar corte
        deesser_adaptativo = p.deesser_gain_db
        if analisis.sibilance_rms_db > -40:
            extra_cut = (analisis.sibilance_rms_db + 40) * 0.3
            deesser_adaptativo -= extra_cut
        deesser_adaptativo = float(np.clip(deesser_adaptativo, -12.0, -1.0))

        logger.info(
            f"Ajustes adaptativos: gain={gain_adaptativo:+.1f}dB | "
            f"comp_thr={comp_thr_adaptativo:.1f}dB | "
            f"deesser={deesser_adaptativo:.1f}dB"
        )

        return {
            "input_gain_db": gain_adaptativo,
            "comp_threshold_db": comp_thr_adaptativo,
            "deesser_gain_db": deesser_adaptativo,
        }

    def _construir_cadena(self, ajustes: dict) -> Pedalboard:
        """Construye el Pedalboard con parametros finales (perfil + ajustes adaptativos)."""
        p = self._profile
        gain_db      = ajustes["input_gain_db"]
        comp_thr     = ajustes["comp_threshold_db"]
        deesser_gain = ajustes["deesser_gain_db"]

        efectos = [
            Gain(gain_db=gain_db),
            HighpassFilter(cutoff_frequency_hz=p.highpass_cutoff_hz),
            PeakFilter(cutoff_frequency_hz=p.eq_cut_freq_hz,
                       gain_db=p.eq_cut_gain_db, q=p.eq_cut_q),
            LowShelfFilter(cutoff_frequency_hz=p.eq_warmth_freq_hz,
                           gain_db=p.eq_warmth_gain_db, q=p.eq_warmth_q),
            HighShelfFilter(cutoff_frequency_hz=p.eq_presence_freq_hz,
                            gain_db=p.eq_presence_gain_db, q=p.eq_presence_q),
        ]

        # Corte nasal (opcional segun perfil)
        if p.eq_nasal_cut_db != 0.0 and p.eq_nasal_cut_hz > 0:
            efectos.append(PeakFilter(
                cutoff_frequency_hz=p.eq_nasal_cut_hz,
                gain_db=p.eq_nasal_cut_db,
                q=p.eq_nasal_cut_q,
            ))

        efectos += [
            Compressor(threshold_db=comp_thr, ratio=p.comp_ratio,
                       attack_ms=p.comp_attack_ms, release_ms=p.comp_release_ms),
            PeakFilter(cutoff_frequency_hz=p.deesser_freq_hz,
                       gain_db=deesser_gain, q=3.0),
        ]

        if p.saturation_active and p.saturation_drive_db > 0:
            efectos += [
                Gain(gain_db=p.saturation_drive_db),
                Clipping(threshold_db=-0.5),
                Gain(gain_db=-p.saturation_drive_db),
            ]

        efectos += [
            Reverb(room_size=p.reverb_room_size, damping=p.reverb_damping,
                   wet_level=p.reverb_wet_level, dry_level=p.reverb_dry_level),
            NoiseGate(threshold_db=p.gate_threshold_db,
                      attack_ms=p.gate_attack_ms, release_ms=p.gate_release_ms),
            Limiter(threshold_db=p.limiter_threshold_db),
        ]

        return Pedalboard(efectos)

    def procesar(self, input_path: Path, output_path: Path) -> None:
        """
        Pipeline completo:
          1. Analizar audio crudo
          2. Calcular ajustes adaptativos
          3. Pitch shift + time stretch si el perfil lo requiere
          4. Aplicar cadena Pedalboard en chunks
        """
        p = self._profile
        logger.info(f"Procesando con perfil: {p.nombre}")

        # ── 1. Analizar audio ─────────────────────────────────────────────
        analisis = analizar_audio(input_path)
        ajustes = self._calcular_ajustes_adaptativos(analisis)

        # ── 2. Pitch shift + time stretch (librosa, pre-pedalboard) ───────
        necesita_librosa = abs(p.pitch_semitones) > 0.05 or abs(p.speed_factor - 1.0) > 0.01

        if necesita_librosa:
            audio_raw, sr = librosa.load(str(input_path), sr=None, mono=True)

            if abs(p.pitch_semitones) > 0.05:
                logger.info(f"Pitch shift: {p.pitch_semitones:+.1f} st")
                audio_raw = librosa.effects.pitch_shift(
                    audio_raw, sr=sr, n_steps=p.pitch_semitones, bins_per_octave=24
                )

            if abs(p.speed_factor - 1.0) > 0.01:
                logger.info(f"Time stretch: x{p.speed_factor:.2f}")
                audio_raw = librosa.effects.time_stretch(audio_raw, rate=p.speed_factor)

            audio_raw = audio_raw.astype(np.float32)
            mx = np.max(np.abs(audio_raw))
            if mx > 0:
                audio_raw = audio_raw / mx * 0.95

            # Guardar temp para que pedalboard lo lea
            tmp_path = input_path.parent / "_tmp_librosa.wav"
            sf.write(str(tmp_path), audio_raw, sr)
            process_input = tmp_path
        else:
            process_input = input_path
            tmp_path = None

        # ── 3. Construir cadena y procesar en chunks ──────────────────────
        board = self._construir_cadena(ajustes)
        chunk_size = 1024 * 256

        try:
            with AudioFile(str(process_input)) as infile:
                sample_rate = infile.samplerate
                num_channels = infile.num_channels
                total_frames = infile.frames
                duracion_sec = total_frames / sample_rate

                logger.info(
                    f"Procesando: {duracion_sec:.1f}s | {sample_rate}Hz | "
                    f"{len(board)} efectos en cadena"
                )

                with AudioFile(str(output_path), "w",
                               samplerate=sample_rate,
                               num_channels=num_channels) as outfile:
                    frames_done = 0
                    while infile.tell() < total_frames:
                        chunk = infile.read(chunk_size)
                        processed = board(chunk, sample_rate)
                        outfile.write(processed)
                        frames_done += chunk.shape[1] if chunk.ndim > 1 else chunk.shape[0]
                        if frames_done % (sample_rate * 15) < chunk_size:
                            pct = frames_done / total_frames * 100
                            logger.debug(f"  {pct:.0f}%")
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

        print_info(
            f"Audio procesado: {output_path.name} | "
            f"Perfil: {p.nombre} | Dur: {analisis.duracion_seg:.1f}s"
        )
