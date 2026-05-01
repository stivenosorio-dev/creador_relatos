"""
🎙️ Narrador TTS — Generación de audio narrativo premium.

Genera narración con edge-tts o kokoro y aplica post-procesamiento profesional
para eliminar todo rastro de voz sintética. El resultado es una voz
de narrador de hoguera: cálida, profunda, inmersiva.

Flujo:
  Texto → Preprocesamiento dramático → TTS (edge-tts/kokoro) → Post-procesamiento → MP3 final
"""

import asyncio
import re
import wave
from pathlib import Path

import edge_tts
import numpy as np
from pydub import AudioSegment

from config import VozConfig, AudioProcessConfig, AUDIO_PROCESS_DEFAULT
from utils.logger import (
    get_logger,
    print_info,
    print_success,
    print_warning,
    print_step,
)
from utils.memory_manager import memory_manager

logger = get_logger("narrador_tts")


class NarradorTTS:
    """
    Generador de audio narrativo premium con edge-tts o kokoro.

    Preprocesa el texto para agregar pausas dramáticas,
    genera el audio con la voz seleccionada, y aplica
    una cadena de post-procesamiento profesional.
    """

    def __init__(
        self,
        voz_config: VozConfig,
        velocidad: str = "-5%",
        pitch: str = "-2Hz",
        audio_config: AudioProcessConfig = AUDIO_PROCESS_DEFAULT,
    ):
        self.voz = voz_config
        self.velocidad = velocidad
        self.pitch = pitch
        self.audio_config = audio_config

    async def generar(self, texto: str, output_dir: Path) -> Path:
        """
        Pipeline completo de generación de audio narrativo.

        Args:
            texto: Texto del relato paranormal.
            output_dir: Directorio donde guardar el audio final.

        Returns:
            Path al archivo MP3 final procesado.
        """
        # Verificar memoria antes de iniciar
        memory_manager.pre_module_check("NarradorTTS", estimated_mb=300)

        # Paso 1: Preprocesar texto para dramatismo
        print_step(1, 4, "Preprocesando texto con pausas dramáticas...")
        texto_dramatico = self._preprocesar_texto(texto)
        logger.info(f"Texto preprocesado: {len(texto)} → {len(texto_dramatico)} caracteres")

        # Paso 2: Generar audio con TTS
        print_step(2, 4, f"Generando narración con voz '{self.voz.nombre}' ({self.voz.motor})...")
        audio_crudo_path = output_dir / "audio_crudo.wav"
        await self._generar_tts(texto_dramatico, audio_crudo_path)
        print_info(f"Audio crudo generado: {audio_crudo_path.name}")

        # Paso 3: Post-procesamiento premium
        print_step(3, 4, "Aplicando cadena de efectos profesional (8 etapas)...")
        audio_procesado_path = output_dir / "audio_narrativo_procesado.wav"
        self._postprocesar_audio(audio_crudo_path, audio_procesado_path)
        print_info("Post-procesamiento completado: voz sintética eliminada")

        # Paso 4: Exportar a MP3 320kbps
        print_step(4, 4, "Exportando a MP3 320kbps...")
        audio_final_path = output_dir / "audio_narrativo.mp3"
        self._exportar_mp3(audio_procesado_path, audio_final_path)

        # Limpiar archivos intermedios
        self._limpiar_intermedios(audio_crudo_path, audio_procesado_path)

        duracion = self.obtener_duracion(audio_final_path)
        print_success(
            f"Audio final: {audio_final_path.name} "
            f"({int(duracion // 60)}:{int(duracion % 60):02d})"
        )

        return audio_final_path

    # ========================================================================
    # PREPROCESAMIENTO DE TEXTO
    # ========================================================================

    def _preprocesar_texto(self, texto: str) -> str:
        """
        Transforma el texto crudo en texto optimizado para TTS dramático.
        
        Agrega pausas SSML, ajusta puntuación para mejorar la prosodia,
        y optimiza el ritmo narrativo para contenido de terror.
        
        Nota: Las pausas via comas son efectivas en edge-tts. Kokoro
        interpreta la puntuación de forma nativa y también se beneficia
        de estos marcadores.
        """
        resultado = texto

        # 1. Normalizar espacios y saltos de línea
        resultado = re.sub(r'\n{3,}', '\n\n', resultado)
        resultado = re.sub(r' {2,}', ' ', resultado)

        # 2. Puntos suspensivos → pausa larga de suspenso (900ms)
        resultado = re.sub(r'\.{3,}', ', , , ', resultado)

        # 3. Después de signos de exclamación → pausa de impacto (600ms)
        resultado = re.sub(r'!(\s)', r'! , \1', resultado)

        # 4. Después de signos de interrogación → pausa de incertidumbre (400ms)
        resultado = re.sub(r'\?(\s)', r'? , \1', resultado)

        # 5. Guiones largos (—) → pausa dramática
        resultado = resultado.replace('—', ', , ')
        resultado = resultado.replace('–', ', ')

        # 6. Separar párrafos con pausas largas
        resultado = re.sub(r'\n\n', '\n, , , ,\n', resultado)

        # 7. Texto entre comillas (diálogos) - agregar pausa antes y después
        resultado = re.sub(r'"([^"]+)"', r', "\1", ', resultado)
        resultado = re.sub(r'"([^"]+)"', r', "\1", ', resultado)
        resultado = re.sub(r'«([^»]+)»', r', "\1", ', resultado)

        # 8. Palabras en MAYÚSCULAS → agregar énfasis con pausas
        def enfatizar_mayusculas(match):
            palabra = match.group(0)
            if len(palabra) > 2 and palabra.isupper():
                return f", {palabra.capitalize()}, "
            return palabra

        resultado = re.sub(r'\b[A-ZÁÉÍÓÚÑ]{3,}\b', enfatizar_mayusculas, resultado)

        # 9. Limpiar comas múltiples excesivas
        resultado = re.sub(r',(\s*,){4,}', ', , , ,', resultado)
        resultado = re.sub(r'\s{2,}', ' ', resultado)

        return resultado.strip()

    # ========================================================================
    # GENERACIÓN TTS
    # ========================================================================

    async def _generar_tts(self, texto: str, output_path: Path) -> None:
        """
        Genera audio con el motor TTS configurado (edge-tts o kokoro).

        Args:
            texto: Texto preprocesado para narración.
            output_path: Ruta del archivo WAV de salida.
        """
        if self.voz.motor == "kokoro":
            # kokoro no es async nativo; ejecutar en thread para no bloquear el loop
            await asyncio.get_event_loop().run_in_executor(
                None, self._generar_tts_kokoro_sync, texto, output_path
            )
        else:
            await self._generar_tts_edge(texto, output_path)

    async def _generar_tts_edge(self, texto: str, output_path: Path) -> None:
        """Genera audio con edge-tts."""
        communicate = edge_tts.Communicate(
            text=texto,
            voice=self.voz.voice_id,
            rate=self.velocidad,
            pitch=self.pitch,
        )

        # edge-tts genera MP3, necesitamos convertir a WAV para procesamiento
        temp_mp3 = output_path.parent / "_temp_tts_output.mp3"

        try:
            await communicate.save(str(temp_mp3))

            # Convertir MP3 → WAV para procesamiento de audio sin pérdida
            audio = AudioSegment.from_mp3(str(temp_mp3))
            audio = audio.set_frame_rate(self.audio_config.sample_rate)
            audio = audio.set_channels(1)  # Mono para narración
            audio.export(str(output_path), format="wav")

            logger.info(
                f"TTS edge-tts generado: {output_path.name} | "
                f"Duración: {len(audio) / 1000:.1f}s | "
                f"Sample rate: {audio.frame_rate}Hz"
            )
        finally:
            # Limpiar archivo temporal
            if temp_mp3.exists():
                temp_mp3.unlink()

    def _generar_tts_kokoro_sync(self, texto: str, output_path: Path) -> None:
        """
        Genera audio con kokoro (KPipeline) — versión síncrona.

        Kokoro oficial:
          - KPipeline(lang_code='e')  → español
          - generator = pipeline(text, voice='em_santa', speed=1.0)
          - for i, (gs, ps, audio) in enumerate(generator):
                sf.write(f'{i}.wav', audio, 24000)
          - audio es un numpy array float32, sample rate 24000 Hz

        Esta implementación:
          1. Divide el texto en párrafos para manejar textos largos sin OOM.
          2. Concatena todos los chunks de audio en un solo array float32.
          3. Exporta a WAV 44100 Hz mono (vía pydub) para que el
             AudioProcessor lo procese igual que el audio de edge-tts.
        """
        try:
            import soundfile as sf
            from kokoro import KPipeline
        except ImportError as e:
            raise RuntimeError(
                "Dependencias de kokoro no encontradas. "
                "Ejecuta: pip install kokoro>=0.9.2 soundfile\n"
                "Y asegúrate de tener espeak-ng instalado:\n"
                "  Linux: sudo apt-get install espeak-ng\n"
                "  Windows: instalar desde https://github.com/espeak-ng/espeak-ng/releases"
            ) from e

        KOKORO_SAMPLE_RATE = 24000

        # Inicializar pipeline para español
        try:
            pipeline = KPipeline(lang_code='e')
        except Exception as e:
            raise RuntimeError(
                f"No se pudo inicializar KPipeline para español (lang_code='e'). "
                f"Verifica que espeak-ng esté instalado correctamente. Error: {e}"
            ) from e

        logger.info(f"Kokoro pipeline inicializado. Voz: {self.voz.voice_id}")

        # Dividir texto en párrafos para evitar fragmentos demasiado largos
        # (Kokoro funciona mejor con chunks de ~500 palabras o menos)
        parrafos = [p.strip() for p in texto.split('\n') if p.strip()]
        if not parrafos:
            parrafos = [texto]

        all_audio_chunks: list[np.ndarray] = []

        for idx_parrafo, parrafo in enumerate(parrafos):
            if not parrafo:
                continue

            logger.debug(f"Kokoro procesando párrafo {idx_parrafo + 1}/{len(parrafos)}...")

            try:
                # API oficial: pipeline(text, voice, speed)
                # El generator yield: (graphemes, phonemes, audio_array)
                generator = pipeline(
                    parrafo,
                    voice=self.voz.voice_id,
                    speed=1.0,
                )

                for i, (gs, ps, audio) in enumerate(generator):
                    if audio is None or len(audio) == 0:
                        logger.debug(f"  Chunk {i} vacío, saltando.")
                        continue
                    # Kokoro puede devolver torch.Tensor o np.ndarray según versión/SO.
                    # Normalizar siempre a numpy float32.
                    try:
                        import torch
                        if isinstance(audio, torch.Tensor):
                            audio_np = audio.detach().cpu().numpy().astype(np.float32)
                        else:
                            audio_np = np.asarray(audio, dtype=np.float32)
                    except ImportError:
                        audio_np = np.asarray(audio, dtype=np.float32)
                    all_audio_chunks.append(audio_np)

            except Exception as e:
                logger.warning(f"Error en párrafo {idx_parrafo + 1}: {e}. Saltando.")
                continue

        if not all_audio_chunks:
            raise RuntimeError(
                "Kokoro no generó audio para ningún fragmento del texto. "
                "Verifica que el texto no esté vacío y que la voz sea válida."
            )

        # Concatenar todos los chunks
        audio_combined = np.concatenate(all_audio_chunks)  # float32, 24000 Hz

        # Guardar WAV temporal en 24000 Hz (nativo de kokoro)
        temp_wav_24k = output_path.parent / "_temp_kokoro_24k.wav"
        sf.write(str(temp_wav_24k), audio_combined, KOKORO_SAMPLE_RATE)

        duracion_seg = len(audio_combined) / KOKORO_SAMPLE_RATE
        logger.info(
            f"TTS Kokoro generado: {temp_wav_24k.name} | "
            f"Duración: {duracion_seg:.1f}s | "
            f"Sample rate: {KOKORO_SAMPLE_RATE}Hz | "
            f"Chunks: {len(all_audio_chunks)}"
        )

        # Resamplear a 44100 Hz mono (requerido por AudioProcessor / pedalboard)
        # pydub maneja la conversión de sample rate automáticamente
        try:
            audio_seg = AudioSegment.from_wav(str(temp_wav_24k))
            audio_seg = audio_seg.set_frame_rate(self.audio_config.sample_rate)
            audio_seg = audio_seg.set_channels(1)
            audio_seg.export(str(output_path), format="wav")

            logger.info(
                f"Resampling completado: {KOKORO_SAMPLE_RATE}Hz → "
                f"{self.audio_config.sample_rate}Hz | "
                f"Archivo final: {output_path.name}"
            )
        finally:
            if temp_wav_24k.exists():
                temp_wav_24k.unlink()

    # ========================================================================
    # POST-PROCESAMIENTO DE AUDIO
    # ========================================================================

    def _postprocesar_audio(self, input_path: Path, output_path: Path) -> None:
        """
        Aplica la cadena completa de 8 efectos de post-procesamiento
        para eliminar todo rastro de voz sintética.

        Cadena: HPF → EQ → Compresor → De-esser → Saturación → 
                Reverb → Noise Gate → Limiter
        """
        from core.audio_processor import AudioProcessor

        processor = AudioProcessor(self.audio_config)
        processor.procesar(input_path, output_path)

    # ========================================================================
    # EXPORTACIÓN Y UTILIDADES
    # ========================================================================

    def _exportar_mp3(self, wav_path: Path, mp3_path: Path) -> None:
        """Convierte WAV procesado a MP3 320kbps."""
        audio = AudioSegment.from_wav(str(wav_path))
        audio.export(
            str(mp3_path),
            format="mp3",
            bitrate=self.audio_config.output_bitrate,
            parameters=["-q:a", "0"],  # Máxima calidad
        )
        logger.info(f"Exportado MP3: {mp3_path.name} ({self.audio_config.output_bitrate})")

    def _limpiar_intermedios(self, *paths: Path) -> None:
        """Elimina archivos intermedios para liberar espacio."""
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
                    logger.debug(f"Eliminado intermedio: {path.name}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar {path.name}: {e}")

    def obtener_duracion(self, audio_path: Path) -> float:
        """
        Obtiene la duración de un archivo de audio en segundos.

        Args:
            audio_path: Ruta al archivo de audio (MP3 o WAV).

        Returns:
            Duración en segundos. 0.0 si ocurre un error.
        """
        try:
            suffix = audio_path.suffix.lower()
            if suffix == '.mp3':
                audio = AudioSegment.from_mp3(str(audio_path))
            elif suffix == '.wav':
                audio = AudioSegment.from_wav(str(audio_path))
            else:
                audio = AudioSegment.from_file(str(audio_path))

            return len(audio) / 1000.0
        except Exception as e:
            logger.error(f"Error obteniendo duración de {audio_path}: {e}")
            return 0.0