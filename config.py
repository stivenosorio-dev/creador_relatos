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
    """Configuración de una voz TTS."""
    voice_id: str
    nombre: str
    genero: str
    region: str
    descripcion: str
    motor: str = "edge-tts"  # "edge-tts" o "kokoro"


# Motores TTS disponibles
MOTORES_TTS = ["edge-tts", "kokoro"]

VOCES_DISPONIBLES = {
    # --- edge-tts ---
    "jorge": VozConfig(
        voice_id="es-MX-JorgeNeural",
        nombre="Jorge",
        genero="masculino",
        region="México",
        descripcion="Profunda, grave, ideal para terror. La mejor para relatos de hoguera.",
        motor="edge-tts",
    ),
    "gonzalo": VozConfig(
        voice_id="es-CO-GonzaloNeural",
        nombre="Gonzalo",
        genero="masculino",
        region="Colombia",
        descripcion="Clara, envolvente, buen tono narrativo.",
        motor="edge-tts",
    ),
    "tomas": VozConfig(
        voice_id="es-AR-TomasNeural",
        nombre="Tomás",
        genero="masculino",
        region="Argentina",
        descripcion="Expresiva, con carácter, interesante para relatos dramáticos.",
        motor="edge-tts",
    ),
    "alvaro": VozConfig(
        voice_id="es-ES-AlvaroNeural",
        nombre="Álvaro",
        genero="masculino",
        region="España",
        descripcion="Seria, narrativa, estilo documental europeo.",
        motor="edge-tts",
    ),
    # --- kokoro (español) ---
    "kokoro_santa": VozConfig(
        voice_id="em_santa",
        nombre="Kokoro Santa",
        genero="masculino",
        region="Español (Kokoro)",
        descripcion="Voz masculina en español con Kokoro. Profunda y narrativa.",
        motor="kokoro",
    ),
    "kokoro_alex": VozConfig(
        voice_id="em_alex",
        nombre="Kokoro Alex",
        genero="masculino",
        region="Español (Kokoro)",
        descripcion="Voz masculina en español con Kokoro. Clara y enérgica.",
        motor="kokoro",
    ),
    "kokoro_dora": VozConfig(
        voice_id="ef_dora",
        nombre="Kokoro Dora",
        genero="femenino",
        region="Español (Kokoro)",
        descripcion="Voz femenina en español con Kokoro. Cálida y expresiva.",
        motor="kokoro",
    ),
}

VOZ_DEFAULT = "jorge"  # es-MX-JorgeNeural — la mejor para terror latino


@dataclass(frozen=True)
class KokoroNarracionDefaults:
    """
    Valores por defecto del motor Kokoro en NarradorTTS (GUI y CLI).
    Calibrados para relatos; editar aquí si cambias el punto óptimo en test_kokoro_config.
    """

    speed: float = 0.85
    pausa_entre_oraciones_s: float = 0.50
    fade_union_ms: float = 25.0
    recorte_cola_relativo: float = 0.020


KOKORO_NARRACION_DEFAULT = KokoroNarracionDefaults()


def narrador_tts_kwargs_para_voz(voz: VozConfig) -> dict:
    """kwargs extra para NarradorTTS cuando la voz usa motor kokoro (vacío si edge-tts)."""
    if voz.motor != "kokoro":
        return {}
    k = KOKORO_NARRACION_DEFAULT
    return {
        "kokoro_speed": k.speed,
        "kokoro_pausa_entre_oraciones_s": k.pausa_entre_oraciones_s,
        "kokoro_fade_union_ms": k.fade_union_ms,
        "kokoro_recorte_cola_relativo": k.recorte_cola_relativo,
    }


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
# PERFILES DE EDICION DE VOZ (5 presets premium)
# ============================================================================

