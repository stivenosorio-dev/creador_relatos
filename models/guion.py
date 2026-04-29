"""
Esquemas Pydantic del guion JSON para el Creador de Relatos Paranormales.

Define la estructura completa del guion de edición que produce el Director IA.
Cada campo está documentado para servir como contrato entre el Director IA
y el editor humano.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ============================================================================
# COMPONENTES DEL GUION
# ============================================================================

class ConfiguracionAudioRecomendada(BaseModel):
    """Niveles y configuración de audio recomendados para la mezcla."""
    volumen_narracion_db: float = Field(
        default=-6.0,
        description="Volumen de la narración en dBFS. Siempre dominante."
    )
    volumen_musica_fondo_db: float = Field(
        default=-22.0,
        description="Volumen de la música de fondo cuando la narración está activa."
    )
    volumen_musica_en_pausas_db: float = Field(
        default=-14.0,
        description="Volumen de la música cuando hay pausas largas en la narración (>2s)."
    )
    volumen_sfx_ambiente_db: float = Field(
        default=-20.0,
        description="Volumen de efectos de sonido ambientales continuos."
    )
    volumen_sfx_impacto_db: float = Field(
        default=-10.0,
        description="Volumen de efectos de impacto puntuales (sustos, golpes)."
    )
    ducking_activado: bool = Field(
        default=True,
        description="Si True, la música baja automáticamente cuando hay narración."
    )
    fade_in_musica_ms: int = Field(
        default=3000,
        description="Duración del fade-in de la música al inicio del video (milisegundos)."
    )
    fade_out_musica_ms: int = Field(
        default=5000,
        description="Duración del fade-out de la música al final del video (milisegundos)."
    )
    notas_mezcla: str = Field(
        default="",
        description="Notas adicionales del director sobre la mezcla de audio."
    )


class PistaDeFondo(BaseModel):
    """Recomendación de una pista de fondo real para un segmento del video."""
    segmento: str = Field(
        description="Nombre del segmento narrativo: introduccion, desarrollo, climax, cierre."
    )
    tiempo_inicio: str = Field(
        description="Tiempo de inicio del segmento. Formato: HH:MM:SS"
    )
    tiempo_fin: str = Field(
        description="Tiempo de fin del segmento. Formato: HH:MM:SS"
    )
    referencia: str = Field(
        description="Artista y nombre de la pista recomendada. Ej: 'Myuu - Haunted'"
    )
    alternativa: str = Field(
        description="Pista alternativa en caso de no encontrar la principal."
    )
    mood: str = Field(
        description="Estado emocional del segmento: misterio_creciente, tension_sostenida, terror_intenso, inquietud_residual."
    )
    volumen_relativo_sugerido: float = Field(
        default=0.15,
        description="Volumen relativo sugerido (0.0-1.0) para este segmento."
    )
    notas: str = Field(
        default="",
        description="Notas del director sobre cómo usar esta pista en la edición."
    )


class ImagenEscena(BaseModel):
    """Imagen de fondo para un momento específico del video."""
    id: int = Field(
        description="Identificador secuencial de la imagen."
    )
    tiempo_inicio: str = Field(
        description="Momento en que aparece esta imagen. Formato: HH:MM:SS"
    )
    tiempo_fin: str = Field(
        description="Momento en que la imagen sale o transiciona. Formato: HH:MM:SS"
    )
    duracion_segundos: int = Field(
        description="Duración en pantalla de esta imagen en segundos."
    )
    prompt: str = Field(
        description=(
            "Prompt DETALLADO para generar la imagen con IA generativa. "
            "Debe incluir: sujeto, composición, iluminación, paleta de colores, "
            "atmósfera, estilo artístico, y calidad técnica. "
            "En inglés para máxima compatibilidad con IAs generativas."
        )
    )
    transicion_entrada: str = Field(
        default="crossfade_1.5s",
        description="Tipo de transición de entrada: fade_from_black_2s, crossfade_1.5s, cut, etc."
    )
    transicion_salida: str = Field(
        default="crossfade_1.5s",
        description="Tipo de transición de salida hacia la siguiente imagen."
    )
    efecto_movimiento: str = Field(
        default="zoom_lento_in",
        description="Efecto de movimiento: zoom_lento_in, zoom_lento_out, paneo_lento_derecha, paneo_lento_izquierda, estatico, pulso_sutil."
    )
    intensidad_emocional: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Intensidad emocional del momento (1=calma, 10=terror máximo)."
    )
    notas_director: str = Field(
        default="",
        description="Notas del director sobre el propósito narrativo de esta imagen."
    )


class EfectoSonido(BaseModel):
    """Efecto de sonido especial con timing preciso."""
    id: int = Field(
        description="Identificador secuencial del efecto."
    )
    tiempo_exacto: str = Field(
        description="Momento exacto del efecto. Formato: HH:MM:SS"
    )
    duracion_ms: int = Field(
        description="Duración del efecto en milisegundos."
    )
    tipo: str = Field(
        description="Categoría: ambiente, impacto, impacto_extremo, transicion."
    )
    referencia: str = Field(
        description="Nombre descriptivo del sonido: viento_nocturno, crujido_madera, golpe_puerta_seco, etc."
    )
    descripcion: str = Field(
        description="Descripción detallada del efecto y su propósito narrativo."
    )
    volumen_sugerido_db: float = Field(
        default=-15.0,
        description="Volumen sugerido en dBFS."
    )
    fade_in_ms: int = Field(
        default=0,
        description="Fade-in del efecto en milisegundos. 0 para impactos secos."
    )
    fade_out_ms: int = Field(
        default=300,
        description="Fade-out del efecto en milisegundos."
    )


class NotasDirector(BaseModel):
    """Notas generales del Director IA sobre la edición del video."""
    ritmo_narrativo: str = Field(
        description="Indicaciones sobre el ritmo y arco de tensión del video."
    )
    uso_silencios: str = Field(
        description="Estrategia de uso de silencios para generar impacto."
    )
    regla_de_oro_sfx: str = Field(
        description="Directriz sobre la cantidad y uso de efectos de sonido."
    )
    imagenes_principio: str = Field(
        description="Directriz sobre el estilo visual de las imágenes."
    )
    hook_inicial: str = Field(
        description="Estrategia para los primeros segundos del video."
    )
    call_to_action: str = Field(
        default="",
        description="Dónde y cómo incluir un CTA (subscribe, like, follow)."
    )


# ============================================================================
# GUION COMPLETO
# ============================================================================

class Guion(BaseModel):
    """Estructura completa del guion de edición para un relato paranormal."""
    titulo_video: str = Field(
        description="Título atractivo y optimizado para la plataforma destino."
    )
    descripcion: str = Field(
        description="Descripción del video para la plataforma (SEO-optimizada)."
    )
    hashtags: str = Field(
        description="Hashtags relevantes separados por espacios."
    )
    duracion_total_audio: str = Field(
        description="Duración total del audio de narración. Formato: MM:SS"
    )
    plataforma: str = Field(
        description="Plataforma destino: tiktok, youtube_short, instagram_reels, facebook, youtube_largo."
    )
    formato_video: str = Field(
        description="Formato del video: '16:9 (1920x1080)' o '9:16 (1080x1920)'."
    )
    configuracion_audio_recomendada: ConfiguracionAudioRecomendada = Field(
        description="Configuración de niveles de audio para la mezcla."
    )
    pistas_de_fondo_recomendadas: list[PistaDeFondo] = Field(
        description="Lista de pistas de fondo reales recomendadas por segmento."
    )
    imagenes: list[ImagenEscena] = Field(
        description="Secuencia de imágenes con prompts detallados y tiempos exactos."
    )
    efectos_sonidos_especiales: list[EfectoSonido] = Field(
        description="Lista de efectos de sonido con tiempos exactos."
    )
    notas_generales_director: NotasDirector = Field(
        description="Notas y directrices generales del Director IA para la edición."
    )
    thumbnail_sugerido: Optional[str] = Field(
        default=None,
        description="Prompt para generar un thumbnail atractivo (solo YouTube)."
    )


class GuionWrapper(BaseModel):
    """Wrapper raíz del JSON del guion."""
    guion: Guion
