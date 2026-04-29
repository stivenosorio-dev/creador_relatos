"""
🎬 Creador de Relatos Paranormales V1
=====================================
Director y generador de guiones de edición para videos de relatos paranormales.

Entregables:
  - audio_narrativo.mp3  → Narración premium sin rastro de voz sintética
  - subtitulos.srt/.ass  → Subtítulos sincronizados word-level
  - guion.json           → Guion de edición cinematográfico completo

Uso:
  python main.py crear --relato mi_historia.txt
  python main.py crear --relato mi_historia.txt --plataforma youtube_largo
  python main.py audio --relato mi_historia.txt
  python main.py guion --relato mi_historia.txt --duracion "07:23"
  python main.py subtitulos --audio output/audio_narrativo.mp3
  python main.py plataformas --duracion 450
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from config import (
    PLATAFORMAS,
    VOCES_DISPONIBLES,
    VOZ_DEFAULT,
    OUTPUT_DIR,
    recomendar_plataforma,
)
from utils.logger import (
    setup_logger,
    console,
    print_header,
    print_success,
    print_error,
    print_info,
    print_step,
    print_warning,
)
from utils.memory_manager import memory_manager


# ============================================================================
# BANNER Y UTILIDADES
# ============================================================================

BANNER = r"""
[bold red]
   ██████╗██████╗ ███████╗ █████╗ ██████╗  ██████╗ ██████╗
  ██╔════╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
  ██║     ██████╔╝█████╗  ███████║██║  ██║██║   ██║██████╔╝
  ██║     ██╔══██╗██╔══╝  ██╔══██║██║  ██║██║   ██║██╔══██╗
  ╚██████╗██║  ██║███████╗██║  ██║██████╔╝╚██████╔╝██║  ██║
   ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚═╝  ╚═╝
[/bold red]
[bold white]  ██████╗ ███████╗    ██████╗ ███████╗██╗      █████╗ ████████╗ ██████╗ ███████╗
  ██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║     ██╔══██╗╚══██╔══╝██╔═══██╗██╔════╝
  ██║  ██║█████╗      ██████╔╝█████╗  ██║     ███████║   ██║   ██║   ██║███████╗
  ██║  ██║██╔══╝      ██╔══██╗██╔══╝  ██║     ██╔══██║   ██║   ██║   ██║╚════██║
  ██████╔╝███████╗    ██║  ██║███████╗███████╗██║  ██║   ██║   ╚██████╔╝███████║
  ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝[/bold white]