@dataclass
class AudioEditProfile:
    """
    Perfil de edicion de voz completo.
    Cada perfil define todos los parametros de la cadena de efectos
    mas ajustes de pitch/speed via librosa (aplicados ANTES de pedalboard).
    Un analizador previo mide LUFS, pico, centroide espectral y sibilancia,
    y ajusta dinamicamente ganancia de entrada y umbral del compresor.
    """
    nombre: str
    descripcion: str
    emoji: str
    pitch_semitones: float = 0.0
    speed_factor: float = 1.0
    input_gain_db: float = 0.0
    highpass_cutoff_hz: float = 80.0
    eq_cut_freq_hz: float = 3200.0
    eq_cut_gain_db: float = -3.0
    eq_cut_q: float = 1.5
    eq_warmth_freq_hz: float = 180.0
    eq_warmth_gain_db: float = 2.0
    eq_warmth_q: float = 0.8
    eq_presence_freq_hz: float = 8000.0
    eq_presence_gain_db: float = 1.5
    eq_presence_q: float = 1.0
    eq_nasal_cut_hz: float = 900.0
    eq_nasal_cut_db: float = 0.0
    eq_nasal_cut_q: float = 1.2
    comp_threshold_db: float = -18.0
    comp_ratio: float = 3.0
    comp_attack_ms: float = 15.0
    comp_release_ms: float = 150.0
    deesser_freq_hz: float = 6500.0
    deesser_gain_db: float = -3.0
    saturation_drive_db: float = 2.0
    saturation_active: bool = True
    reverb_room_size: float = 0.10
    reverb_damping: float = 0.65
    reverb_wet_level: float = 0.05
    reverb_dry_level: float = 1.0
    gate_threshold_db: float = -50.0
    gate_attack_ms: float = 2.0
    gate_release_ms: float = 80.0
    limiter_threshold_db: float = -1.5


