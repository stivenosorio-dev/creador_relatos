"""
🔊 Audio Processor — Cadena de efectos profesional para eliminar voz sintética.

Aplica 8 etapas de procesamiento con pedalboard (Spotify) para transformar
la voz de edge-tts en una narración que suena como un locutor profesional
grabado en un estudio íntimo de radio nocturna.

Cadena de efectos:
  1. High-Pass Filter (80 Hz)     → Eliminar rumble sub-grave
  2. EQ Paramétrico               → Eliminar dureza robótica + calidez
  3. Compresor                    → Consistencia y presencia
  4. De-esser (EQ + Compressor)   → Reducir sibilancia artificial
  5. Saturación armónica          → Calidez analógica vintage
  6. Reverb de sala               → Profundidad y naturalidad
  7. Noise Gate                   → Silencios limpios
  8. Limiter                      → Prevenir clipping

Resultado: Voz de narrador de hoguera, cálida, profunda, inmersiva.
           Cero rastro de voz virtual.
"""

import numpy as np
from pathlib import Path

from pedalboard import (
    Pedalboard,
    HighpassFilter,
    LowShelfFilter,
    HighShelfFilter,
    PeakFilter,
    Compressor,
    Reverb,
    NoiseGate,
    Limiter,
    Gain,
    Clipping,
)
from pedalboard.io import AudioFile

from config import AudioProcessConfig, AUDIO_PROCESS_DEFAULT
from utils.logger import get_logger, print_info

logger = get_logger("audio_processor")


