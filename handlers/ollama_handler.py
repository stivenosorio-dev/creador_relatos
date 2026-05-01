"""
🤖 Ollama Handler — Comunicación con Ollama para generar guiones.

Maneja las peticiones al modelo local de Ollama (ej. llama3.2:3b).
Utiliza Structured Outputs para garantizar que la respuesta del LLM
esté formateada exactamente como requiere el esquema JSON del Guion.
"""

from typing import Dict, Any

import ollama
from ollama import Client

from config import OllamaConfig, OLLAMA_DEFAULT
from models.guion import GuionWrapper
from utils.logger import get_logger, print_warning

logger = get_logger("ollama_handler")


class OllamaHandler:
    """
    Cliente de Ollama que obliga al LLM a responder con un esquema JSON
    estricto basado en modelos Pydantic.
    """

    def __init__(self, config: OllamaConfig = OLLAMA_DEFAULT, modelo_override: str = None):
        self.config = config
        self.modelo = modelo_override or config.modelo
        self.client = Client(host=config.host)

    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo y el modelo está disponible."""
        try:
            modelos = self.client.list()
            nombres_modelos = [m['model'] for m in modelos['models']]
            
            # Buscar coincidencia (ej: "llama3.2" puede aparecer como "llama3.2:latest")
            return any(self.modelo in name for name in nombres_modelos)
        except Exception as e:
            logger.error(f"Error conectando a Ollama en {self.config.host}: {e}")
            return False

    def generar_guion_estructurado(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """
        Envía los prompts a Ollama y fuerza la salida para que cumpla
        con el esquema GuionWrapper.
        
        Args:
            system_prompt: Reglas cinematográficas del Director.
            user_prompt: El relato y datos de duración/plataforma.
            
        Returns:
            JSON crudo (como string) válido según el esquema.
        """
        logger.info(f"Llamando a Ollama (modelo: {self.modelo}) con Structured Output...")
        
        try:
            response = self.client.chat(
                model=self.modelo,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                format=GuionWrapper.model_json_schema(),
                options={
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "num_ctx": self.config.num_ctx,
                }
            )
            
            return response.message.content
        except Exception as e:
            logger.error(f"Error durante la generación con Ollama: {e}")
            raise
