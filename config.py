"""
Configuración global del Creador de Relatos Paranormales V1.
Define perfiles de plataformas, voces TTS, parámetros de audio y modelos IA.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# RUTAS DEL PROYECTO
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ASSETS_DIR = PROJECT_ROOT / "assets"


# ============================================================================
# PERFILES DE PLATAFORMAS
# ============================================================================

@dataclass
class PlataformaConfig:
    """Configuración específica de cada plataforma/red social."""
    nombre: str
    nombre_display: str
    aspecto: str                    # "16:9" o "9:16"
    resolucion: str                 # "1920x1080" o "1080x1920"
    duracion_max_segundos: int
    duracion_min_segundos: int
    duracion_optima_segundos: tuple  # (min_optimo, max_optimo)
    fps: int = 30
    formato_archivo: str = "mp4"
    # Estrategia de contenido
    hook_max_segundos: float = 3.0
    permite_cta_medio: bool = True
    estilo_subtitulos: str = "grande_centrado"
    notas_estrategia: str = ""


PLATAFORMAS = {
    "tiktok": PlataformaConfig(
        nombre="tiktok",
        nombre_display="TikTok",
        aspecto="9:16",
        resolucion="1080x1920",
        duracion_min_segundos=15,
        duracion_max_segundos=600,  # 10 minutos
        duracion_optima_segundos=(60, 180),  # 1-3 minutos ideal
        hook_max_segundos=2.0,
        permite_cta_medio=False,
        estilo_subtitulos="grande_centrado_animado",
        notas_estrategia=(
            "Hook en los primeros 2 segundos. Ritmo rápido. "
            "Subtítulos grandes y animados obligatorios. "
            "Imágenes de alto impacto visual con cambios cada 5-8 segundos. "
            "SFX frecuentes pero sutiles para mantener atención. "
            "La música debe tener ritmo marcado. "
            "Evitar momentos de calma prolongados (>15s)."
        ),
    ),
    "youtube_short": PlataformaConfig(
        nombre="youtube_short",
        nombre_display="YouTube Shorts",
        aspecto="9:16",
        resolucion="1080x1920",
        duracion_min_segundos=15,
        duracion_max_segundos=60,
        duracion_optima_segundos=(30, 58),  # Casi al límite
        hook_max_segundos=2.0,
        permite_cta_medio=False,
        estilo_subtitulos="grande_centrado_animado",
        notas_estrategia=(
            "Máximo 60 segundos. Hook INMEDIATO en 1.5 segundos. "
            "Contar la esencia del relato comprimida. "
            "Subtítulos grandes obligatorios. "
            "Una sola imagen de fondo o máximo 3-4 cambios. "
            "Terminar con gancho para ver el video largo. "
            "Ideal para teasers de relatos largos."
        ),
    ),
    "instagram_reels": PlataformaConfig(
        nombre="instagram_reels",
        nombre_display="Instagram Reels",
        aspecto="9:16",
        resolucion="1080x1920",
        duracion_min_segundos=15,
        duracion_max_segundos=900,  # 15 minutos
        duracion_optima_segundos=(60, 90),  # 1-1.5 minutos ideal
        hook_max_segundos=2.0,
        permite_cta_medio=False,
        estilo_subtitulos="grande_centrado_elegante",
        notas_estrategia=(
            "Estética visual premium obligatoria. Instagram es visual. "
            "Imágenes de altísima calidad con color grading oscuro elegante. "
            "Subtítulos con tipografía estilizada. "
            "Ritmo medio-rápido. Transiciones suaves (crossfade). "
            "Música ambiental con personalidad. "
            "El contenido debe verse 'premium' y 'producido'."
        ),
    ),
    "facebook": PlataformaConfig(
        nombre="facebook",
        nombre_display="Facebook",
        aspecto="9:16",
        resolucion="1080x1920",
        duracion_min_segundos=30,
        duracion_max_segundos=1200,  # 20 minutos
        duracion_optima_segundos=(120, 300),  # 2-5 minutos
        hook_max_segundos=3.0,
        permite_cta_medio=True,
        estilo_subtitulos="grande_centrado",
        notas_estrategia=(
            "Facebook premia los videos largos con buen watch time. "
            "Hook en 3 segundos. Ritmo medio con pausas dramáticas. "
            "Subtítulos OBLIGATORIOS (80% de usuarios ven sin audio). "
            "Imágenes pueden durar más (10-20s). "
            "CTA de compartir/comentar a mitad del video. "
            "Las reacciones de 'Asombro' y 'Tristeza' impulsan el alcance."
        ),
    ),
    "youtube_largo": PlataformaConfig(
        nombre="youtube_largo",
        nombre_display="YouTube (Video Largo)",
        aspecto="16:9",
        resolucion="1920x1080",
        duracion_min_segundos=180,
        duracion_max_segundos=3600,  # 60 minutos
        duracion_optima_segundos=(480, 900),  # 8-15 minutos ideal
        fps=30,
        hook_max_segundos=5.0,
        permite_cta_medio=True,
        estilo_subtitulos="inferior_cinematico",
        notas_estrategia=(
            "Formato cinematográfico horizontal 16:9. "
            "Hook elaborado en los primeros 5 segundos con preview del clímax. "
            "Ritmo narrativo completo: introducción → desarrollo → clímax → cierre. "
            "Imágenes con movimiento Ken Burns (zoom lento, paneo). "
            "Duración de imagen: 10-30 segundos. "
            "Música ambiental continua con ducking. "
            "SFX estratégicos y espaciados. "
            "CTA para suscripción entre desarrollo y clímax. "
            "Pantalla final con recomendaciones. "
            "Chapters/timestamps en la descripción. "
            "Thumbnail sugerido en el guion."
        ),
    ),
}


# ============================================================================
# CONFIGURACIÓN DE AUDIO (TTS)
# ============================================================================

@dataclass
class VozConfig:
    """Configuración de una voz de edge-tts."""
    voice_id: str
    nombre: str
    genero: str
    region: str
    descripcion: str


VOCES_DISPONIBLES = {
    "jorge": VozConfig(
        voice_id="es-MX-JorgeNeural",
        nombre="Jorge",
        genero="masculino",
        region="México",
        descripcion="Profunda, grave, ideal para terror. La mejor para relatos de hoguera.",
    ),
    "gonzalo": VozConfig(
        voice_id="es-CO-GonzaloNeural",
        nombre="Gonzalo",
        genero="masculino",
        region="Colombia",
        descripcion="Clara, envolvente, buen tono narrativo.",
    ),
    "tomas": VozConfig(
        voice_id="es-AR-TomasNeural",
        nombre="Tomás",
        genero="masculino",
        region="Argentina",
        descripcion="Expresiva, con carácter, interesante para relatos dramáticos.",
    ),
    "alvaro": VozConfig(
        voice_id="es-ES-AlvaroNeural",
        nombre="Álvaro",
        genero="masculino",
        region="España",
        descripcion="Seria, narrativa, estilo documental europeo.",
    ),
}

VOZ_DEFAULT = "jorge"  # es-MX-JorgeNeural — la mejor para terror latino


# ============================================================================
# CONFIGURACIÓN DE POST-PROCESAMIENTO DE AUDIO
# ============================================================================

@dataclass
class AudioProcessConfig:
    """Parámetros de la cadena de efectos de post-procesamiento."""
    # High-pass filter
    highpass_cutoff_hz: float = 80.0

    # EQ Paramétrico
    eq_cut_freq_hz: float = 3200.0     # Eliminar dureza robótica
    eq_cut_gain_db: float = -3.0
    eq_cut_q: float = 1.5
    eq_warmth_freq_hz: float = 180.0   # Calidez de hoguera
    eq_warmth_gain_db: float = 2.0
    eq_warmth_q: float = 0.8
    eq_presence_freq_hz: float = 8000.0  # Brillo natural
    eq_presence_gain_db: float = 1.5
    eq_presence_q: float = 1.0

    # Compresor
    comp_threshold_db: float = -18.0
    comp_ratio: float = 3.0
    comp_attack_ms: float = 15.0
    comp_release_ms: float = 150.0

    # De-esser (rango de sibilancia)
    deesser_freq_hz: float = 6500.0
    deesser_threshold_db: float = -22.0

    # Saturación armónica
    saturation_drive_db: float = 2.0
    saturation_mix: float = 0.12       # 12% wet

    # Reverb de sala
    reverb_room_size: float = 0.12
    reverb_damping: float = 0.6
    reverb_wet_level: float = 0.06
    reverb_dry_level: float = 1.0

    # Noise gate
    gate_threshold_db: float = -50.0
    gate_attack_ms: float = 2.0
    gate_release_ms: float = 80.0

    # Limiter
    limiter_threshold_db: float = -1.5

    # Formato de salida
    sample_rate: int = 44100
    output_bitrate: str = "320k"


AUDIO_PROCESS_DEFAULT = AudioProcessConfig()


# ============================================================================
# CONFIGURACIÓN DE OLLAMA
# ============================================================================

@dataclass
class OllamaConfig:
    """Configuración del modelo Ollama para el Director IA."""
    modelo: str = "llama3.2:3b"
    host: str = "http://localhost:11434"
    temperature: float = 0.7       # Creatividad balanceada
    top_p: float = 0.9
    num_ctx: int = 8192            # Contexto amplio para relatos largos
    timeout_seconds: int = 300     # 5 min máx para relatos largos


OLLAMA_DEFAULT = OllamaConfig()


# ============================================================================
# CONFIGURACIÓN DE WHISPER (SUBTÍTULOS)
# ============================================================================

@dataclass
class WhisperConfig:
    """Configuración del modelo faster-whisper para transcripción."""
    model_size: str = "medium"
    device: str = "cpu"            # Auto-detectar GPU en runtime
    compute_type: str = "int8"     # Cuantización para 8GB RAM
    beam_size: int = 3
    language: str = "es"
    word_timestamps: bool = True
    vad_filter: bool = True
    vad_parameters: dict = field(default_factory=lambda: {
        "min_silence_duration_ms": 300,
    })


WHISPER_DEFAULT = WhisperConfig()


# ============================================================================
# CONFIGURACIÓN DE NIVELES DE AUDIO (MEZCLA RECOMENDADA)
# ============================================================================

@dataclass
class NivelesAudioConfig:
    """Niveles de audio recomendados para la mezcla final."""
    narracion_db: float = -6.0
    musica_fondo_db: float = -22.0
    musica_en_pausas_db: float = -14.0
    sfx_ambiente_db: float = -20.0
    sfx_impacto_db: float = -10.0
    ducking_activado: bool = True
    fade_in_musica_ms: int = 3000
    fade_out_musica_ms: int = 5000


NIVELES_AUDIO_DEFAULT = NivelesAudioConfig()


# ============================================================================
# UTILIDADES DE PLATAFORMA
# ============================================================================

def recomendar_plataforma(duracion_segundos: float) -> list[dict]:
    """
    Recomienda las mejores plataformas según la duración del relato.
    Retorna lista ordenada de mejor a peor match.
    """
    recomendaciones = []

    for key, plataforma in PLATAFORMAS.items():
        min_opt, max_opt = plataforma.duracion_optima_segundos

        if min_opt <= duracion_segundos <= max_opt:
            score = 100  # Match perfecto con rango óptimo
        elif plataforma.duracion_min_segundos <= duracion_segundos <= plataforma.duracion_max_segundos:
            # Dentro de los límites pero fuera del óptimo
            if duracion_segundos < min_opt:
                score = 60 - int((min_opt - duracion_segundos) / min_opt * 30)
            else:
                score = 60 - int((duracion_segundos - max_opt) / max_opt * 30)
            score = max(score, 10)
        else:
            score = 0  # Fuera de los límites de la plataforma

        if score > 0:
            recomendaciones.append({
                "plataforma": key,
                "nombre": plataforma.nombre_display,
                "score": score,
                "aspecto": plataforma.aspecto,
                "duracion_optima": f"{min_opt//60}:{min_opt%60:02d} - {max_opt//60}:{max_opt%60:02d}",
                "nota": "✅ Duración óptima" if score == 100 else "⚠️ Viable pero fuera del rango óptimo",
            })

    recomendaciones.sort(key=lambda x: x["score"], reverse=True)
    return recomendaciones


# ============================================================================
# RANGOS DE DURACIÓN PARA RECOMENDACIÓN
# ============================================================================

DURACION_RECOMENDACION = """
┌──────────────────────────────────────────────────┐
│     GUÍA DE DURACIÓN POR PLATAFORMA              │
├──────────────────────────────────────────────────┤
│  YouTube Short   │  30s - 58s   │ 9:16          │
│  TikTok          │  1min - 3min │ 9:16          │
│  Instagram Reels │  1min - 1.5min│ 9:16         │
│  Facebook        │  2min - 5min │ 9:16          │
│  YouTube Largo   │  8min - 15min│ 16:9          │
└──────────────────────────────────────────────────┘
"""