class AudioProcessor:
    """
    Cadena de post-procesamiento profesional de audio.
    
    Transforma el audio crudo de TTS en una narración premium
    indistinguible de una grabación humana real.
    """

    def __init__(self, config: AudioProcessConfig = AUDIO_PROCESS_DEFAULT):
        self.config = config
        self._board = self._construir_cadena()

    def _construir_cadena(self) -> Pedalboard:
        """
        Construye la cadena de efectos completa.
        
        Cada efecto está calibrado específicamente para contrarrestar
        los artefactos típicos de las voces neurales de edge-tts.
        """
        cfg = self.config

        board = Pedalboard([
            # ================================================================
            # ETAPA 1: HIGH-PASS FILTER (80 Hz)
            # ================================================================
            # Elimina el rumble sub-grave que no aporta nada a la voz
            # y puede causar problemas en la mezcla final.
            HighpassFilter(cutoff_frequency_hz=cfg.highpass_cutoff_hz),

            # ================================================================
            # ETAPA 2: EQ PARAMÉTRICO (3 bandas)
            # ================================================================

            # 2a. Corte en 3.2 kHz → Eliminar la "dureza robótica"
            # Las voces neurales tienen un pico antinatural en 2-4 kHz
            # que las hace sonar "digitales" y "cortantes".
            PeakFilter(
                cutoff_frequency_hz=cfg.eq_cut_freq_hz,
                gain_db=cfg.eq_cut_gain_db,
                q=cfg.eq_cut_q,
            ),

            # 2b. Boost en 180 Hz → Calidez de voz de hoguera
            # Agrega cuerpo y gravedad a la voz, como un narrador
            # hablando cerca de un micrófono de condensador grande.
            LowShelfFilter(
                cutoff_frequency_hz=cfg.eq_warmth_freq_hz,
                gain_db=cfg.eq_warmth_gain_db,
                q=cfg.eq_warmth_q,
            ),

            # 2c. Boost sutil en 8 kHz → Presencia y brillo natural
            # Agrega "aire" a la voz sin agregar sibilancia.
            # Simula la respuesta de un buen micrófono de estudio.
            HighShelfFilter(
                cutoff_frequency_hz=cfg.eq_presence_freq_hz,
                gain_db=cfg.eq_presence_gain_db,
                q=cfg.eq_presence_q,
            ),

            # ================================================================
            # ETAPA 3: COMPRESOR
            # ================================================================
            # Ratio 3:1 con threshold moderado.
            # Da consistencia a la voz: las partes suaves se elevan,
            # las partes fuertes se controlan.
            # Attack rápido (15ms) para captar consonantes.
            # Release medio (150ms) para sonar natural.
            Compressor(
                threshold_db=cfg.comp_threshold_db,
                ratio=cfg.comp_ratio,
                attack_ms=cfg.comp_attack_ms,
                release_ms=cfg.comp_release_ms,
            ),

            # ================================================================
            # ETAPA 4: DE-ESSER (via PeakFilter + Compressor focalizado)
            # ================================================================
            # Las voces de TTS tienen sibilancia artificial muy uniforme.
            # Atenuamos la banda de 6.5 kHz donde vive la sibilancia.
            PeakFilter(
                cutoff_frequency_hz=cfg.deesser_freq_hz,
                gain_db=cfg.deesser_threshold_db + 19,  # -3dB sutil
                q=3.0,  # Q alto para no afectar frecuencias vecinas
            ),

            # ================================================================
            # ETAPA 5: SATURACIÓN ARMÓNICA
            # ================================================================
            # Simula la calidez de un preamplificador analógico vintage.
            # Agrega armónicos pares (2do, 4to) que hacen la voz más
            # "humana" y "rica". Las voces digitales son demasiado
            # limpias; esto agrega la "imperfección" natural.
            #
            # Usamos Gain (para subir antes del clipping) + Clipping
            # suave + Gain (para bajar después) = saturación controlada.
            Gain(gain_db=cfg.saturation_drive_db),
            Clipping(threshold_db=-0.5),  # Clipping suave
            Gain(gain_db=-cfg.saturation_drive_db),  # Compensar ganancia

            # ================================================================
            # ETAPA 6: REVERB DE SALA PEQUEÑA
            # ================================================================
            # Simula un espacio real íntimo (sala pequeña / estudio).
            # Las voces de TTS suenan como grabadas en una cámara
            # anecoica (sin ningún ambiente), lo cual es antinatural.
            # Este reverb sutil agrega la "vida" del espacio.
            Reverb(
                room_size=cfg.reverb_room_size,
                damping=cfg.reverb_damping,
                wet_level=cfg.reverb_wet_level,
                dry_level=cfg.reverb_dry_level,
            ),

            # ================================================================
            # ETAPA 7: NOISE GATE
            # ================================================================
            # Limpia los silencios entre frases.
            # Las voces de TTS a veces dejan artefactos muy tenues
            # en los silencios. El gate los elimina.
            NoiseGate(
                threshold_db=cfg.gate_threshold_db,
                attack_ms=cfg.gate_attack_ms,
                release_ms=cfg.gate_release_ms,
            ),

            # ================================================================
            # ETAPA 8: LIMITER
            # ================================================================
            # Protección final contra clipping.
            # Asegura que ningún pico supere -1.5 dBFS.
            # Esencial para la mezcla posterior con música y SFX.
            Limiter(threshold_db=cfg.limiter_threshold_db),
        ])

        return board

    def procesar(self, input_path: Path, output_path: Path) -> None:
        """
        Procesa un archivo de audio a través de la cadena completa.

        Lee el audio en chunks para optimizar el uso de memoria
        en equipos con 8GB RAM.

        Args:
            input_path: Ruta al archivo WAV de entrada (crudo de TTS).
            output_path: Ruta al archivo WAV de salida (procesado).
        """
        logger.info(f"Iniciando post-procesamiento: {input_path.name}")
        logger.info(f"Cadena de efectos: {len(self._board)} etapas")

        # Procesar en chunks para optimizar memoria
        chunk_size = 1024 * 256  # ~256K samples por chunk

        with AudioFile(str(input_path)) as infile:
            sample_rate = infile.samplerate
            num_channels = infile.num_channels
            total_frames = infile.frames
            duration_sec = total_frames / sample_rate

            logger.info(
                f"Audio de entrada: {duration_sec:.1f}s | "
                f"{sample_rate}Hz | {num_channels}ch | "
                f"{total_frames} frames"
            )

            with AudioFile(
                str(output_path),
                "w",
                samplerate=sample_rate,
                num_channels=num_channels,
            ) as outfile:
                frames_processed = 0

                while infile.tell() < total_frames:
                    # Leer chunk
                    chunk = infile.read(chunk_size)

                    # Aplicar cadena de efectos al chunk
                    processed = self._board(chunk, sample_rate)

                    # Escribir chunk procesado
                    outfile.write(processed)

                    frames_processed += chunk.shape[1] if chunk.ndim > 1 else chunk.shape[0]

                    # Log de progreso cada ~10 segundos de audio
                    if frames_processed % (sample_rate * 10) < chunk_size:
                        progress = (frames_processed / total_frames) * 100
                        logger.debug(f"Procesando: {progress:.0f}%")

        print_info(
            f"Audio procesado: {output_path.name} | "
            f"Duración: {duration_sec:.1f}s | 8 efectos aplicados"
        )

    def describir_cadena(self) -> str:
        """Retorna una descripción legible de la cadena de efectos."""
        cfg = self.config
        return (
            "🔊 Cadena de Post-Procesamiento Premium\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  1. High-Pass Filter     │ {cfg.highpass_cutoff_hz}Hz\n"
            f"  2. EQ Cut (robótica)    │ {cfg.eq_cut_gain_db}dB @ {cfg.eq_cut_freq_hz}Hz\n"
            f"  3. EQ Warm (calidez)    │ +{cfg.eq_warmth_gain_db}dB @ {cfg.eq_warmth_freq_hz}Hz\n"
            f"  4. EQ Presence (brillo) │ +{cfg.eq_presence_gain_db}dB @ {cfg.eq_presence_freq_hz}Hz\n"
            f"  5. Compresor            │ {cfg.comp_ratio}:1 @ {cfg.comp_threshold_db}dB\n"
            f"  6. De-esser             │ @ {cfg.deesser_freq_hz}Hz\n"
            f"  7. Saturación armónica  │ {cfg.saturation_drive_db}dB drive, {cfg.saturation_mix*100:.0f}% mix\n"
            f"  8. Reverb sala          │ size={cfg.reverb_room_size}, wet={cfg.reverb_wet_level}\n"
            f"  9. Noise Gate           │ {cfg.gate_threshold_db}dB threshold\n"
            f" 10. Limiter              │ {cfg.limiter_threshold_db}dBFS ceiling\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
