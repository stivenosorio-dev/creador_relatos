#!/usr/bin/env python3
"""
Prueba Kokoro + NarradorTTS (preprocesado, uniones, post-procesado, MP3).

Interfaz simple (Tkinter): pegas o cargas el texto del relato; el MP3 se
guarda solo en _test_kokoro_output/ (nombre con fecha y hora).

  python test_kokoro_config.py

Modo solo consola (sin ventana):

  python test_kokoro_config.py --cli [opciones]
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import VOCES_DISPONIBLES
from core.narrador_tts import NarradorTTS

TEXTO_MUESTRA = """\
La casa llevaba años vacía. Nadie se atrevía a cruzar el umbral al anochecer.
Un ruido seco resonó en el piso de arriba. No había nadie más allí.
¿O sí? El silencio volvió a pesar como plomo."""


def voces_kokoro() -> list[str]:
    return [k for k, v in VOCES_DISPONIBLES.items() if v.motor == "kokoro"]


def _cargar_texto(path: Path | None) -> str:
    if path is None:
        return TEXTO_MUESTRA
    return path.read_text(encoding="utf-8").strip()


def generar_mp3(
    *,
    texto: str,
    mp3_destino: Path,
    voz_key: str,
    velocidad: str,
    pausa_s: float,
    fade_ms: float,
    recorte: float,
    kokoro_speed: float | None = None,
) -> Path:
    """Genera en la carpeta del MP3 y deja el archivo en la ruta indicada."""
    if voz_key not in VOCES_DISPONIBLES:
        raise ValueError(f"Voz desconocida: {voz_key!r}")
    voz = VOCES_DISPONIBLES[voz_key]
    if voz.motor != "kokoro":
        raise ValueError(f"La voz {voz_key!r} no es kokoro.")

    texto = (texto or "").strip()
    if not texto:
        raise ValueError("El guion está vacío.")

    destino = mp3_destino.resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)

    narrador = NarradorTTS(
        voz,
        velocidad=velocidad,
        kokoro_pausa_entre_oraciones_s=pausa_s,
        kokoro_fade_union_ms=fade_ms,
        kokoro_recorte_cola_relativo=recorte,
        kokoro_speed=kokoro_speed,
    )

    generado = asyncio.run(narrador.generar(texto, destino.parent))
    generado = generado.resolve()

    if generado != destino:
        if destino.exists():
            destino.unlink()
        shutil.move(str(generado), str(destino))

    return destino


def main_cli() -> None:
    p = argparse.ArgumentParser(description="Test Kokoro (solo consola)")
    p.add_argument("--voz", default="kokoro_santa")
    p.add_argument("--velocidad", default="-5%")
    p.add_argument("--pausa", type=float, default=0.40, metavar="S")
    p.add_argument("--fade", type=float, default=17.0, metavar="MS")
    p.add_argument("--recorte", type=float, default=0.018, metavar="REL")
    p.add_argument(
        "--kokoro-speed",
        type=float,
        default=None,
        metavar="X",
        help="Velocidad Kokoro (0.5–1.5; <1 más lento). Si se omite, se usa --velocidad estilo edge.",
    )
    p.add_argument("--texto", type=Path, default=None)
    p.add_argument(
        "-o",
        "--output-mp3",
        type=Path,
        default=ROOT / "_test_kokoro_output" / "audio_narrativo.mp3",
        help="Ruta del MP3 final",
    )
    args = p.parse_args()

    texto = _cargar_texto(args.texto)
    mp3 = generar_mp3(
        texto=texto,
        mp3_destino=args.output_mp3,
        voz_key=args.voz,
        velocidad=args.velocidad,
        pausa_s=args.pausa,
        fade_ms=args.fade,
        recorte=args.recorte,
        kokoro_speed=args.kokoro_speed,
    )
    print(f"Listo: {mp3}")


def main_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    kokoro_keys = voces_kokoro()
    if not kokoro_keys:
        print("No hay voces kokoro en config.", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    root.title("Prueba Kokoro")
    root.minsize(520, 480)
    pad = {"padx": 8, "pady": 4}

    out_dir_gui = ROOT / "_test_kokoro_output"

    # --- Relato (lo principal) ---
    ttk.Label(root, text="Texto del relato (pega aquí o carga un .txt)").pack(
        anchor=tk.W, padx=8, pady=(8, 0)
    )
    txt = scrolledtext.ScrolledText(root, height=14, wrap=tk.WORD, font=("Segoe UI", 10))
    txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
    txt.insert("1.0", TEXTO_MUESTRA)

    ttk.Label(
        root,
        text=(
            f"MP3 automático en esta carpeta (nombre con fecha y hora): "
            f"{out_dir_gui.resolve()}"
        ),
        foreground="gray",
        wraplength=640,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, padx=8, pady=(0, 4))

    def cargar_txt() -> None:
        p = filedialog.askopenfilename(
            title="Texto del relato",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if not p:
            return
        try:
            contenido = Path(p).read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Error", str(e), parent=root)
            return
        txt.delete("1.0", tk.END)
        txt.insert("1.0", contenido)

    frm_cargar = ttk.Frame(root)
    frm_cargar.pack(fill=tk.X, padx=8, pady=(0, 6))
    ttk.Button(frm_cargar, text="Cargar .txt…", command=cargar_txt).pack(side=tk.LEFT)

    # --- Voz y velocidad ---
    frm_top = ttk.Frame(root)
    frm_top.pack(fill=tk.X, **pad)
    ttk.Label(frm_top, text="Voz").grid(row=0, column=0, sticky=tk.W)
    var_voz = tk.StringVar(value=kokoro_keys[0])
    ttk.Combobox(frm_top, textvariable=var_voz, values=kokoro_keys, state="readonly", width=28).grid(
        row=0, column=1, sticky=tk.W, padx=(8, 0)
    )

    ttk.Label(frm_top, text="% velocidad Edge (si speed vacío)").grid(
        row=1, column=0, sticky=tk.W, pady=(6, 0)
    )
    var_vel = tk.StringVar(value="-5%")
    ttk.Entry(frm_top, textvariable=var_vel, width=12).grid(
        row=1, column=1, sticky=tk.W, padx=(8, 0), pady=(6, 0)
    )

    # --- Speed Kokoro + pausas / fundido / recorte ---
    frm_num = ttk.LabelFrame(root, text="Kokoro (velocidad, pausas y uniones)")
    frm_num.pack(fill=tk.X, **pad)
    var_k_speed = tk.StringVar(value="")
    var_pausa = tk.StringVar(value="0.40")
    var_fade = tk.StringVar(value="17")
    var_recorte = tk.StringVar(value="0.018")

    def fila_num(r: int, label: str, var: tk.StringVar, w: int = 10) -> None:
        ttk.Label(frm_num, text=label).grid(row=r, column=0, sticky=tk.W, padx=6, pady=3)
        ttk.Entry(frm_num, textvariable=var, width=w).grid(row=r, column=1, sticky=tk.W, pady=3)

    fila_num(0, "Speed Kokoro (1.0=normal; vacío=auto desde %)", var_k_speed, w=8)
    fila_num(1, "Pausa entre oraciones (s)", var_pausa)
    fila_num(2, "Fundido uniones (ms)", var_fade)
    fila_num(3, "Recorte colas (× pico)", var_recorte)

    frm_btns = ttk.Frame(root)
    frm_btns.pack(fill=tk.X, padx=8, pady=8)
    lbl_estado = ttk.Label(root, text="Listo.")
    lbl_estado.pack(anchor=tk.W, padx=8, pady=(0, 4))

    btn_gen = ttk.Button(frm_btns, text="Generar MP3")

    def al_generar() -> None:
        out_dir_gui.mkdir(parents=True, exist_ok=True)
        mp3_path = out_dir_gui / f"kokoro_prueba_{datetime.now():%Y%m%d_%H%M%S}.mp3"

        try:
            pausa = float(var_pausa.get().replace(",", "."))
            fade = float(var_fade.get().replace(",", "."))
            recorte = float(var_recorte.get().replace(",", "."))
        except ValueError:
            messagebox.showerror(
                "Valores", "Pausa, fundido y recorte deben ser números válidos.", parent=root
            )
            return

        ks_raw = var_k_speed.get().strip()
        kokoro_speed: float | None = None
        if ks_raw:
            try:
                kokoro_speed = float(ks_raw.replace(",", "."))
                kokoro_speed = max(0.5, min(1.5, kokoro_speed))
            except ValueError:
                messagebox.showerror(
                    "Speed Kokoro",
                    "Escribe un número (ej. 0,88) o déjalo vacío para usar el % Edge.",
                    parent=root,
                )
                return

        guion = txt.get("1.0", tk.END).strip()
        if not guion:
            messagebox.showwarning(
                "Relato vacío", "Escribe o carga el texto del relato.", parent=root
            )
            return

        voz_key = var_voz.get().strip()
        if voz_key not in VOCES_DISPONIBLES:
            messagebox.showerror("Voz", f"Voz no válida: {voz_key!r}", parent=root)
            return

        btn_gen.configure(state=tk.DISABLED)
        lbl_estado.configure(text="Generando… (puede tardar varios minutos)")

        def trabajo() -> None:
            try:
                final = generar_mp3(
                    texto=guion,
                    mp3_destino=mp3_path,
                    voz_key=voz_key,
                    velocidad=var_vel.get().strip() or "-5%",
                    pausa_s=pausa,
                    fade_ms=fade,
                    recorte=recorte,
                    kokoro_speed=kokoro_speed,
                )

                def ok() -> None:
                    btn_gen.configure(state=tk.NORMAL)
                    lbl_estado.configure(text=f"Guardado: {final}")
                    messagebox.showinfo("Listo", f"MP3 generado:\n{final}", parent=root)

                root.after(0, ok)

            except Exception as e:

                def err() -> None:
                    btn_gen.configure(state=tk.NORMAL)
                    lbl_estado.configure(text="Error.")
                    messagebox.showerror("Error", str(e), parent=root)

                root.after(0, err)

        threading.Thread(target=trabajo, daemon=True).start()

    btn_gen.configure(command=al_generar)
    btn_gen.pack(side=tk.RIGHT, padx=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.argv.pop(1)
        main_cli()
    else:
        main_gui()
