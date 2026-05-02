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

from config import (
    VozConfig,
    AudioProcessConfig,
    AUDIO_PROCESS_DEFAULT,
    KOKORO_NARRACION_DEFAULT,
)
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
        *,
        kokoro_pausa_entre_oraciones_s: float | None = None,
        kokoro_fade_union_ms: float | None = None,
        kokoro_recorte_cola_relativo: float | None = None,
        kokoro_speed: float | None = None,
    ):
        self.voz = voz_config
        self.velocidad = velocidad
        self.pitch = pitch
        self.audio_config = audio_config
        # Solo motor kokoro; None = valores por defecto en _generar_tts_kokoro_sync
        self.kokoro_pausa_entre_oraciones_s = kokoro_pausa_entre_oraciones_s
        self.kokoro_fade_union_ms = kokoro_fade_union_ms
        self.kokoro_recorte_cola_relativo = kokoro_recorte_cola_relativo
        # None = derivar de `velocidad` estilo edge; float = pasar directo a KPipeline(speed=…)
        self.kokoro_speed = kokoro_speed

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
        texto_dramatico = self._preprocesar_texto(texto, motor=self.voz.motor)
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

    def _preprocesar_texto(self, texto: str, *, motor: str = "edge-tts") -> str:
        """
        Transforma el texto crudo en texto optimizado para TTS dramático.

        ESTRATEGIA DE PAUSAS:
        Edge-TTS interpreta las comas como pausas cortas (~300ms) cuando están
        dentro de una frase continua. El problema que causaba el artefacto "brr"
        era colocar comas ENTRE saltos de línea (\n, , , ,\n), lo que generaba
        una línea vacía que empezaba con coma — edge-tts la vocalizaba como un
        fonema inválido.

        Solución: los saltos de línea (cambios de párrafo) se convierten en un
        punto final seguido de un espacio, unificando el texto en un flujo
        continuo de frases. Las pausas dramáticas se insertan SIEMPRE dentro
        de la misma línea como comas de puntuación, nunca al inicio de línea.

        Kokoro ignora parte de esa prosodia textual y suele concatenar los
        segmentos sin silencios audibles entre oraciones — para kokoro las
        oraciones pasan a líneas (\n), y `_generar_tts_kokoro_sync` inserta
        silencio explícito entre cada línea. No se usa "? ."/"! ." markers de
        edge porque verbalizarían una frase cortada rara en kokoro/espeak.
        """
        resultado = texto

        # ── ETAPA 1: Unificar el texto en un flujo continuo ───────────────
        # El error principal: \n\n con comas al inicio de la línea siguiente
        # causa que edge-tts vocalice las comas como fonema — produce "brr".
        # Solución: convertir párrafos en punto + espacio (pausa natural del motor).
        resultado = re.sub(r'([^.!?])\n{2,}', r'\1. ', resultado)  # sin puntuacion -> agregar punto
        resultado = re.sub(r'([.!?])\n{2,}', r'\1 ', resultado)     # ya tiene puntuacion -> solo espacio
        resultado = re.sub(r' *\n *', ' ', resultado)                  # salto simple -> espacio

        # ── ETAPA 2: Normalizar espacios redundantes ──────────────────────
        resultado = re.sub(r' {2,}', ' ', resultado)

        # ── ETAPA 3: Puntos suspensivos → pausa larga de suspenso ─────────
        # ". . . " es seguro: está rodeado de espacios, nunca al inicio.
        resultado = re.sub(r'\.{3,}', '. . . ', resultado)

        # ── ETAPA 4/5: Impacto/Incertidumbre (solo edge: "? ." / "! .").
        # Kokoro: silencios reales entre oraciones en lugar de estos marcadores.

        if motor != "kokoro":
            resultado = re.sub(r'!(\s+)', r'! . \1', resultado)
            resultado = re.sub(r'\?(\s+)', r'? . \1', resultado)

        # ── ETAPA 6: Guiones largos → pausa dramática ─────────────────────
        # Reemplazar con punto y coma rodeado de espacios (pausa media segura)
        resultado = resultado.replace('—', '; ')
        resultado = resultado.replace('–', ', ')

        # ── ETAPA 7: Diálogos entre comillas → pausa antes y después ──────
        # Solo añadir coma de pausa ANTES de la comilla de apertura,
        # nunca al inicio del resultado.
        resultado = re.sub(r'(?<=\w)\s*"([^"]+)"', r', "\1"', resultado)
        resultado = re.sub(r'(?<=\w)\s*"([^"]+)"', r', "\1"', resultado)
        resultado = re.sub(r'(?<=\w)\s*«([^»]+)»', r', "\1"', resultado)

        # ── ETAPA 8: Palabras en MAYÚSCULAS → énfasis con pausas ──────────
        def enfatizar_mayusculas(match):
            palabra = match.group(0)
            if len(palabra) > 2 and palabra.isupper():
                return f", {palabra.capitalize()}, "
            return palabra

        resultado = re.sub(r'\b[A-ZÁÉÍÓÚÑ]{3,}\b', enfatizar_mayusculas, resultado)

        # ── ETAPA 9: Limpieza final ────────────────────────────────────────
        # Eliminar cualquier coma que haya quedado al inicio de la cadena
        resultado = re.sub(r'^[\s,;\.]+', '', resultado)
        # Colapsar secuencias de puntuación duplicada
        resultado = re.sub(r'(\.\s*){3,}', '. . . ', resultado)
        resultado = re.sub(r',(\s*,){2,}', ', , ', resultado)
        # Espacios múltiples finales
        resultado = re.sub(r' {2,}', ' ', resultado)

        resultado = resultado.strip()

        # Kokoro: una oración por línea para insertar pausas WAV entre ellas.
        if motor == "kokoro":
            resultado = self._kokoro_fragmentar_en_lineas(resultado)

        return resultado

    def _kokoro_fragmentar_en_lineas(self, texto: str) -> str:
        """
        Una oración por línea (. ! ? …) para poder insertar silencio WAV real
        entre oraciones — Kokoro no separa tanto como edge al concatenar yields.
        """
        ell = "\ue666"
        t = texto.replace(". . . ", f"{ell} ")
        trozos = re.split(r"(?<=[.!?])\s+", t)
        lineas = [frag.replace(ell, ". . . ").strip() for frag in trozos]
        lineas = [ln for ln in lineas if ln]
        return "\n".join(lineas) if lineas else texto

    def _kokoro_speed_desde_velocidad_edge(self) -> float:
        """Mapea el rate edge (p. ej. '-5%' → algo más lento) al parámetro speed de kokoro."""
        raw = self.velocidad.strip().replace(" ", "")
        match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)%", raw)
        if not match:
            return 0.92
        pct = float(match.group(1))
        # -5% en edge≈ ritmo algo más calmado ⇒ speed < 1.0
        return float(max(0.65, min(1.3, 1.0 + pct / 100.0)))

    @staticmethod
    def _kokoro_recortar_colas_mudas(
        audio: np.ndarray, rel_peak: float = 0.018
    ) -> np.ndarray:
        """
        Quita silencio casi plano al inicio/fin de cada síntesis.
        Si no se hace, el fundido actúa sobre tramos ya mudos y la unión
        voz–pausa suena a 'tapón' o corte brusco.
        """
        if audio.size < 32:
            return audio
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-8:
            return audio
        thr = max(peak * rel_peak, 1e-5)
        idx = np.nonzero(np.abs(audio) > thr)[0]
        if idx.size == 0:
            return audio
        return np.ascontiguousarray(audio[idx[0] : idx[-1] + 1], dtype=np.float32)

    @staticmethod
    def _kokoro_fundir_bordes(
        audio: np.ndarray,
        sample_rate: int,
        fade_ms: float,
        *,
        fundir_entrada: bool,
        fundir_salida: bool,
    ) -> np.ndarray:
        """
        Fundidos cortos (sen² / cos²) para evitar discontinuidades que el oído
        percibe como clic al pasar de habla a silencio o viceversa.
        """
        n = max(3, int(sample_rate * fade_ms * 0.001))
        out = np.ascontiguousarray(audio, dtype=np.float32).copy()
        if len(out) <= n * 2:
            return out
        if fundir_entrada:
            t = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)
            out[:n] *= np.sin(t) ** 2
        if fundir_salida:
            t = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)
            out[-n:] *= np.cos(t) ** 2
        return out

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
          1. Una línea = una oración (preprocesado kokoro): evita pegar todas
             las yields del modelo sin huecos audibles entre frases.
          2. Entre líneas inserta silencio explícito (24 kHz) — ritmo tipo relato.
          3. Recorte de colas mudas + fundidos de borde para evitar clics entre trozos.
          4. Usa `speed` derivado del mismo dial de velocidad que edge (`-5%`…).
          5. Resample a la frecuencia del AudioProcessor igual que edge-tts.
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
        # Duración perceptible tipo “hueco narrativo”; terror suele funcionar algo por encima.
        kd = KOKORO_NARRACION_DEFAULT
        KOKORO_PAUSE_ENTRE_ORACIONES_S = (
            self.kokoro_pausa_entre_oraciones_s
            if self.kokoro_pausa_entre_oraciones_s is not None
            else kd.pausa_entre_oraciones_s
        )
        # Fundido en uniones oración–pausa–oración (evita clics).
        KOKORO_FADE_UNION_MS = (
            self.kokoro_fade_union_ms
            if self.kokoro_fade_union_ms is not None
            else kd.fade_union_ms
        )
        recorte_rel = (
            self.kokoro_recorte_cola_relativo
            if self.kokoro_recorte_cola_relativo is not None
            else kd.recorte_cola_relativo
        )

        if self.kokoro_speed is not None:
            kokoro_speed = float(max(0.5, min(1.5, self.kokoro_speed)))
            origen_speed = f"fijo={kokoro_speed}"
        else:
            kokoro_speed = self._kokoro_speed_desde_velocidad_edge()
            origen_speed = f"desde edge '{self.velocidad}' → {kokoro_speed}"

        silencio_interlinea = np.zeros(
            int(KOKORO_SAMPLE_RATE * KOKORO_PAUSE_ENTRE_ORACIONES_S),
            dtype=np.float32,
        )

        # Inicializar pipeline para español
        try:
            pipeline = KPipeline(lang_code='e')
        except Exception as e:
            raise RuntimeError(
                f"No se pudo inicializar KPipeline para español (lang_code='e'). "
                f"Verifica que espeak-ng esté instalado correctamente. Error: {e}"
            ) from e

        logger.info(
            f"Kokoro pipeline inicializado. Voz: {self.voz.voice_id} | "
            f"speed={kokoro_speed} ({origen_speed})"
        )

        # Líneas = oraciones (~); silencio entre líneas para pausas de narrador.
        oraciones_lineas = [p.strip() for p in texto.split("\n") if p.strip()]
        if not oraciones_lineas:
            oraciones_lineas = [texto]

        audio_por_oracion: list[np.ndarray] = []

        def _normalize_chunk(audio_chunk) -> np.ndarray:
            """Kokoro puede devolver torch.Tensor o ndarray."""
            try:
                import torch
                if isinstance(audio_chunk, torch.Tensor):
                    return audio_chunk.detach().cpu().numpy().astype(np.float32)
            except ImportError:
                pass
            return np.asarray(audio_chunk, dtype=np.float32)

        for idx, linea in enumerate(oraciones_lineas):
            if not linea:
                continue

            logger.debug(f"Kokoro oración {idx + 1}/{len(oraciones_lineas)}...")

            try:
                generator = pipeline(
                    linea,
                    voice=self.voz.voice_id,
                    speed=kokoro_speed,
                )

                intra_linea: list[np.ndarray] = []
                for i, (gs, ps, audio) in enumerate(generator):
                    if audio is None or len(audio) == 0:
                        logger.debug(f"  Chunk {i} vacío, saltando.")
                        continue
                    intra_linea.append(_normalize_chunk(audio))

                if not intra_linea:
                    logger.warning(f"Sin audio para oración {idx + 1}, se omite.")
                    continue

                bloque = self._kokoro_recortar_colas_mudas(
                    np.concatenate(intra_linea), rel_peak=recorte_rel
                )
                if bloque.size == 0:
                    logger.warning(f"Audio vacío tras recorte en oración {idx + 1}, se omite.")
                    continue

                audio_por_oracion.append(bloque)

            except Exception as e:
                logger.warning(f"Error en oración {idx + 1}: {e}. Saltando.")
                continue

        if not audio_por_oracion:
            raise RuntimeError(
                "Kokoro no generó audio para ningún fragmento del texto. "
                "Verifica que el texto no esté vacío y que la voz sea válida."
            )

        audio_por_oracion = [
            self._kokoro_fundir_bordes(
                blk,
                KOKORO_SAMPLE_RATE,
                KOKORO_FADE_UNION_MS,
                fundir_entrada=i > 0,
                fundir_salida=True,
            )
            for i, blk in enumerate(audio_por_oracion)
        ]

        with_pauses: list[np.ndarray] = []
        for i, block in enumerate(audio_por_oracion):
            with_pauses.append(block)
            if i < len(audio_por_oracion) - 1:
                with_pauses.append(silencio_interlinea)

        audio_combined = np.concatenate(with_pauses)

        # Guardar WAV temporal en 24000 Hz (nativo de kokoro)
        temp_wav_24k = output_path.parent / "_temp_kokoro_24k.wav"
        sf.write(str(temp_wav_24k), audio_combined, KOKORO_SAMPLE_RATE)

        duracion_seg = len(audio_combined) / KOKORO_SAMPLE_RATE
        logger.info(
            f"TTS Kokoro generado: {temp_wav_24k.name} | "
            f"Duración: {duracion_seg:.1f}s | "
            f"Sample rate: {KOKORO_SAMPLE_RATE}Hz | "
            f"Oraciones: {len(audio_por_oracion)} "
            f"(pausa {KOKORO_PAUSE_ENTRE_ORACIONES_S:.2f}s, "
            f"fundido uniones {KOKORO_FADE_UNION_MS:.0f}ms)"
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