[dim white]  🔥 Director y Generador de Guiones para Relatos Paranormales 🔥[/dim white]
[dim]  v1.0.0 — Contenido inmersivo de hoguera[/dim]
"""


def mostrar_banner():
    """Muestra el banner de la aplicación."""
    console.print(BANNER)


def leer_relato(ruta: str) -> str:
    """Lee el archivo de texto del relato."""
    path = Path(ruta)
    if not path.exists():
        print_error(f"No se encontró el archivo: {ruta}")
        sys.exit(1)
    if not path.suffix in ('.txt', '.md', '.text'):
        print_warning(f"El archivo {ruta} no es .txt pero se intentará leer.")
    
    contenido = path.read_text(encoding='utf-8').strip()
    if not contenido:
        print_error(f"El archivo {ruta} está vacío.")
        sys.exit(1)
    
    return contenido


def crear_directorio_output(titulo: str = "relato") -> Path:
    """Crea el directorio de output para un relato."""
    # Sanitizar el titulo para usarlo como nombre de directorio
    titulo_safe = "".join(
        c if c.isalnum() or c in (' ', '-', '_') else '_'
        for c in titulo
    ).strip().replace(' ', '_')[:60]

    output_path = OUTPUT_DIR / titulo_safe
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


# ============================================================================
# GRUPO DE COMANDOS CLI
# ============================================================================

@click.group()
@click.version_option(version="1.0.0", prog_name="Creador de Relatos Paranormales")
def cli():
    """🎬 Creador de Relatos Paranormales — Director IA de contenido inmersivo."""
    pass


# ============================================================================
# COMANDO: crear (pipeline completo)
# ============================================================================

@cli.command()
@click.option(
    '--relato', '-r',
    required=True,
    type=click.Path(exists=True),
    help='Ruta al archivo de texto con el relato paranormal.'
)
@click.option(
    '--plataforma', '-p',
    type=click.Choice(list(PLATAFORMAS.keys()), case_sensitive=False),
    default=None,
    help='Plataforma destino. Si no se indica, se recomendará automáticamente.'
)
@click.option(
    '--voz', '-v',
    type=click.Choice(list(VOCES_DISPONIBLES.keys()), case_sensitive=False),
    default=VOZ_DEFAULT,
    show_default=True,
    help='Voz del narrador.'
)
@click.option(
    '--modelo', '-m',
    default="llama3.2",
    show_default=True,
    help='Modelo de Ollama para el Director IA.'
)
@click.option(
    '--velocidad-voz',
    default="-5%",
    show_default=True,
    help='Ajuste de velocidad de la voz (ej: -10%, +5%, -5%).'
)
@click.option(
    '--output', '-o',
    default=None,
    help='Directorio de salida personalizado.'
)
def crear(relato, plataforma, voz, modelo, velocidad_voz, output):
    """
    🔥 Pipeline completo: genera audio + subtítulos + guion de edición.

    Ejemplo:
      python main.py crear -r mi_historia.txt -p youtube_largo
    """
    mostrar_banner()
    logger = setup_logger()

    # Leer relato
    print_header("CARGANDO RELATO")
    texto_relato = leer_relato(relato)
    palabras = len(texto_relato.split())
    print_success(f"Relato cargado: {palabras} palabras")

    # Estimar duración (aprox 150 palabras/minuto para narración dramática)
    duracion_estimada_seg = (palabras / 150) * 60
    print_info(f"Duración estimada del audio: {int(duracion_estimada_seg // 60)}:{int(duracion_estimada_seg % 60):02d}")

    # Recomendar plataforma si no se indicó
    if plataforma is None:
        print_header("RECOMENDACIÓN DE PLATAFORMA")
        recomendaciones = recomendar_plataforma(duracion_estimada_seg)
        _mostrar_recomendaciones(recomendaciones)

        if recomendaciones:
            plataforma = recomendaciones[0]["plataforma"]
            print_success(f"Plataforma seleccionada automáticamente: {PLATAFORMAS[plataforma].nombre_display}")
        else:
            print_error("No se encontró una plataforma adecuada para esta duración.")
            sys.exit(1)

    plataforma_config = PLATAFORMAS[plataforma]
    voz_config = VOCES_DISPONIBLES[voz]

    # Crear directorio de output
    output_path = Path(output) if output else crear_directorio_output(
        Path(relato).stem
    )
    output_path.mkdir(parents=True, exist_ok=True)

    # Mostrar configuración
    _mostrar_configuracion(plataforma_config, voz_config, modelo, velocidad_voz, output_path)

    # Verificar memoria
    print_header("VERIFICACIÓN DE SISTEMA")
    memory_manager.log_status("INICIO")

    # ========================================================================
    # PIPELINE
    # ========================================================================

    print_header("PASO 1/3 — GENERANDO AUDIO NARRATIVO")
    print_step(1, 3, f"Generando narración con voz '{voz_config.nombre}' ({voz_config.voice_id})")

    try:
        from core.narrador_tts import NarradorTTS
        narrador = NarradorTTS(voz_config, velocidad_voz)
        audio_path = asyncio.run(narrador.generar(texto_relato, output_path))
        print_success(f"Audio generado: {audio_path}")

        # Obtener duración real
        duracion_real = narrador.obtener_duracion(audio_path)
        duracion_str = f"{int(duracion_real // 60):02d}:{int(duracion_real % 60):02d}"
        print_info(f"Duración real del audio: {duracion_str}")
    except Exception as e:
        print_error(f"Error generando audio: {e}")
        raise

    memory_manager.post_module_cleanup("NarradorTTS")

    # ----- Paso 2: Subtítulos -----
    print_header("PASO 2/3 — GENERANDO SUBTÍTULOS")
    print_step(2, 3, "Transcribiendo audio con faster-whisper")

    try:
        from core.transcriptor import Transcriptor
        transcriptor = Transcriptor()
        srt_path, ass_path = transcriptor.generar(audio_path, output_path)
        print_success(f"Subtítulos SRT: {srt_path}")
        print_success(f"Subtítulos ASS: {ass_path}")
    except Exception as e:
        print_error(f"Error generando subtítulos: {e}")
        raise

    memory_manager.post_module_cleanup("Transcriptor")

    # ----- Paso 3: Guion de edición -----
    print_header("PASO 3/3 — DIRECTOR IA GENERANDO GUION")
    print_step(3, 3, f"El Director IA ({modelo}) está creando el guion de edición...")

    try:
        from core.script_director import ScriptDirector
        director = ScriptDirector(modelo=modelo)
        guion_path = director.generar(
            relato=texto_relato,
            duracion_audio=duracion_str,
            plataforma=plataforma,
            output_dir=output_path,
        )
        print_success(f"Guion de edición: {guion_path}")
    except Exception as e:
        print_error(f"Error generando guion: {e}")
        raise

    memory_manager.post_module_cleanup("ScriptDirector")

    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print_header("✅ PROCESO COMPLETADO")

    resumen_table = Table(title="📦 Entregables Generados", show_header=True)
    resumen_table.add_column("Archivo", style="cyan")
    resumen_table.add_column("Descripción", style="white")
    resumen_table.add_row("🎙️ audio_narrativo.mp3", "Narración premium procesada")
    resumen_table.add_row("📝 subtitulos.srt", "Subtítulos sincronizados")
    resumen_table.add_row("📝 subtitulos.ass", "Subtítulos con estilo horror")
    resumen_table.add_row("📋 guion.json", "Guion de edición completo")
    console.print(resumen_table)

    console.print(f"\n  📂 Ubicación: [bold cyan]{output_path}[/bold cyan]\n")
    console.print(memory_manager.get_summary())


# ============================================================================
# COMANDO: audio (solo generar audio)
# ============================================================================

@cli.command()
@click.option('--relato', '-r', required=True, type=click.Path(exists=True),
              help='Ruta al archivo de texto con el relato.')
@click.option('--voz', '-v', type=click.Choice(list(VOCES_DISPONIBLES.keys())),
              default=VOZ_DEFAULT, show_default=True, help='Voz del narrador.')
@click.option('--velocidad', default="-5%", show_default=True,
              help='Ajuste de velocidad de la voz.')
@click.option('--output', '-o', default=None, help='Directorio de salida.')
def audio(relato, voz, velocidad, output):
    """🎙️ Genera solo el audio narrativo premium."""
    mostrar_banner()
    setup_logger()

    texto = leer_relato(relato)
    voz_config = VOCES_DISPONIBLES[voz]
    output_path = Path(output) if output else crear_directorio_output(Path(relato).stem)
    output_path.mkdir(parents=True, exist_ok=True)

    print_header("GENERANDO AUDIO NARRATIVO")

    from core.narrador_tts import NarradorTTS
    narrador = NarradorTTS(voz_config, velocidad)
    audio_path = asyncio.run(narrador.generar(texto, output_path))
    duracion = narrador.obtener_duracion(audio_path)

    print_success(f"Audio generado: {audio_path}")
    print_info(f"Duración: {int(duracion // 60):02d}:{int(duracion % 60):02d}")


# ============================================================================
# COMANDO: guion (solo generar guion JSON)
# ============================================================================

@cli.command()
@click.option('--relato', '-r', required=True, type=click.Path(exists=True),
              help='Ruta al archivo de texto con el relato.')
@click.option('--duracion', '-d', required=True,
              help='Duración del audio en formato MM:SS (ej: 07:23).')
@click.option('--plataforma', '-p', type=click.Choice(list(PLATAFORMAS.keys())),
              default=None, help='Plataforma destino.')
@click.option('--modelo', '-m', default="llama3.2", show_default=True,
              help='Modelo de Ollama.')
@click.option('--output', '-o', default=None, help='Directorio de salida.')
def guion(relato, duracion, plataforma, modelo, output):
    """📋 Genera solo el guion de edición JSON con el Director IA."""
    mostrar_banner()
    setup_logger()

    texto = leer_relato(relato)
    output_path = Path(output) if output else crear_directorio_output(Path(relato).stem)
    output_path.mkdir(parents=True, exist_ok=True)

    # Recomendar plataforma si no se indicó
    if plataforma is None:
        # Convertir MM:SS a segundos
        partes = duracion.split(':')
        segs = int(partes[0]) * 60 + int(partes[1])
        recs = recomendar_plataforma(segs)
        if recs:
            plataforma = recs[0]["plataforma"]
            print_info(f"Plataforma recomendada: {PLATAFORMAS[plataforma].nombre_display}")
        else:
            plataforma = "youtube_largo"

    print_header("DIRECTOR IA GENERANDO GUION")

    from core.script_director import ScriptDirector
    director = ScriptDirector(modelo=modelo)
    guion_path = director.generar(
        relato=texto,
        duracion_audio=duracion,
        plataforma=plataforma,
        output_dir=output_path,
    )
    print_success(f"Guion generado: {guion_path}")


# ============================================================================
# COMANDO: subtitulos (solo generar subtítulos)
# ============================================================================

@cli.command()
@click.option('--audio', '-a', required=True, type=click.Path(exists=True),
              help='Ruta al archivo de audio (MP3/WAV).')
@click.option('--output', '-o', default=None, help='Directorio de salida.')
def subtitulos(audio, output):
    """📝 Genera solo los subtítulos desde un archivo de audio."""
    mostrar_banner()
    setup_logger()

    audio_path = Path(audio)
    output_path = Path(output) if output else audio_path.parent
    output_path.mkdir(parents=True, exist_ok=True)

    print_header("GENERANDO SUBTÍTULOS")

    from core.transcriptor import Transcriptor
    transcriptor = Transcriptor()
    srt_path, ass_path = transcriptor.generar(audio_path, output_path)
    print_success(f"SRT: {srt_path}")
    print_success(f"ASS: {ass_path}")


# ============================================================================
# COMANDO: plataformas (ver recomendación por duración)
# ============================================================================

@cli.command()
@click.option('--duracion', '-d', required=True, type=float,
              help='Duración del relato en segundos.')
def plataformas(duracion):
    """📊 Muestra las plataformas recomendadas según la duración."""
    mostrar_banner()

    recomendaciones = recomendar_plataforma(duracion)
    minutos = int(duracion // 60)
    segundos = int(duracion % 60)

    console.print(f"\n  ⏱️  Duración del relato: [bold]{minutos}:{segundos:02d}[/bold]\n")
    _mostrar_recomendaciones(recomendaciones)


# ============================================================================
# COMANDO: voces (listar voces disponibles)
# ============================================================================

@cli.command()
def voces():
    """🎤 Muestra las voces disponibles para la narración."""
    mostrar_banner()

    table = Table(title="🎤 Voces Disponibles", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Nombre", style="white")
    table.add_column("Región", style="yellow")
    table.add_column("Voice ID", style="dim")
    table.add_column("Descripción", style="green")

    for key, voz in VOCES_DISPONIBLES.items():
        marker = " ⭐" if key == VOZ_DEFAULT else ""
        table.add_row(
            key + marker,
            voz.nombre,
            voz.region,
            voz.voice_id,
            voz.descripcion,
        )

    console.print(table)
    console.print(f"\n  ⭐ Voz por defecto: [bold cyan]{VOZ_DEFAULT}[/bold cyan]\n")


# ============================================================================
# FUNCIONES AUXILIARES DE DISPLAY
# ============================================================================

def _mostrar_recomendaciones(recomendaciones: list[dict]) -> None:
    """Muestra tabla de recomendaciones de plataforma."""
    table = Table(title="📊 Recomendación de Plataformas", show_header=True)
    table.add_column("Score", style="bold", justify="center")
    table.add_column("Plataforma", style="cyan")
    table.add_column("Aspecto", justify="center")
    table.add_column("Duración Óptima", justify="center")
    table.add_column("Nota", style="dim")

    for rec in recomendaciones:
        score_color = "green" if rec["score"] >= 80 else "yellow" if rec["score"] >= 50 else "red"
        table.add_row(
            f"[{score_color}]{rec['score']}%[/{score_color}]",
            rec["nombre"],
            rec["aspecto"],
            rec["duracion_optima"],
            rec["nota"],
        )

    console.print(table)


def _mostrar_configuracion(plataforma, voz, modelo, velocidad, output_path) -> None:
    """Muestra la configuración del pipeline."""
    config_text = Text()
    config_text.append("\n")

    table = Table(title="⚙️ Configuración", show_header=False, box=None, padding=(0, 2))
    table.add_column("Param", style="dim")
    table.add_column("Valor", style="bold cyan")

    table.add_row("Plataforma", f"{plataforma.nombre_display} ({plataforma.aspecto})")
    table.add_row("Voz", f"{voz.nombre} ({voz.voice_id})")
    table.add_row("Modelo IA", modelo)
    table.add_row("Velocidad voz", velocidad)
    table.add_row("Output", str(output_path))

    console.print(table)
    console.print()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    cli()