AUDIO_EDIT_PROFILES: dict[str, AudioEditProfile] = {

    "natural": AudioEditProfile(
        nombre="Voz Natural — Sin Rastros Artificiales", emoji="\U0001f9ec",
        descripcion=(
            "Elimina todos los marcadores de TTS: dureza robotica de 3 kHz, "
            "sibilancia uniforme y ausencia de espacio acustico. "
            "Satura armonicos pares, micro-reverb de sala y compresion suave. "
            "Resultado: indistinguible de voz humana profesional."
        ),
        pitch_semitones=-0.5, speed_factor=0.97, input_gain_db=1.0,
        highpass_cutoff_hz=75.0,
        eq_cut_freq_hz=3100.0, eq_cut_gain_db=-4.5, eq_cut_q=1.8,
        eq_warmth_freq_hz=180.0, eq_warmth_gain_db=3.5, eq_warmth_q=0.7,
        eq_presence_freq_hz=8000.0, eq_presence_gain_db=2.0, eq_presence_q=0.9,
        eq_nasal_cut_hz=900.0, eq_nasal_cut_db=-1.5, eq_nasal_cut_q=1.2,
        comp_threshold_db=-16.0, comp_ratio=3.5, comp_attack_ms=12.0, comp_release_ms=120.0,
        deesser_freq_hz=6800.0, deesser_gain_db=-5.0,
        saturation_drive_db=3.5, saturation_active=True,
        reverb_room_size=0.14, reverb_damping=0.70, reverb_wet_level=0.07,
        gate_threshold_db=-52.0, gate_attack_ms=1.5, gate_release_ms=60.0,
        limiter_threshold_db=-1.0,
    ),

    "fluido": AudioEditProfile(
        nombre="Afinador Fluido — Relatos Calmados", emoji="\U0001f39a",
        descripcion=(
            "Compresion suave estilo radio FM, EQ de presencia elevada para "
            "claridad articulatoria, reverb de sala mediana. "
            "Sin saturacion agresiva. Para audiobooks y misterio suave."
        ),
        pitch_semitones=0.0, speed_factor=0.98, input_gain_db=0.5,
        highpass_cutoff_hz=85.0,
        eq_cut_freq_hz=4000.0, eq_cut_gain_db=-2.0, eq_cut_q=1.0,
        eq_warmth_freq_hz=200.0, eq_warmth_gain_db=2.0, eq_warmth_q=0.9,
        eq_presence_freq_hz=5000.0, eq_presence_gain_db=3.0, eq_presence_q=0.8,
        eq_nasal_cut_hz=0.0, eq_nasal_cut_db=0.0, eq_nasal_cut_q=1.0,
        comp_threshold_db=-15.0, comp_ratio=2.5, comp_attack_ms=20.0, comp_release_ms=200.0,
        deesser_freq_hz=7000.0, deesser_gain_db=-4.0,
        saturation_drive_db=1.2, saturation_active=True,
        reverb_room_size=0.08, reverb_damping=0.80, reverb_wet_level=0.04,
        gate_threshold_db=-48.0, gate_attack_ms=2.0, gate_release_ms=100.0,
        limiter_threshold_db=-1.5,
    ),

    "hoguera": AudioEditProfile(
        nombre="Hoguera Oscura — Terror Inmersivo", emoji="\U0001f525",
        descripcion=(
            "Pitch -2 semitonos, calidez extrema en 150 Hz, compresion agresiva "
            "estilo tape vintage, saturacion alta, reverb de cueva. "
            "Para terror, creepypasta y misterio oscuro."
        ),
        pitch_semitones=-2.0, speed_factor=0.93, input_gain_db=2.0,
        highpass_cutoff_hz=60.0,
        eq_cut_freq_hz=3500.0, eq_cut_gain_db=-5.0, eq_cut_q=2.0,
        eq_warmth_freq_hz=150.0, eq_warmth_gain_db=5.5, eq_warmth_q=0.6,
        eq_presence_freq_hz=6000.0, eq_presence_gain_db=1.0, eq_presence_q=1.2,
        eq_nasal_cut_hz=800.0, eq_nasal_cut_db=-2.0, eq_nasal_cut_q=1.4,
        comp_threshold_db=-14.0, comp_ratio=5.0, comp_attack_ms=8.0, comp_release_ms=200.0,
        deesser_freq_hz=6000.0, deesser_gain_db=-6.5,
        saturation_drive_db=5.5, saturation_active=True,
        reverb_room_size=0.22, reverb_damping=0.50, reverb_wet_level=0.12,
        gate_threshold_db=-46.0, gate_attack_ms=3.0, gate_release_ms=100.0,
        limiter_threshold_db=-1.5,
    ),

    "podcast": AudioEditProfile(
        nombre="Podcast Oscuro Profesional", emoji="\U0001f399",
        descripcion=(
            "Sonido broadcast de alta gama: compresion de radio ratio 4:1, "
            "de-essing agresivo, EQ de presencia de microfono condensador. "
            "Para true crime, conspiracion, paranormal."
        ),
        pitch_semitones=0.0, speed_factor=0.98, input_gain_db=1.5,
        highpass_cutoff_hz=85.0,
        eq_cut_freq_hz=4000.0, eq_cut_gain_db=-2.0, eq_cut_q=1.0,
        eq_warmth_freq_hz=200.0, eq_warmth_gain_db=2.0, eq_warmth_q=0.9,
        eq_presence_freq_hz=5000.0, eq_presence_gain_db=3.5, eq_presence_q=0.8,
        eq_nasal_cut_hz=950.0, eq_nasal_cut_db=-1.5, eq_nasal_cut_q=1.2,
        comp_threshold_db=-14.0, comp_ratio=4.0, comp_attack_ms=10.0, comp_release_ms=100.0,
        deesser_freq_hz=7000.0, deesser_gain_db=-5.5,
        saturation_drive_db=1.8, saturation_active=True,
        reverb_room_size=0.06, reverb_damping=0.85, reverb_wet_level=0.03,
        gate_threshold_db=-44.0, gate_attack_ms=1.0, gate_release_ms=50.0,
        limiter_threshold_db=-1.0,
    ),

    "misterio": AudioEditProfile(
        nombre="Misterio Suave — Suspenso Elegante", emoji="\U0001f32b",
        descripcion=(
            "Reverb de sala grande para soledad y espacio, compresion suave-media, "
            "pitch -0.8 st y velocidad reducida para tension controlada. "
            "Para thriller psicologico y suspenso sin terror extremo."
        ),
        pitch_semitones=-0.8, speed_factor=0.95, input_gain_db=1.0,
        highpass_cutoff_hz=80.0,
        eq_cut_freq_hz=3300.0, eq_cut_gain_db=-3.0, eq_cut_q=1.5,
        eq_warmth_freq_hz=160.0, eq_warmth_gain_db=3.0, eq_warmth_q=0.75,
        eq_presence_freq_hz=7000.0, eq_presence_gain_db=2.5, eq_presence_q=1.0,
        eq_nasal_cut_hz=900.0, eq_nasal_cut_db=-1.0, eq_nasal_cut_q=1.2,
        comp_threshold_db=-16.0, comp_ratio=3.0, comp_attack_ms=18.0, comp_release_ms=180.0,
        deesser_freq_hz=6500.0, deesser_gain_db=-4.0,
        saturation_drive_db=2.0, saturation_active=True,
        reverb_room_size=0.18, reverb_damping=0.55, reverb_wet_level=0.09,
        gate_threshold_db=-50.0, gate_attack_ms=2.5, gate_release_ms=90.0,
        limiter_threshold_db=-1.5,
    ),
}

AUDIO_EDIT_PROFILE_DEFAULT = "natural"


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
