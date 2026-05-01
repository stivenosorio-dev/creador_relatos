"""
🎬 Script Director — Lógica central del Director IA.

Toma el relato, la duración del audio y la plataforma destino, y
orquesta la generación del guion JSON utilizando Ollama.
Verifica y formatea la salida para asegurar que los tiempos sean exactos.
"""

import json
from pathlib import Path
from string import Formatter

from config import PLATAFORMAS
from handlers.ollama_handler import OllamaHandler
from models.guion import GuionWrapper, Guion
from utils.logger import get_logger, print_info, print_warning
from utils.memory_manager import memory_manager

logger = get_logger("script_director")

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SYSTEM_PROMPT_PATH = TEMPLATES_DIR / "system_prompt_director.txt"
USER_PROMPT_PATH = TEMPLATES_DIR / "prompt_guion.txt"


class ScriptDirector:
    """
    Orquesta la creación del guion. Emula a un Director Experto.
    """

    def __init__(self, modelo: str = "llama3.2:3b"):
        self.ollama = OllamaHandler(modelo_override=modelo)

    def generar(
        self,
        relato: str,
        duracion_audio: str,
        plataforma: str,
        output_dir: Path,
    ) -> Path:
        """
        Genera el guion completo para el relato dado.

        Args:
            relato: Texto completo del relato.
            duracion_audio: Duración medida en formato MM:SS.
            plataforma: Nombre de la plataforma (ej: youtube_largo).
            output_dir: Directorio para guardar el guion.json.

        Returns:
            Ruta al archivo guion.json generado.
        """
        memory_manager.pre_module_check("ScriptDirector", estimated_mb=2500)

        # 1. Validar pre-requisitos
        if not self.ollama.is_available():
            raise RuntimeError(
                f"Ollama no está disponible o el modelo '{self.ollama.modelo}' "
                f"no está instalado. Verifica que Ollama esté corriendo."
            )

        plat_config = PLATAFORMAS[plataforma]

        # 2. Cargar templates
        try:
            system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
            base_user_prompt = USER_PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            logger.error(f"Falta un template: {e.filename}")
            raise

        # 3. Preparar Prompts
        schema_json = json.dumps(GuionWrapper.model_json_schema(), ensure_ascii=False, indent=2)

        user_prompt = base_user_prompt.format(
            plataforma=plat_config.nombre_display,
            formato_video=f"{plat_config.aspecto} ({plat_config.resolucion})",
            resolucion=plat_config.resolucion,
            duracion_audio=duracion_audio,
            relato=relato,
            notas_plataforma=plat_config.notas_estrategia,
            schema_json=schema_json
        )

        logger.info(
            f"Director IA preparando guion para {plat_config.nombre_display} "
            f"({duracion_audio})..."
        )

        # 4. Generar con Ollama
        json_crudo = self.ollama.generar_guion_estructurado(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # 5. Validar y procesar JSON
        guion_path = output_dir / "guion.json"
        guion_obj = self._validar_y_guardar(json_crudo, guion_path)

        # 6. Verificación post-generación
        self._verificar_tiempos_contiguos(guion_obj.guion)

        return guion_path

    def _validar_y_guardar(self, json_str: str, output_path: Path) -> GuionWrapper:
        """Parsea, valida con Pydantic y guarda a disco."""
        try:
            # Parsear string a dict
            datos = json.loads(json_str)

            # Validar con Pydantic (esto lanza ValidationError si falta algo)
            guion_wrapper = GuionWrapper(**datos)

            # Guardar bonito
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    guion_wrapper.model_dump(), 
                    f, 
                    ensure_ascii=False, 
                    indent=4
                )
                
            return guion_wrapper
        except json.JSONDecodeError as e:
            logger.error(f"Ollama devolvió JSON inválido: {e}")
            logger.debug(f"JSON crudo: {json_str}")
            raise
        except Exception as e:
            logger.error(f"Error de validación Pydantic del guion: {e}")
            raise

    def _verificar_tiempos_contiguos(self, guion: Guion) -> None:
        """
        Revisa que las imágenes del guion sean contiguas (sin huecos)
        y emite advertencias si detecta problemas.
        """
        imagenes = guion.imagenes
        
        if not imagenes:
            print_warning("El guion no generó imágenes.")
            return

        # Chequear que la priera imagen empiece en 00:00:00
        if imagenes[0].tiempo_inicio not in ("00:00:00", "0:00:00"):
            print_warning(f"La primera imagen no empieza en 00:00:00 (Empieza en {imagenes[0].tiempo_inicio})")

        # Chequear huecos
        for i in range(len(imagenes) - 1):
            actual = imagenes[i]
            siguiente = imagenes[i + 1]
            
            if actual.tiempo_fin != siguiente.tiempo_inicio:
                print_warning(
                    f"Posible hueco entre imágenes {actual.id} y {siguiente.id}: "
                    f"[{actual.tiempo_inicio} - {actual.tiempo_fin}] -> "
                    f"[{siguiente.tiempo_inicio} - {siguiente.tiempo_fin}]"
                )

        logger.info(f"Guion verificado: {len(imagenes)} imágenes planeadas.")
