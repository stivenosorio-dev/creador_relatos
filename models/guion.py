"""
Esquemas Pydantic del guion JSON para el Creador de Relatos Paranormales.

Define la estructura completa del guion de edición que produce el Director IA.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ConfiguracionAudioRecomendada(BaseModel):
    volumen_narracion_db: float = Field(default=-6.0, description="Volumen de la narración en dBFS.")
    volumen_musica_fondo_db: float = Field(default=-22.0, description="Volumen música con narración activa.")
    volumen_musica_en_pausas_db: float = Field(default=-14.0, description="Volumen música en pausas largas.")
    volumen_sfx_ambiente_db: float = Field(default=-20.0, description="Volumen efectos ambientales continuos.")
    volumen_sfx_impacto_db: float = Field(default=-10.0, description="Volumen efectos de impacto puntuales.")
    ducking_activado: bool = Field(default=True, description="Música baja automáticamente con narración.")
    fade_in_musica_ms: int = Field(default=3000, description="Fade-in de música al inicio (ms).")
    fade_out_musica_ms: int = Field(default=5000, description="Fade-out de música al final (ms).")
    notas_mezcla: str = Field(default="", description="Notas adicionales sobre la mezcla de audio.")


class PistaDeFondo(BaseModel):
    segmento: str = Field(description="Segmento narrativo: introduccion, desarrollo, climax, cierre.")
    tiempo_inicio: str = Field(description="HH:MM:SS")
    tiempo_fin: str = Field(description="HH:MM:SS")
    referencia: str = Field(description="Artista y nombre. Ej: 'Myuu - Haunted'")
    alternativa: str = Field(description="Pista alternativa.")
    mood: str = Field(description="misterio_creciente, tension_sostenida, terror_intenso, inquietud_residual.")
    volumen_relativo_sugerido: float = Field(default=0.15, description="Volumen relativo (0.0-1.0).")
    notas: str = Field(default="", description="Notas sobre uso en edición.")


class ImagenEscena(BaseModel):
    """
    Imagen de fondo para un momento específico del video.

    El campo `prompt` es el núcleo visual del guion. Debe ser lo suficientemente
    rico para que cualquier IA generativa produzca exactamente la imagen correcta
    sin ambigüedad: incluye resolución, composición, iluminación, paleta,
    filtro de color, estilo editorial y detalles técnicos de producción.
    """
    id: int = Field(description="Identificador secuencial (1, 2, 3...).")
    tiempo_inicio: str = Field(description="Momento de aparición. Formato: HH:MM:SS")
    tiempo_fin: str = Field(description="Momento de salida. Formato: HH:MM:SS")
    duracion_segundos: int = Field(description="Duración en pantalla en segundos.")

    prompt: str = Field(
        description=(
            "Prompt ULTRA-DETALLADO en inglés para IA generativa (Midjourney, DALL-E 3, Flux, SD). "
            "DEBE contener TODOS estos bloques en orden:\n"
            "1. SUBJECT: Sujeto principal, acción y estado emocional exacto.\n"
            "2. ENVIRONMENT: Entorno, época, locación con detalles arquitectónicos/naturales precisos.\n"
            "3. COMPOSITION: Tipo de plano (extreme close-up/wide shot/aerial/low-angle), "
            "   regla de tercios, líneas guía, profundidad, espacio negativo.\n"
            "4. LIGHTING: Fuente (moonlight/single candle/lightning flash/neon glow/bioluminescent), "
            "   dirección (rim light/under-light/side light/backlight), "
            "   dureza (hard shadows/soft diffused/fog-filtered/overcast).\n"
            "5. COLOR PALETTE: 3-4 colores hex dominantes. "
            "   Ej: charcoal #0d0d0d, blood red #8b0000, candlelight amber #c8a96e, bone white #f0ede0.\n"
            "6. COLOR GRADING: Nombre del grade cinematográfico aplicado. "
            "   Ej: 'teal-orange horror grade with crushed blacks', "
            "   'desaturated cold blue, bleach bypass', "
            "   'sepia with cyan deep shadows, lifted blacks to dark green', "
            "   'high contrast noir, pushed grain, vignette'.\n"
            "7. ATMOSPHERE: Niebla, lluvia, polvo, humo, partículas de luz, humedad, temperatura visual.\n"
            "8. ARTISTIC STYLE: Referencia visual cinematográfica o artística concreta. "
            "   Ej: 'cinematic still from The Conjuring 2013', "
            "   'dark romanticism oil painting style of Zdzislaw Beksinski', "
            "   'hyperrealistic photography Leica M11 35mm f/1.4 lens', "
            "   'digital matte painting, 8K UHD, film grain'.\n"
            "9. ASPECT RATIO: '--ar 9:16' para plataformas verticales (TikTok/Reels/Shorts/Facebook), "
            "   '--ar 16:9' para YouTube largo. OBLIGATORIO segun plataforma.\n"
            "10. QUALITY TAGS: cinematic, masterpiece, ultra-realistic, sharp focus, "
            "    depth of field, 8K, award-winning photography, film grain.\n"
            "11. NEGATIVE: 'no text, no watermark, no cartoon, no anime, no bright cheerful colors, "
            "    no people smiling, no daylight'.\n"
            "El prompt completo debe tener entre 120 y 200 palabras en inglés."
        )
    )

    aspecto_ratio: str = Field(
        default="9:16",
        description="'9:16' para vertical (TikTok/Reels/Shorts/Facebook), '16:9' para YouTube largo."
    )
    resolucion_objetivo: str = Field(
        default="1080x1920",
        description="'1080x1920' para vertical, '1920x1080' para horizontal."
    )
    grading_cinematografico: str = Field(
        default="",
        description=(
            "Nombre del color grade de esta escena para coherencia visual. "
            "Ej: 'teal-orange horror', 'cold desaturated blue', 'warm sepia climax'. "
            "Debe evolucionar con el arco emocional: frío al inicio, cálido/rojo en el clímax."
        )
    )
    transicion_entrada: str = Field(
        default="crossfade_1.5s",
        description="fade_from_black_2s | crossfade_1.5s | cut | dissolve_lento_3s | flash_blanco_0.1s"
    )
    transicion_salida: str = Field(
        default="crossfade_1.5s",
        description="Transición de salida hacia la siguiente imagen."
    )
    efecto_movimiento: str = Field(
        default="zoom_lento_in",
        description=(
            "Ken Burns para dar vida a la imagen estática: "
            "zoom_lento_in | zoom_lento_out | paneo_lento_derecha | "
            "paneo_lento_izquierda | estatico | pulso_sutil"
        )
    )
    intensidad_emocional: int = Field(
        default=5, ge=1, le=10,
        description="1=calma total, 10=terror máximo/clímax."
    )
    segmento_narrativo: str = Field(
        default="desarrollo",
        description="hook | introduccion | desarrollo | tension | climax | cierre"
    )
    notas_director: str = Field(
        default="",
        description="Propósito narrativo, emoción objetivo y conexión con la narración en ese momento."
    )


class EfectoSonido(BaseModel):
    id: int = Field(description="Identificador secuencial.")
    tiempo_exacto: str = Field(description="HH:MM:SS")
    duracion_ms: int = Field(description="Duración en milisegundos.")
    tipo: str = Field(description="ambiente | impacto | impacto_extremo | transicion")
    referencia: str = Field(description="Nombre del sonido: viento_nocturno, crujido_madera, etc.")
    descripcion: str = Field(description="Descripción y propósito narrativo del efecto.")
    volumen_sugerido_db: float = Field(default=-15.0, description="Volumen en dBFS.")
    fade_in_ms: int = Field(default=0, description="Fade-in en ms. 0 para impactos secos.")
    fade_out_ms: int = Field(default=300, description="Fade-out en ms.")


class NotasDirector(BaseModel):
    ritmo_narrativo: str = Field(description="Ritmo y arco de tensión del video.")
    uso_silencios: str = Field(description="Estrategia de silencios para generar impacto.")
    regla_de_oro_sfx: str = Field(description="Directriz sobre cantidad y uso de efectos.")
    coherencia_visual: str = Field(
        description=(
            "Color grading unificado del video completo. "
            "Indicar LUT/grade dominante y cómo evoluciona por segmento narrativo. "
            "Ej: 'Introducción: azul frío desaturado. Desarrollo: teal-orange. "
            "Clímax: rojo sangre con negros aplastados. Cierre: gris ceniza.'"
        )
    )
    hook_inicial: str = Field(description="Estrategia para los primeros segundos (imagen + audio + texto).")
    call_to_action: str = Field(default="", description="Cuándo y cómo incluir CTA.")
    instrucciones_edicion: str = Field(
        default="",
        description=(
            "Instrucciones técnicas para el editor: software recomendado, "
            "plugins de color, orden de capas, exportación y configuración de subtítulos ASS."
        )
    )


class Guion(BaseModel):
    titulo_video: str = Field(description="Título atractivo optimizado para la plataforma.")
    descripcion: str = Field(description="Descripción SEO-optimizada para la plataforma.")
    hashtags: str = Field(description="Hashtags separados por espacios.")
    duracion_total_audio: str = Field(description="Duración total del audio. Formato: MM:SS")
    plataforma: str = Field(description="tiktok | youtube_short | instagram_reels | facebook | youtube_largo")
    formato_video: str = Field(description="'16:9 (1920x1080)' o '9:16 (1080x1920)'.")
    estilo_visual_global: str = Field(
        default="",
        description=(
            "Estilo visual unificado de todo el video: color grade dominante, "
            "paleta de colores, referencias cinematográficas y reglas de coherencia. "
            "Ej: 'Grade teal-orange desaturado con negros aplastados. "
            "Referencias: The Conjuring 2013, Hereditary 2018. "
            "Imágenes frías al inicio, progresivamente más rojas hacia el clímax.'"
        )
    )
    configuracion_audio_recomendada: ConfiguracionAudioRecomendada
    pistas_de_fondo_recomendadas: list[PistaDeFondo]
    imagenes: list[ImagenEscena] = Field(
        description=(
            "Secuencia de imágenes con prompts ultra-detallados, tiempos exactos, "
            "resolución correcta para la plataforma y metadatos editoriales."
        )
    )
    efectos_sonidos_especiales: list[EfectoSonido]
    notas_generales_director: NotasDirector
    thumbnail_sugerido: Optional[str] = Field(
        default=None,
        description="Prompt completo para thumbnail (solo YouTube). Mismo formato que ImagenEscena.prompt."
    )


class GuionWrapper(BaseModel):
    guion: Guion
