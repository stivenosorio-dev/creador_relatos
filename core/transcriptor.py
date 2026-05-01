"""
📝 Transcriptor de Subtítulos — Generación de subtítulos SRT y ASS.

Utiliza faster-whisper optimizado para 8GB RAM (int8, CPU).
Extrae tiempos a nivel de palabra para máxima precisión en la sincronización.
Produce dos formatos:
  - SRT: Estándar universal
  - ASS: Subtítulos estilizados (colores, fuentes, animaciones) ideales para horror.
"""

from pathlib import Path
from typing import List, Dict, Any

from faster_whisper import WhisperModel

from config import WhisperConfig, WHISPER_DEFAULT
from utils.logger import get_logger, print_info
from utils.memory_manager import memory_manager

logger = get_logger("transcriptor")


class Transcriptor:
    """
    Generador de subtítulos sincronizados.
    
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
            # El manager ya verificó RAM, cargamos:
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

    def generar(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        """
        Transcribe el audio y genera los archivos de subtítulos.

        Args:
            audio_path: Ruta al archivo de audio (MP3 o WAV).
            output_dir: Directorio donde guardar los subtítulos.

        Returns:
            Tupla con paths (srt_path, ass_path).
        """
        memory_manager.pre_module_check("Transcriptor", estimated_mb=1500)

        self._cargar_modelo()

        logger.info(f"Iniciando transcripción de: {audio_path.name}")
        segments, info = self.model.transcribe(
            str(audio_path),
            beam_size=self.config.beam_size,
            language=self.config.language,
            word_timestamps=self.config.word_timestamps,
            vad_filter=self.config.vad_filter,
            vad_parameters=self.config.vad_parameters,
        )

        logger.info(f"Idioma detectado: {info.language} (p={info.language_probability:.2f})")

        # Recolectar datos
        palabras_transcritas = []
        texto_completo = []

        # List para chunks de SRT estándar (por frase pequeña)
        srt_segments = []
        
        for segment in segments:
            texto_completo.append(segment.text)
            srt_segments.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })
            if self.config.word_timestamps and segment.words:
                for word in segment.words:
                    palabras_transcritas.append({
                        'word': word.word.strip(),
                        'start': word.start,
                        'end': word.end,
                        'probability': word.probability
                    })

        # Generar archivos
        srt_path = output_dir / "subtitulos.srt"
        ass_path = output_dir / "subtitulos.ass"

        self._generar_srt(srt_segments, srt_path)
        
        if self.config.word_timestamps and palabras_transcritas:
            self._generar_ass_por_palabra(palabras_transcritas, ass_path)
        else:
            self._generar_ass(srt_segments, ass_path)

        # Forzar liberación de memoria del modelo
        self.model = None
        
        return srt_path, ass_path

    # ========================================================================
    # UTILIDADES DE FORMATO DE TIEMPO
    # ========================================================================

    def _format_time_srt(self, seconds: float) -> str:
        """Formatea tiempo para SRT: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_time_ass(self, seconds: float) -> str:
        """Formatea tiempo para ASS: H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    # ========================================================================
    # GENERADORES DE ARCHIVOS
    # ========================================================================

    def _generar_srt(self, segments: List[Dict[str, Any]], output_path: Path) -> None:
        """Genera el archivo SRT estándar."""
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, seg in enumerate(segments, start=1):
                f.write(f"{idx}\n")
                f.write(f"{self._format_time_srt(seg['start'])} --> {self._format_time_srt(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
        logger.info(f"Archivo SRT generado: {output_path.name}")

    def _generar_ass(self, segments: List[Dict[str, Any]], output_path: Path) -> None:
        """Genera el archivo ASS con estilos básicos (fallback)."""
        header = self._get_ass_header()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for seg in segments:
                t_start = self._format_time_ass(seg['start'])
                t_end = self._format_time_ass(seg['end'])
                f.write(f"Dialogue: 0,{(t_start)},{(t_end)},Terror,,0,0,0,,{seg['text']}\n")
        logger.info(f"Archivo ASS generado: {output_path.name}")

    def _generar_ass_por_palabra(self, words: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Genera el archivo ASS con estilo dinámico palabra por palabra
        y limitación a 3-4 palabras por línea (ideal cortos/TikTok).
        """
        header = self._get_ass_header()
        
        max_words_per_line = 3
        words_chunks = []
        current_chunk = []
        
        for w in words:
            current_chunk.append(w)
            if len(current_chunk) >= max_words_per_line or w['word'].endswith(('.', ',', '?', '!')):
                words_chunks.append(current_chunk)
                current_chunk = []
                
        if current_chunk:
            words_chunks.append(current_chunk)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            
            for chunk in words_chunks:
                t_start = self._format_time_ass(chunk[0]['start'])
                t_end = self._format_time_ass(chunk[-1]['end'])
                
                # Construir el texto con efecto Karaoke progresivo de aparición y color rojo
                # La palabra actual brilla en rojo, las demás en blanco.
                texto_ass = ""
                for w in chunk:
                    # Duración de la palabra en centisegundos
                    duracion_cs = int((w['end'] - w['start']) * 100)
                    
                    # \K para temporización, \c&H para color
                    # Usando color rojo sangre para el resaltado karaoke {\k..}
                    texto_ass += f"{{\\k{duracion_cs}}}{w['word']} "
                
                # Escribimos el diálogo con el estilo "Impacto" que tiene color secundario rojo
                # El karaoke \kf o \K llenará las palabras sincronizadamente
                f.write(f"Dialogue: 0,{(t_start)},{(t_end)},Impacto,,0,0,0,,{texto_ass.strip()}\n")
                
        logger.info(f"Archivo ASS palabra por palabra generado: {output_path.name}")

    def _get_ass_header(self) -> str:
        """Retorna la cabecera del archivo ASS con los estilos de horror definidos."""
        return """[Script Info]
Title: Subtitulos Paranormales
ScriptType: v4.00+
WrapStyle: 1
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; Letra blanca con sombra oscura (para relato base)
Style: Terror,Bebas Neue,100,&H00FFFFFF,&H000000FF,&H44000000,&H88000000,-1,0,0,0,100,100,2,0,1,6,0,5,50,50,400,1
; Letra con resalte rojo (usado principalmente con el karaoke)
Style: Impacto,Bebas Neue,110,&H00FFFFFF,&H000000FF,&H33000000,&H88000000,-1,0,0,0,100,100,2,0,1,8,0,5,50,50,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
