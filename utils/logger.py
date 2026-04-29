"""
Logger con Rich para el Creador de Relatos Paranormales.
Proporciona logging estilizado con colores y formato para la consola.
"""

import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

# Tema personalizado para el proyecto
THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "module": "bold magenta",
    "time": "dim white",
})

console = Console(theme=THEME)


def setup_logger(
    name: str = "creador_relatos",
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """
    Configura y retorna un logger con Rich para salida estilizada.

    Args:
        name: Nombre del logger.
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR).
        log_file: Ruta opcional para guardar logs en archivo.

    Returns:
        Logger configurado con Rich.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicar handlers si se llama varias veces
    if logger.handlers:
        return logger

    # Handler de consola con Rich
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # Handler de archivo (opcional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(module_name: str = "creador_relatos") -> logging.Logger:
    """Obtiene el logger del proyecto. Crea uno si no existe."""
    return logging.getLogger(module_name)


# ============================================================================
# FUNCIONES DE CONSOLA DIRECTAS (para mensajes estilizados fuera del logger)
# ============================================================================

def print_header(titulo: str) -> None:
    """Imprime un header estilizado para el inicio de una fase."""
    console.print()
    console.rule(f"[bold magenta]🎬 {titulo}[/bold magenta]", style="magenta")
    console.print()


def print_success(mensaje: str) -> None:
    """Imprime un mensaje de éxito."""
    console.print(f"  [success]✅ {mensaje}[/success]")


def print_warning(mensaje: str) -> None:
    """Imprime un mensaje de advertencia."""
    console.print(f"  [warning]⚠️  {mensaje}[/warning]")


def print_error(mensaje: str) -> None:
    """Imprime un mensaje de error."""
    console.print(f"  [error]❌ {mensaje}[/error]")


def print_info(mensaje: str) -> None:
    """Imprime un mensaje informativo."""
    console.print(f"  [info]ℹ️  {mensaje}[/info]")


def print_step(paso: int, total: int, descripcion: str) -> None:
    """Imprime un paso del pipeline."""
    console.print(
        f"  [module]▶ Paso {paso}/{total}:[/module] {descripcion}"
    )
