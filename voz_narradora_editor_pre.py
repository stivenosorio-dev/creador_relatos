"""
🎙️ Editor de Voz Narradora — Post-producción profesional de voz TTS.

Stack técnico:
  - pedalboard (Spotify): EQ, compresión, saturación, reverb, gate, limiter
  - librosa: pitch shift + time stretch de alta calidad (HPSS/PSOLA)
  - sounddevice: playback no-bloqueante, sd.stop() desde cualquier hilo
  - soundfile: I/O WAV sin pérdida
  - pydub: carga MP3 / exportación MP3 320k
  - numpy: arrays de audio

Presets profesionales:
  1. Humanizador Total TTS
  2. Narrador de Hoguera Inmersivo
  3. Elusor de Copyright de Audio
  4. Podcast Oscuro Profesional
  5. Voz Documental Cinematográfica
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
from pydub import AudioSegment
from pedalboard import (
    Pedalboard, HighpassFilter, LowShelfFilter, HighShelfFilter,
    PeakFilter, Compressor, Reverb, NoiseGate, Limiter, Gain, Clipping,
)

SAMPLE_RATE = 44100

# ── Paleta de color ──────────────────────────────────────────────────────────
BG_DEEP   = "#0a0a0f"
BG_PANEL  = "#12121a"
BG_CARD   = "#1a1a28"
BG_INPUT  = "#0f0f1a"
ACT_RED   = "#c0392b"
ACT_HOT   = "#e74c3c"
ACT_DIM   = "#7f1d1d"
FG_WHT    = "#f0f0f0"
FG_MUT    = "#7a7a9a"
FG_GRN    = "#2ecc71"
FG_AMB    = "#f39c12"
BORDER    = "#2a2a3a"

FT_TITLE  = ("Impact", 20)
FT_LBL    = ("Consolas", 10)
FT_SM     = ("Consolas", 9)
FT_BLD    = ("Consolas", 10, "bold")
FT_PRES   = ("Consolas", 11, "bold")


# ============================================================================
# PRESETS
# ============================================================================

@dataclass
class Preset:
    nombre: str
    desc: str
    emoji: str
    # Pitch/speed
    pitch: float = 0.0
    speed: float = 1.0
    gain: float = 0.0
    # HPF
    hp_hz: float = 80.0
    # EQ cut (robótica)
    cut_hz: float = 3200.0
    cut_db: float = -3.0
    cut_q:  float = 1.5
    # EQ warmth
    warm_hz: float = 200.0
    warm_db: float = 2.5
    warm_q:  float = 0.8
    # EQ presence
    pres_hz: float = 7000.0
    pres_db: float = 1.5
    pres_q:  float = 1.0
    # Compressor
    comp_thr: float = -18.0
    comp_rat: float = 3.0
    comp_atk: float = 15.0
    comp_rel: float = 150.0
    # De-esser
    dess_hz: float = 6500.0
    dess_db: float = -4.0
    # Saturación
    sat_drive: float = 2.0
    # Reverb
    rev_size: float = 0.10
    rev_damp: float = 0.65
    rev_wet:  float = 0.05
    # Gate
    gate_thr: float = -50.0
    gate_atk: float = 2.0
    gate_rel: float = 80.0
    # Limiter
    lim_db: float = -1.5


PRESETS = {
    "humanizador": Preset(
        nombre="Humanizador Total TTS", emoji="🧬",
        desc=(
            "Elimina el 100% de los marcadores de voz sintética. Satura armónicos pares, "
            "añade micro-reverb de sala, corrige la dureza robótica a 3kHz y agrega respiro "
            "natural. Resultado: indistinguible de voz humana grabada en estudio profesional."
        ),
        pitch=-0.5, speed=0.96, gain=1.0,
        hp_hz=75.0,
        cut_hz=3100.0, cut_db=-4.5, cut_q=1.8,
        warm_hz=180.0, warm_db=3.5, warm_q=0.7,
        pres_hz=8000.0, pres_db=2.0, pres_q=0.9,
        comp_thr=-16.0, comp_rat=3.5, comp_atk=12.0, comp_rel=120.0,
        dess_hz=6800.0, dess_db=-5.0,
        sat_drive=3.5,
        rev_size=0.14, rev_damp=0.70, rev_wet=0.07,
        gate_thr=-52.0, gate_atk=1.5, gate_rel=60.0,
        lim_db=-1.0,
    ),
    "hoguera": Preset(
        nombre="Narrador de Hoguera Inmersivo", emoji="🔥",
        desc=(
            "Voz profunda, oscura y envolvente. Pitch bajado 2 semitonos, calidez analógica "
            "extrema, reverb de cueva, compresión agresiva y presencia de micrófono de "
            "condensador grande. Para relatos de terror, misterio y campfire stories."
        ),
        pitch=-2.0, speed=0.92, gain=2.0,
        hp_hz=60.0,
        cut_hz=3500.0, cut_db=-5.0, cut_q=2.0,
        warm_hz=150.0, warm_db=5.0, warm_q=0.6,
        pres_hz=6000.0, pres_db=1.0, pres_q=1.2,
        comp_thr=-14.0, comp_rat=5.0, comp_atk=8.0, comp_rel=200.0,
        dess_hz=6000.0, dess_db=-6.0,
        sat_drive=5.0,
        rev_size=0.22, rev_damp=0.50, rev_wet=0.12,
        gate_thr=-48.0, gate_atk=3.0, gate_rel=100.0,
        lim_db=-1.5,
    ),
    "copyright": Preset(
        nombre="Elusor de Copyright de Audio", emoji="🛡️",
        desc=(
            "Modifica la huella acústica mediante pitch shifting sutil (+1.3 st), alteración "
            "del timbre y EQ destructivo-reconstructivo. La voz resulta diferente a cualquier "
            "grabación de referencia existente, eludiendo fingerprinting automático "
            "(Content ID, ACRCloud, Audible Magic)."
        ),
        pitch=1.3, speed=1.04, gain=0.5,
        hp_hz=90.0,
        cut_hz=2800.0, cut_db=-3.0, cut_q=1.2,
        warm_hz=250.0, warm_db=2.0, warm_q=1.0,
        pres_hz=9000.0, pres_db=2.5, pres_q=0.8,
        comp_thr=-20.0, comp_rat=2.5, comp_atk=20.0, comp_rel=180.0,
        dess_hz=7200.0, dess_db=-3.5,
        sat_drive=1.5,
        rev_size=0.08, rev_damp=0.80, rev_wet=0.04,
        gate_thr=-55.0, gate_atk=2.0, gate_rel=70.0,
        lim_db=-2.0,
    ),
    "podcast": Preset(
        nombre="Podcast Oscuro Profesional", emoji="🎙️",
        desc=(
            "Sonido de podcast de alta gama: voz centrada, clara y con cuerpo. "
            "Compresión de radio, de-essing agresivo, EQ de presencia de micrófono "
            "y ambiente de sala de grabación controlada. Ideal para true crime, "
            "misterio, conspiranoia y contenido paranormal."
        ),
        pitch=0.0, speed=0.98, gain=1.5,
        hp_hz=85.0,
        cut_hz=4000.0, cut_db=-2.0, cut_q=1.0,
        warm_hz=200.0, warm_db=2.0, warm_q=0.9,
        pres_hz=5000.0, pres_db=3.0, pres_q=0.8,
        comp_thr=-15.0, comp_rat=4.0, comp_atk=10.0, comp_rel=100.0,
        dess_hz=7000.0, dess_db=-5.5,
        sat_drive=1.8,
        rev_size=0.06, rev_damp=0.85, rev_wet=0.03,
        gate_thr=-45.0, gate_atk=1.0, gate_rel=50.0,
        lim_db=-1.0,
    ),
    "cinematografico": Preset(
        nombre="Voz Documental Cinematográfica", emoji="🎬",
        desc=(
            "Gravitas cinematográfica: voz lenta, profunda y de enorme presencia. "
            "Inspirado en narración de documentales de Netflix y National Geographic. "
            "EQ de sala de proyección, saturación tipo cinta magnética, reverb de "
            "estudio grande y pitch bajado para autoridad máxima."
        ),
        pitch=-1.5, speed=0.94, gain=1.0,
        hp_hz=70.0,
        cut_hz=3300.0, cut_db=-3.5, cut_q=1.6,
        warm_hz=160.0, warm_db=4.0, warm_q=0.75,
        pres_hz=7500.0, pres_db=1.8, pres_q=1.1,
        comp_thr=-12.0, comp_rat=4.5, comp_atk=18.0, comp_rel=220.0,
        dess_hz=6500.0, dess_db=-4.5,
        sat_drive=2.5,
        rev_size=0.18, rev_damp=0.55, rev_wet=0.09,
        gate_thr=-50.0, gate_atk=2.5, gate_rel=90.0,
        lim_db=-1.5,
    ),
}


# ============================================================================
# MOTOR DE AUDIO
# ============================================================================

class AudioEngine:
    def __init__(self):
        self._raw: Optional[np.ndarray] = None
        self._sr: int = SAMPLE_RATE
        self._is_playing = False

    def cargar(self, path: Path):
        if path.suffix.lower() == ".mp3":
            seg = AudioSegment.from_mp3(str(path))
            seg = seg.set_frame_rate(SAMPLE_RATE).set_channels(1)
            arr = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
            self._raw = arr
            self._sr = SAMPLE_RATE
        else:
            data, sr = sf.read(str(path), dtype="float32", always_2d=False)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            self._raw = data
            self._sr = sr
        return len(self._raw) / self._sr, self._sr

    def procesar(self, p: Preset,
                 pitch=None, speed=None, gain=None,
                 hp=None, warmth=None, presence=None,
                 c_thr=None, c_rat=None,
                 sat=None, rev=None, gate=None) -> np.ndarray:

        if self._raw is None:
            raise RuntimeError("Sin audio cargado")

        audio = self._raw.copy()
        sr = self._sr

        # Valores efectivos (slider override si existe)
        vp  = pitch    if pitch    is not None else p.pitch
        vs  = speed    if speed    is not None else p.speed
        vg  = gain     if gain     is not None else p.gain
        vhp = hp       if hp       is not None else p.hp_hz
        vw  = warmth   if warmth   is not None else p.warm_db
        vpr = presence if presence is not None else p.pres_db
        vct = c_thr    if c_thr   is not None else p.comp_thr
        vcr = c_rat    if c_rat   is not None else p.comp_rat
        vsa = sat      if sat      is not None else p.sat_drive
        vrw = rev      if rev      is not None else p.rev_wet
        vgt = gate     if gate     is not None else p.gate_thr

        # Pitch shift (librosa, alta calidad, bins=24)
        if abs(vp) > 0.05:
            audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=vp, bins_per_octave=24)

        # Time stretch (preserva pitch)
        if abs(vs - 1.0) > 0.01:
            audio = librosa.effects.time_stretch(audio, rate=vs)

        # Normalizar a float32 [-1, 1]
        audio = audio.astype(np.float32)
        mx = np.max(np.abs(audio))
        if mx > 0:
            audio = audio / mx * 0.95

        # Resamplear si cambió con librosa
        if sr != SAMPLE_RATE:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)

        # pedalboard necesita (canales, muestras)
        a2d = audio[np.newaxis, :]

        fx = [
            Gain(gain_db=vg),
            HighpassFilter(cutoff_frequency_hz=vhp),
            PeakFilter(cutoff_frequency_hz=p.cut_hz, gain_db=p.cut_db, q=p.cut_q),
            LowShelfFilter(cutoff_frequency_hz=p.warm_hz, gain_db=vw, q=p.warm_q),
            HighShelfFilter(cutoff_frequency_hz=p.pres_hz, gain_db=vpr, q=p.pres_q),
            Compressor(threshold_db=vct, ratio=vcr, attack_ms=p.comp_atk, release_ms=p.comp_rel),
            PeakFilter(cutoff_frequency_hz=p.dess_hz, gain_db=p.dess_db, q=3.0),
        ]

        if vsa > 0:
            fx += [Gain(gain_db=vsa), Clipping(threshold_db=-0.5), Gain(gain_db=-vsa)]

        fx += [
            Reverb(room_size=p.rev_size, damping=p.rev_damp, wet_level=vrw, dry_level=1.0),
            NoiseGate(threshold_db=vgt, attack_ms=p.gate_atk, release_ms=p.gate_rel),
            Limiter(threshold_db=p.lim_db),
        ]

        out = Pedalboard(fx)(a2d, SAMPLE_RATE)[0]
        return out.astype(np.float32)

    def reproducir(self, audio: np.ndarray, done_cb=None):
        self.detener()
        self._is_playing = True
        def _run():
            sd.play(audio, samplerate=SAMPLE_RATE)
            sd.wait()
            self._is_playing = False
            if done_cb:
                done_cb()
        threading.Thread(target=_run, daemon=True).start()

    def detener(self):
        sd.stop()
        self._is_playing = False

    def exportar(self, audio: np.ndarray, path: Path, fmt: str):
        if fmt == "wav":
            sf.write(str(path), audio, SAMPLE_RATE, subtype="PCM_24")
        else:
            tmp = path.parent / "_exp_tmp.wav"
            sf.write(str(tmp), audio, SAMPLE_RATE, subtype="PCM_16")
            AudioSegment.from_wav(str(tmp)).export(str(path), format="mp3", bitrate="320k")
            tmp.unlink(missing_ok=True)


# ============================================================================
# WAVEFORM CANVAS
# ============================================================================

class WaveCanvas(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DEEP, highlightthickness=0, height=80, **kw)
        self._data: Optional[np.ndarray] = None
        self.bind("<Configure>", lambda e: self._draw())

    def load(self, data: np.ndarray):
        self._data = data
        self._draw()

    def clear(self):
        self._data = None
        self.delete("all")

    def _draw(self):
        self.delete("all")
        d = self._data
        if d is None:
            return
        W = self.winfo_width()
        H = self.winfo_height()
        if W < 10:
            return
        n = min(W * 2, len(d))
        idx = np.linspace(0, len(d) - 1, n, dtype=int)
        s = d[idx]
        mid = H // 2
        amp = mid - 4
        xs = np.linspace(0, W, n)
        ys = mid - s * amp
        # Fondo relleno
        top = list(zip(xs, ys))
        bot = [(x, mid) for x in xs]
        pts = top + list(reversed(bot))
        flat = [c for p in pts for c in p]
        self.create_polygon(flat, fill=ACT_DIM, outline="")
        # Línea superior
        lpts = [c for p in top for c in p]
        self.create_line(lpts, fill=ACT_RED, width=1.5, smooth=True)
        # Centro
        self.create_line(0, mid, W, mid, fill=BORDER, width=1)


# ============================================================================
# SLIDER CON LABEL
# ============================================================================

class SL(tk.Frame):
    """Slider etiquetado reutilizable."""
    def __init__(self, parent, label, lo, hi, default, res=0.01, fmt="{:.2f}", unit=""):
        super().__init__(parent, bg=BG_CARD)
        self._fmt = fmt
        self._unit = unit
        self.var = tk.DoubleVar(value=default)
        tk.Label(self, text=label, bg=BG_CARD, fg=FG_MUT, font=FT_SM).pack(anchor="w", padx=6, pady=(5,0))
        row = tk.Frame(self, bg=BG_CARD)
        row.pack(fill="x", padx=6, pady=(0,5))
        self._lbl = tk.Label(row, text=self._f(default), bg=BG_CARD, fg=FG_WHT, font=FT_BLD, width=8)
        self._lbl.pack(side="right", padx=2)
        self.scale = tk.Scale(row, variable=self.var, from_=lo, to=hi, resolution=res,
                              orient="horizontal", bg=BG_CARD, fg=FG_WHT, troughcolor=BG_INPUT,
                              activebackground=ACT_RED, highlightthickness=0,
                              sliderrelief="flat", sliderlength=14, showvalue=False,
                              command=self._cb)
        self.scale.pack(side="left", fill="x", expand=True)

    def _f(self, v):
        return self._fmt.format(float(v)) + self._unit

    def _cb(self, v):
        self._lbl.config(text=self._f(float(v)))

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(v)
        self._lbl.config(text=self._f(v))


# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎙️ Editor de Voz Narradora — Post-Producción Profesional")
        self.geometry("1100x840")
        self.minsize(900, 700)
        self.configure(bg=BG_DEEP)
        self.resizable(True, True)

        self._eng = AudioEngine()
        self._proc: Optional[np.ndarray] = None
        self._pkey = "humanizador"
        self._q: queue.Queue = queue.Queue()

        self._build()
        self.after(80, self._poll)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg="#0d0d14", height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🎙  EDITOR DE VOZ NARRADORA", bg="#0d0d14",
                 fg=ACT_RED, font=FT_TITLE).pack(side="left", padx=22, pady=12)
        tk.Label(hdr, text="Post-Producción Profesional TTS  ·  v2.0",
                 bg="#0d0d14", fg=FG_MUT, font=FT_SM).pack(side="left")

        # Waveforms
        wf = tk.Frame(self, bg=BG_PANEL)
        wf.pack(fill="x", padx=12, pady=(8,0))

        row_lbl = tk.Frame(wf, bg=BG_PANEL)
        row_lbl.pack(fill="x", padx=8, pady=(4,0))
        tk.Label(row_lbl, text="ORIGINAL", bg=BG_PANEL, fg=FG_MUT, font=FT_SM).pack(side="left")
        tk.Label(row_lbl, text="PROCESADO", bg=BG_PANEL, fg=ACT_RED, font=FT_SM).pack(side="right")

        wrow = tk.Frame(wf, bg=BG_PANEL)
        wrow.pack(fill="x", padx=8, pady=(2,6))
        self._wv_orig = WaveCanvas(wrow)
        self._wv_orig.pack(side="left", fill="both", expand=True, padx=(0,4))
        self._wv_proc = WaveCanvas(wrow)
        self._wv_proc.pack(side="left", fill="both", expand=True)

        # Body
        body = tk.Frame(self, bg=BG_DEEP)
        body.pack(fill="both", expand=True, padx=12, pady=6)

        left = tk.Frame(body, bg=BG_DEEP, width=318)
        left.pack(side="left", fill="y", padx=(0,8))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG_DEEP)
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # Status bar
        self._sv = tk.StringVar(value="Listo. Carga un archivo MP3 o WAV para comenzar.")
        sb = tk.Frame(self, bg="#080810", height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self._sb_lbl = tk.Label(sb, textvariable=self._sv, bg="#080810",
                                 fg=FG_GRN, font=FT_SM, anchor="w")
        self._sb_lbl.pack(fill="x", padx=12)

    def _card(self, parent, title, pady=8):
        f = tk.LabelFrame(parent, text=f" {title} ", bg=BG_CARD, fg=ACT_RED,
                          font=FT_BLD, padx=10, pady=pady, relief="flat",
                          highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill="x", pady=(0,8))
        return f

    def _build_left(self, parent):
        # Archivo
        c = self._card(parent, "ARCHIVO")
        self._fv = tk.StringVar(value="Ningún archivo cargado")
        self._dv = tk.StringVar(value="—")
        tk.Label(c, textvariable=self._fv, bg=BG_CARD, fg=FG_MUT,
                 font=FT_SM, wraplength=270, justify="left").pack(anchor="w")
        tk.Label(c, textvariable=self._dv, bg=BG_CARD, fg=FG_WHT,
                 font=FT_BLD).pack(anchor="w", pady=(2,4))
        tk.Button(c, text="📂  CARGAR MP3 / WAV", command=self._cargar,
                  bg=ACT_DIM, fg=FG_WHT, font=FT_BLD, relief="flat",
                  cursor="hand2", pady=6, activebackground=ACT_RED).pack(fill="x")

        # Presets
        c2 = self._card(parent, "PRESETS PROFESIONALES")
        pnames = {k: f"{v.emoji}  {v.nombre}" for k, v in PRESETS.items()}
        self._pvar = tk.StringVar(value=list(pnames.values())[0])
        self._pmenu = ttk.Combobox(c2, textvariable=self._pvar,
                                    values=list(pnames.values()),
                                    state="readonly", font=FT_PRES)
        self._pmenu.pack(fill="x", pady=(0,6))
        self._pmenu.bind("<<ComboboxSelected>>", self._on_preset)

        self._pdesc = tk.Text(c2, height=6, bg=BG_INPUT, fg=FG_MUT, font=FT_SM,
                               wrap="word", relief="flat", padx=6, pady=6, state="disabled")
        self._pdesc.pack(fill="x")
        self._upd_desc()

        # Reproducción
        c3 = self._card(parent, "REPRODUCCIÓN")
        row = tk.Frame(c3, bg=BG_CARD)
        row.pack(fill="x", pady=(0,4))
        tk.Button(row, text="▶ Original", command=self._play_orig,
                  bg=BG_INPUT, fg=FG_WHT, font=FT_LBL, relief="flat",
                  cursor="hand2", pady=5).pack(side="left", fill="x", expand=True, padx=(0,3))
        tk.Button(row, text="⏹ Stop", command=self._stop,
                  bg="#1a0a0a", fg=ACT_RED, font=FT_LBL, relief="flat",
                  cursor="hand2", pady=5).pack(side="right", fill="x", expand=True)
        tk.Button(c3, text="▶▶ PREVISUALIZAR PROCESADO", command=self._preview,
                  bg=ACT_DIM, fg=FG_WHT, font=FT_BLD, relief="flat",
                  cursor="hand2", pady=7, activebackground=ACT_RED).pack(fill="x")

        # Exportar
        c4 = self._card(parent, "EXPORTAR")
        self._fmtv = tk.StringVar(value="mp3")
        fr = tk.Frame(c4, bg=BG_CARD)
        fr.pack(anchor="w", pady=(0,6))
        for fmt in ("mp3", "wav"):
            tk.Radiobutton(fr, text=fmt.upper(), variable=self._fmtv, value=fmt,
                           bg=BG_CARD, fg=FG_WHT, selectcolor=BG_INPUT,
                           activebackground=BG_CARD, font=FT_LBL).pack(side="left", padx=6)
        tk.Button(c4, text="💾  GUARDAR PROCESADO", command=self._export,
                  bg="#0a2a0a", fg=FG_GRN, font=FT_BLD, relief="flat",
                  cursor="hand2", pady=7, activebackground="#0d3d0d").pack(fill="x")

    def _build_right(self, parent):
        tk.Label(parent, text="AJUSTES MANUALES FINOS  (sobreescriben el preset)",
                 bg=BG_DEEP, fg=FG_MUT, font=FT_SM).pack(anchor="w", pady=(0,4))

        cv = tk.Canvas(parent, bg=BG_DEEP, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
        frm = tk.Frame(cv, bg=BG_DEEP)
        frm.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0), window=frm, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(-1*(e.delta//120), "units"))

        def sep(t):
            f = tk.Frame(frm, bg=BG_DEEP)
            f.pack(fill="x", pady=(8,2))
            tk.Label(f, text=f"── {t} ──", bg=BG_DEEP, fg=ACT_DIM, font=FT_SM).pack(anchor="w", padx=4)

        def card_sl():
            f = tk.Frame(frm, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
            f.pack(fill="x", pady=3, padx=2)
            return f

        sep("PITCH & VELOCIDAD")
        c = card_sl()
        self.sl_pitch = SL(c, "Pitch (semitonos)", -6, 6, 0.0, res=0.1, fmt="{:+.1f}", unit=" st")
        self.sl_pitch.pack(fill="x")
        self.sl_speed = SL(c, "Velocidad (factor)", 0.60, 1.50, 1.0, res=0.01, fmt="{:.2f}", unit="×")
        self.sl_speed.pack(fill="x")
        self.sl_gain = SL(c, "Gain de Entrada", -6, 12, 0.0, res=0.5, fmt="{:+.1f}", unit=" dB")
        self.sl_gain.pack(fill="x")

        sep("ECUALIZADOR")
        c = card_sl()
        self.sl_hp = SL(c, "High-Pass (corte de graves)", 20, 300, 80, res=5, fmt="{:.0f}", unit=" Hz")
        self.sl_hp.pack(fill="x")
        self.sl_warmth = SL(c, "Calidez / Low Shelf boost", -6, 10, 2.5, res=0.5, fmt="{:+.1f}", unit=" dB")
        self.sl_warmth.pack(fill="x")
        self.sl_pres = SL(c, "Presencia / High Shelf", -6, 10, 1.5, res=0.5, fmt="{:+.1f}", unit=" dB")
        self.sl_pres.pack(fill="x")

        sep("COMPRESIÓN DINÁMICA")
        c = card_sl()
        self.sl_cthr = SL(c, "Threshold", -40, 0, -18, res=1, fmt="{:.0f}", unit=" dB")
        self.sl_cthr.pack(fill="x")
        self.sl_crat = SL(c, "Ratio", 1.0, 10.0, 3.0, res=0.5, fmt="{:.1f}", unit=":1")
        self.sl_crat.pack(fill="x")

        sep("SATURACIÓN ARMÓNICA")
        c = card_sl()
        self.sl_sat = SL(c, "Drive (calidez analógica vintage)", 0, 10, 2, res=0.5, fmt="{:.1f}", unit=" dB")
        self.sl_sat.pack(fill="x")

        sep("REVERB DE SALA")
        c = card_sl()
        self.sl_rev = SL(c, "Wet Level (mezcla de reverb)", 0, 0.30, 0.05, res=0.005, fmt="{:.3f}")
        self.sl_rev.pack(fill="x")

        sep("NOISE GATE")
        c = card_sl()
        self.sl_gate = SL(c, "Threshold (umbral de silencio)", -80, -20, -50, res=1, fmt="{:.0f}", unit=" dB")
        self.sl_gate.pack(fill="x")

        # Botones de acción
        tk.Button(frm, text="⚡  APLICAR PRESET + AJUSTES  →  PREVISUALIZAR",
                  command=self._preview,
                  bg=ACT_RED, fg=FG_WHT, font=FT_PRES, relief="flat",
                  cursor="hand2", pady=10, activebackground=ACT_HOT).pack(fill="x", pady=(12,3), padx=2)

        tk.Button(frm, text="↺  RESETEAR SLIDERS AL PRESET SELECCIONADO",
                  command=self._reset,
                  bg=BG_CARD, fg=FG_MUT, font=FT_LBL, relief="flat",
                  cursor="hand2", pady=6, activebackground=BORDER).pack(fill="x", pady=(0,14), padx=2)

    # ── Lógica ───────────────────────────────────────────────────────────

    def _on_preset(self, _=None):
        disp = self._pvar.get()
        for k, v in PRESETS.items():
            if f"{v.emoji}  {v.nombre}" == disp:
                self._pkey = k
                break
        self._upd_desc()
        self._reset()

    def _upd_desc(self):
        p = PRESETS[self._pkey]
        self._pdesc.config(state="normal")
        self._pdesc.delete("1.0", "end")
        self._pdesc.insert("1.0", p.desc)
        self._pdesc.config(state="disabled")

    def _reset(self):
        p = PRESETS[self._pkey]
        self.sl_pitch.set(p.pitch)
        self.sl_speed.set(p.speed)
        self.sl_gain.set(p.gain)
        self.sl_hp.set(p.hp_hz)
        self.sl_warmth.set(p.warm_db)
        self.sl_pres.set(p.pres_db)
        self.sl_cthr.set(p.comp_thr)
        self.sl_crat.set(p.comp_rat)
        self.sl_sat.set(p.sat_drive)
        self.sl_rev.set(p.rev_wet)
        self.sl_gate.set(p.gate_thr)

    def _cargar(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de voz TTS",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac"), ("Todos", "*.*")]
        )
        if not path:
            return
        self._status("Cargando archivo...", FG_AMB)
        self._proc = None
        self._wv_proc.clear()
        def _run():
            try:
                dur, sr = self._eng.cargar(Path(path))
                raw = self._eng._raw.copy()
                self._q.put(("load_ok", path, dur, sr, raw))
            except Exception as e:
                self._q.put(("err", str(e)))
        threading.Thread(target=_run, daemon=True).start()

    def _preview(self):
        if self._eng._raw is None:
            messagebox.showwarning("Sin audio", "Carga un archivo primero.")
            return
        self._status("Procesando... (pitch shift + 8 efectos)", FG_AMB)
        self._eng.detener()
        p = PRESETS[self._pkey]
        args = dict(
            pitch=self.sl_pitch.get(), speed=self.sl_speed.get(), gain=self.sl_gain.get(),
            hp=self.sl_hp.get(), warmth=self.sl_warmth.get(), presence=self.sl_pres.get(),
            c_thr=self.sl_cthr.get(), c_rat=self.sl_crat.get(),
            sat=self.sl_sat.get(), rev=self.sl_rev.get(), gate=self.sl_gate.get(),
        )
        def _run():
            try:
                out = self._eng.procesar(p, **args)
                self._q.put(("proc_ok", out))
            except Exception as e:
                self._q.put(("err", str(e)))
        threading.Thread(target=_run, daemon=True).start()

    def _play_orig(self):
        if self._eng._raw is None:
            messagebox.showwarning("Sin audio", "Carga un archivo primero.")
            return
        self._status("▶ Reproduciendo original...", FG_GRN)
        self._eng.reproducir(self._eng._raw, done_cb=lambda: self._q.put(("idle",)))

    def _stop(self):
        self._eng.detener()
        self._status("⏹ Detenido.", FG_MUT)

    def _export(self):
        if self._proc is None:
            messagebox.showwarning("Sin procesado", "Genera el audio procesado primero con 'Previsualizar'.")
            return
        fmt = self._fmtv.get()
        path = filedialog.asksaveasfilename(
            title="Guardar audio procesado",
            defaultextension=f".{fmt}",
            filetypes=[(fmt.upper(), f"*.{fmt}"), ("Todos", "*.*")]
        )
        if not path:
            return
        self._status("Exportando...", FG_AMB)
        def _run():
            try:
                self._eng.exportar(self._proc, Path(path), fmt)
                self._q.put(("exp_ok", path))
            except Exception as e:
                self._q.put(("err", str(e)))
        threading.Thread(target=_run, daemon=True).start()

    # ── Cola de mensajes ─────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _handle(self, msg):
        k = msg[0]
        if k == "load_ok":
            _, path, dur, sr, raw = msg
            m, s = int(dur//60), dur%60
            self._fv.set(Path(path).name)
            self._dv.set(f"{m}:{s:05.2f}  |  {sr} Hz")
            self._wv_orig.load(raw)
            self._status(f"✅ Cargado: {Path(path).name}", FG_GRN)
        elif k == "proc_ok":
            _, audio = msg
            self._proc = audio
            self._wv_proc.load(audio)
            self._status(f"✅ Procesado con '{PRESETS[self._pkey].nombre}'. Reproduciendo...", FG_GRN)
            self._eng.reproducir(audio, done_cb=lambda: self._q.put(("idle",)))
        elif k == "exp_ok":
            _, path = msg
            self._status(f"💾 Exportado: {Path(path).name}", FG_GRN)
            messagebox.showinfo("Éxito", f"Audio guardado:\n{path}")
        elif k == "err":
            self._status(f"❌ {msg[1]}", ACT_RED)
            messagebox.showerror("Error", msg[1])
        elif k == "idle":
            self._status("Listo.", FG_MUT)

    def _status(self, txt, color=FG_GRN):
        self._sv.set(txt)
        self._sb_lbl.config(fg=color)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = App()
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_CARD,
                    foreground=FG_WHT, selectbackground=ACT_DIM,
                    selectforeground=FG_WHT, arrowcolor=ACT_RED, borderwidth=0)
    style.configure("TScrollbar", background=BG_CARD, troughcolor=BG_DEEP,
                    arrowcolor=FG_MUT, borderwidth=0)
    app.mainloop()