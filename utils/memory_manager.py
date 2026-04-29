"""
Gestor de memoria RAM para el Creador de Relatos Paranormales.
Monitorea y controla el uso de memoria para operar dentro de 8GB RAM.
"""

import gc
import os
import psutil
from utils.logger import get_logger, print_warning, print_info

logger = get_logger("memory_manager")

# Máximo de RAM que Python debería usar (dejar espacio para SO + Ollama)
MAX_RAM_PYTHON_MB = 4096  # 4GB para Python, 4GB para SO + Ollama


class MemoryManager:
    """
    Gestiona el uso de memoria RAM durante el pipeline.
    
    En un equipo con 8GB, el presupuesto es:
    - ~2.5 GB: Sistema Operativo + servicios
    - ~2.5 GB: Ollama (cuando está activo)
    - ~2.5 GB: Módulo de Python activo (máximo)
    - ~0.5 GB: Margen de seguridad
    
    El pipeline es SECUENCIAL: cada módulo se libera antes del siguiente.
    """

    def __init__(self, max_ram_mb: int = MAX_RAM_PYTHON_MB):
        self.max_ram_mb = max_ram_mb
        self.process = psutil.Process(os.getpid())
        self._peak_usage_mb = 0.0

    def get_ram_usage_mb(self) -> float:
        """Retorna el uso actual de RAM del proceso Python en MB."""
        mem_info = self.process.memory_info()
        usage_mb = mem_info.rss / (1024 * 1024)
        self._peak_usage_mb = max(self._peak_usage_mb, usage_mb)
        return usage_mb

    def get_system_ram_info(self) -> dict:
        """Retorna información general de la RAM del sistema."""
        virtual = psutil.virtual_memory()
        return {
            "total_gb": round(virtual.total / (1024**3), 1),
            "disponible_gb": round(virtual.available / (1024**3), 1),
            "usado_porcentaje": virtual.percent,
            "proceso_python_mb": round(self.get_ram_usage_mb(), 1),
            "pico_python_mb": round(self._peak_usage_mb, 1),
        }

    def check_available(self, required_mb: int = 500) -> bool:
        """
        Verifica si hay suficiente RAM disponible.
        
        Args:
            required_mb: MB de RAM requeridos para la siguiente operación.
        
        Returns:
            True si hay suficiente RAM disponible.
        """
        available = psutil.virtual_memory().available / (1024 * 1024)
        if available < required_mb:
            print_warning(
                f"RAM disponible: {available:.0f}MB (se requieren {required_mb}MB)"
            )
            return False
        return True

    def force_cleanup(self) -> float:
        """
        Forzar liberación de memoria: garbage collection completo.
        
        Returns:
            MB liberados (aproximado).
        """
        before = self.get_ram_usage_mb()

        # Forzar garbage collection
        gc.collect()

        # Liberar caché de PyTorch si está disponible
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        after = self.get_ram_usage_mb()
        freed = max(0, before - after)

        if freed > 10:
            print_info(f"Memoria liberada: {freed:.0f}MB")

        return freed

    def log_status(self, fase: str = "") -> None:
        """Imprime el estado actual de memoria en el log."""
        info = self.get_system_ram_info()
        prefix = f"[{fase}] " if fase else ""
        logger.info(
            f"{prefix}RAM: Python={info['proceso_python_mb']}MB | "
            f"Sistema={info['usado_porcentaje']}% usado | "
            f"Disponible={info['disponible_gb']}GB | "
            f"Pico={info['pico_python_mb']}MB"
        )

    def pre_module_check(self, module_name: str, estimated_mb: int) -> bool:
        """
        Verificación pre-módulo: confirma que hay RAM suficiente.
        
        Args:
            module_name: Nombre del módulo a ejecutar.
            estimated_mb: RAM estimada que usará el módulo.
        
        Returns:
            True si es seguro proceder.
        """
        self.log_status(f"PRE-{module_name}")

        if not self.check_available(estimated_mb):
            print_warning(
                f"⚠️ RAM insuficiente para {module_name}. "
                f"Intentando liberar memoria..."
            )
            self.force_cleanup()

            if not self.check_available(estimated_mb):
                print_warning(
                    f"❌ No hay suficiente RAM para {module_name} "
                    f"(requiere ~{estimated_mb}MB). "
                    f"Considera cerrar otras aplicaciones."
                )
                return False

        return True

    def post_module_cleanup(self, module_name: str) -> None:
        """
        Limpieza post-módulo: libera toda la memoria posible.
        
        Args:
            module_name: Nombre del módulo que terminó.
        """
        self.force_cleanup()
        self.log_status(f"POST-{module_name}")

    def get_summary(self) -> str:
        """Retorna un resumen del uso de memoria durante la ejecución."""
        info = self.get_system_ram_info()
        return (
            f"📊 Resumen de memoria:\n"
            f"   RAM total del sistema: {info['total_gb']}GB\n"
            f"   Pico máximo de Python: {info['pico_python_mb']}MB\n"
            f"   Uso actual: {info['proceso_python_mb']}MB\n"
            f"   RAM del sistema usada: {info['usado_porcentaje']}%"
        )


# Instancia global
memory_manager = MemoryManager()
