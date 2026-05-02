"""
📝 Transcriptor de Subtítulos — Generación de subtítulos SRT y ASS.

Utiliza faster-whisper optimizado para 8GB RAM (int8, CPU).
Extrae tiempos a nivel de palabra para máxima precisión en la sincronización.
Produce dos formatos:
  - SRT: Estándar universal, una línea por segmento de frase
  - ASS: Subtítulos estilizados por plataforma con karaoke palabra a palabra

CORRECCIONES:
  - Sin palabras omitidas: se recolectan TODOS los segmentos antes de procesar
    (faster-whisper es un generador lazy; iterar dos veces pierde datos)
  - Chunking inteligente: respeta puntuación Y límite de caracteres, no solo
    cantidad de palabras (evita líneas que desbordan la pantalla)
  - ASS adaptado por plataforma: resolución, tamaño de fuente y márgenes
    correctos para vertical (9:16) y horizontal (16:9)
  - Filtro de probabilidad: palabras con prob < 0.5 se loguean para debug
    pero se incluyen igual (no se omiten)
"""

from pathlib import Path
from typing import List, Dict, Any

from faster_whisper import WhisperModel

from config import WhisperConfig, WHISPER_DEFAULT, PLATAFORMAS
from utils.logger import get_logger, print_info
from utils.memory_manager import memory_manager

logger = get_logger("transcriptor")

# Caracteres máximos por línea de subtítulo según orientación
MAX_CHARS_VERTICAL = 20    # 9:16 — pantallas angostas, fuente grande
MAX_CHARS_HORIZONTAL = 42  # 16:9 — pantallas anchas, fuente más pequeña

# Signos de puntuación que fuerzan corte de chunk
PUNTUACION_CORTE = {'.', ',', '?', '!', ';', ':', '—', '…'}


class Transcriptor:
    """
    Generador de subtítulos sincronizados sin omisión de palabras.

    Usa faster-whisper para crear archivos SRT clásicos
    y archivos ASS estilizados para relatos de terror.
    """

    def __init__(self, config: WhisperConfig = WHISPER_DEFAULT):
        self.config = config
        self.model = None

    def _cargar_modelo(self):
        """Carga el modelo Whisper en memoria perezosamente."""
        if self.model is None:
            logger.info(
                f"Cargando modelo Whisper '{self.config.model_size}' "
                f"({self.config.compute_type} en {self.config.device})..."
            )
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

    def generar(
        self,
        audio_path: Path,
        output_dir: Path,
        plataforma: str = "youtube_largo",
    ) -> tuple[Path, Path]:
        """
        Transcribe el audio y genera los archivos de subtítulos.

        Args:
            audio_path: Ruta al archivo de audio (MP3 o WAV).
            output_dir: Directorio donde guardar los subtítulos.
            plataforma: Clave de plataforma para adaptar el estilo ASS.

        Returns:
            Tupla con paths (srt_path, ass_path).
        """
        memory_manager.pre_module_check("Transcriptor", estimated_mb=1500)

        try:
            self._cargar_modelo()

            logger.info(f"Iniciando transcripción de: {audio_path.name}")

            # ----------------------------------------------------------------
            # CRÍTICO: faster-whisper devuelve un GENERADOR lazy.
            # Hay que consumirlo UNA SOLA VEZ y guardarlo en listas.
            # Si se itera dos veces (una para SRT, otra para ASS) la segunda
            # vuelta devuelve vacío → palabras omitidas.
            # ----------------------------------------------------------------
            segments_gen, info = self.model.transcribe(
                str(audio_path),
                beam_size=self.config.beam_size,
                language=self.config.language,
                word_timestamps=self.config.word_timestamps,
                vad_filter=self.config.vad_filter,
                vad_parameters=self.config.vad_parameters,
            )

            logger.info(
                f"Idioma detectado: {info.language} "
                f"(confianza={info.language_probability:.2f})"
            )

            # Consumir el generador UNA vez, guardar todo en memoria
            srt_segments: List[Dict[str, Any]] = []
            palabras_transcritas: List[Dict[str, Any]] = []
            palabras_baja_prob: int = 0

            for segment in segments_gen:
                texto_seg = segment.text.strip()
                if not texto_seg:
                    continue

                srt_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': texto_seg,
                })

                if self.config.word_timestamps and segment.words:
                    for word in segment.words:
                        palabra = word.word.strip()
                        if not palabra:
                            continue
                        if word.probability < 0.5:
                            palabras_baja_prob += 1
                            logger.debug(
                                f"Palabra baja confianza ({word.probability:.2f}): '{palabra}'"
                            )
                        # Se incluye SIEMPRE — no omitir palabras
                        palabras_transcritas.append({
                            'word': palabra,
                            'start': word.start,
                            'end': word.end,
                            'probability': word.probability,
                        })

            logger.info(
                f"Transcripción completa: {len(srt_segments)} segmentos | "
                f"{len(palabras_transcritas)} palabras | "
                f"{palabras_baja_prob} con baja confianza"
            )

            if not srt_segments:
                raise RuntimeError(
                    "Whisper no detectó ningún segmento de voz en el audio. "
                    "Verifica que el archivo tenga audio y sea legible."
                )

            # Configuración de plataforma para el ASS
            plat_config = PLATAFORMAS.get(plataforma)
            es_vertical = plat_config.aspecto == "9:16" if plat_config else True
            resolucion = plat_config.resolucion if plat_config else "1080x1920"
            res_x, res_y = map(int, resolucion.split("x"))

            # Generar archivos
            srt_path = output_dir / "subtitulos.srt"
            ass_path = output_dir / "subtitulos.ass"

            self._generar_srt(srt_segments, srt_path)

            if self.config.word_timestamps and palabras_transcritas:
                self._generar_ass_por_palabra(
                    palabras_transcritas, ass_path,
                    es_vertical=es_vertical,
                    res_x=res_x, res_y=res_y,
                )
            else:
                self._generar_ass(
                    srt_segments, ass_path,
                    es_vertical=es_vertical,
                    res_x=res_x, res_y=res_y,
                )

        finally:
            # Garantizar liberación de memoria aunque falle
            self.model = None
            import gc
            gc.collect()

        return srt_path, ass_path

    # ========================================================================
    # UTILIDADES DE FORMATO DE TIEMPO
    # ========================================================================

    def _format_time_srt(self, seconds: float) -> str:
        """Formatea tiempo para SRT: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_time_ass(self, seconds: float) -> str:
        """Formatea tiempo para ASS: H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    # ========================================================================
    # CHUNKING INTELIGENTE DE PALABRAS
    # ========================================================================

    def _agrupar_palabras_en_chunks(
        self,
        words: List[Dict[str, Any]],
        max_chars: int,
    ) -> List[List[Dict[str, Any]]]:
        """
        Agrupa palabras en chunks para subtítulos respetando:
          1. Límite de caracteres por línea (evita desbordamiento en pantalla)
          2. Signos de puntuación como cortes naturales de frase
          3. Nunca parte una palabra a la mitad

        Args:
            words: Lista de palabras con timing.
            max_chars: Máximo de caracteres por línea de subtítulo.

        Returns:
            Lista de chunks, cada chunk es una lista de palabras.
        """
        chunks: List[List[Dict[str, Any]]] = []
        current_chunk: List[Dict[str, Any]] = []
        current_len: int = 0

        for w in words:
            palabra = w['word']
            palabra_len = len(palabra) + 1  # +1 por el espacio separador

            # ¿Agregar esta palabra desborda el límite de chars?
            desborda = current_len + palabra_len > max_chars and current_chunk

            # ¿La palabra ANTERIOR terminó en signo de puntuación de corte?
            corte_puntuacion = False
            if current_chunk:
                ultima = current_chunk[-1]['word']
                corte_puntuacion = any(ultima.endswith(p) for p in PUNTUACION_CORTE)

            if (desborda or corte_puntuacion) and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_len = 0

            current_chunk.append(w)
            current_len += palabra_len

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # ========================================================================
    # GENERADORES DE ARCHIVOS
    # ========================================================================

    def _generar_srt(
        self,
        segments: List[Dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Genera el archivo SRT estándar con todos los segmentos."""
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, seg in enumerate(segments, start=1):
                f.write(f"{idx}\n")
                f.write(
                    f"{self._format_time_srt(seg['start'])} --> "
                    f"{self._format_time_srt(seg['end'])}\n"
                )
                f.write(f"{seg['text']}\n\n")
        logger.info(f"SRT generado: {output_path.name} ({len(segments)} entradas)")

    def _generar_ass(
        self,
        segments: List[Dict[str, Any]],
        output_path: Path,
        es_vertical: bool = True,
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> None:
        """Genera ASS básico (fallback cuando no hay word_timestamps)."""
        header = self._get_ass_header(es_vertical, res_x, res_y)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for seg in segments:
                t_start = self._format_time_ass(seg['start'])
                t_end = self._format_time_ass(seg['end'])
                f.write(
                    f"Dialogue: 0,{t_start},{t_end},Terror,,0,0,0,,{seg['text']}\n"
                )
        logger.info(f"ASS (segmentos) generado: {output_path.name}")

    def _generar_ass_por_palabra(
        self,
        words: List[Dict[str, Any]],
        output_path: Path,
        es_vertical: bool = True,
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> None:
        """
        Genera ASS con karaoke palabra a palabra.

        - Chunking por caracteres (no por cantidad fija de palabras)
        - Karaoke \\kf para fill progresivo de izquierda a derecha
        - Color primario blanco, secundario rojo sangre para el fill
        - Tamaño de fuente y márgenes adaptados a la resolución
        """
        max_chars = MAX_CHARS_VERTICAL if es_vertical else MAX_CHARS_HORIZONTAL
        header = self._get_ass_header(es_vertical, res_x, res_y)
        chunks = self._agrupar_palabras_en_chunks(words, max_chars)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for chunk in chunks:
                if not chunk:
                    continue

                t_start_sec = chunk[0]['start']
                t_end_sec   = max(chunk[-1]['end'], t_start_sec + 0.1)
                t_start = self._format_time_ass(t_start_sec)
                t_end   = self._format_time_ass(t_end_sec)

                # \kf<centisegundos> → fill progresivo de izquierda a derecha
                # durante los centisegundos de cada palabra antes de pasar a la siguiente
                texto_ass = ""
                for w in chunk:
                    duracion_cs = max(8, int(round((w['end'] - w['start']) * 100)))
                    texto_ass += f"{{\\kf{duracion_cs}}}{w['word']} "

                f.write(
                    f"Dialogue: 0,{t_start},{t_end},Impacto,,0,0,0,,{texto_ass.strip()}\n"
                )

        logger.info(
            f"ASS (karaoke) generado: {output_path.name} | "
            f"{len(chunks)} líneas | "
            f"{'vertical' if es_vertical else 'horizontal'} {res_x}x{res_y}"
        )

    # ========================================================================
    # CABECERA ASS ADAPTATIVA POR PLATAFORMA
    # ========================================================================

    def _get_ass_header(
        self,
        es_vertical: bool = True,
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> str:
        """
        Genera la cabecera ASS con estilos adaptados a la resolución y orientación.

        Vertical (9:16 / TikTok, Reels, Shorts, Facebook):
            Fuente grande, posición central, márgenes laterales amplios.
        Horizontal (16:9 / YouTube largo):
            Fuente mediana, posición inferior tipo cine, márgenes estándar.
        """
        if es_vertical:
            fontsize_terror  = 110
            fontsize_impacto = 120
            outline_terror   = 7
            outline_impacto  = 9
            shadow    = 0
            alignment = 5      # Centro vertical y horizontal
            margin_l  = 60
            margin_r  = 60
            margin_v  = 420    # Empuja los subs a la zona media-baja
        else:
            fontsize_terror  = 72
            fontsize_impacto = 80
            outline_terror   = 5
            outline_impacto  = 6
            shadow    = 2
            alignment = 2      # Centro-abajo (estilo cine)
            margin_l  = 120
            margin_r  = 120
            margin_v  = 60

        return (
            f"[Script Info]\n"
            f"Title: Subtitulos Paranormales\n"
            f"ScriptType: v4.00+\n"
            f"WrapStyle: 1\n"
            f"ScaledBorderAndShadow: yes\n"
            f"PlayResX: {res_x}\n"
            f"PlayResY: {res_y}\n"
            f"\n"
            f"[V4+ Styles]\n"
            f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            f"OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            f"ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            f"Alignment, MarginL, MarginR, MarginV, Encoding\n"
            # Terror: blanco con borde negro, sin karaoke (fallback)
            f"Style: Terror,"
            f"Bebas Neue,{fontsize_terror},"
            f"&H00FFFFFF,"   # PrimaryColour  : blanco
            f"&H000000FF,"   # SecondaryColour: negro (sin uso en Terror)
            f"&H99000000,"   # OutlineColour  : negro semitransparente
            f"&H00000000,"   # BackColour     : transparente
            f"-1,0,0,0,"     # Bold, Italic, Underline, StrikeOut
            f"100,100,2,0,"  # ScaleX, ScaleY, Spacing, Angle
            f"1,{outline_terror},{shadow},"
            f"{alignment},{margin_l},{margin_r},{margin_v},1\n"
            # Impacto: karaoke con fill rojo sangre (&H000000FF en SecondaryColour)
            f"Style: Impacto,"
            f"Bebas Neue,{fontsize_impacto},"
            f"&H00FFFFFF,"   # PrimaryColour  : blanco (texto sin fill aún)
            f"&H000000FF,"   # SecondaryColour: rojo sangre → fill del karaoke \kf
            f"&H99000000,"   # OutlineColour  : negro semitransparente
            f"&H00000000,"   # BackColour     : transparente
            f"-1,0,0,0,"
            f"100,100,1,0,"  # Spacing 1 → ligeramente más compacto
            f"1,{outline_impacto},{shadow},"
            f"{alignment},{margin_l},{margin_r},{margin_v},1\n"
            f"\n"
            f"[Events]\n"
            f"Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
