import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
from pedalboard import Pedalboard, PitchShift, Reverb, HighShelfFilter, LowShelfFilter, Compressor

class EditorVozPremium:
    def __init__(self, root):
        self.root = root
        self.root.title("Afinador y Editor de Voz TTS Premium v2.0")
        self.root.geometry("550x750")
        self.root.configure(padx=20, pady=20)

        # Variables de Audio
        self.audio_original = None
        self.sr = 44100
        self.audio_procesado = None
        self.is_playing = False
        
        # Diccionario de controles
        self.controles = {}
        self.vars = {}

        # Definición de Presets Profesionales
        self.presets = {
            "Manual (Personalizado)": {"velocidad": 1.0, "pitch": 0.0, "calidez": 2.0, "brillo": -1.0, "espacio": 0.05},
            "Humanizar Voz Virtual": {"velocidad": 1.0, "pitch": 0.0, "calidez": 3.0, "brillo": -2.0, "espacio": 0.03},
            "Voz Profunda (Pecho)": {"velocidad": 0.95, "pitch": -2.0, "calidez": 6.0, "brillo": -1.0, "espacio": 0.05},
            "Relatos de Hoguera": {"velocidad": 0.90, "pitch": -1.0, "calidez": 5.0, "brillo": -4.0, "espacio": 0.15},
            "Voz Celestial": {"velocidad": 0.95, "pitch": 2.0, "calidez": -2.0, "brillo": 4.0, "espacio": 0.40},
            "Evasor de Copyright": {"velocidad": 1.12, "pitch": 1.0, "calidez": 1.0, "brillo": 2.0, "espacio": 0.08}
        }

        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#007BFF", foreground="white", font=('Helvetica', 10, 'bold'))
        style.configure("Header.TLabel", font=('Helvetica', 14, 'bold'))

        ttk.Label(self.root, text="Procesador de Voz Narradora Studio", style="Header.TLabel").pack(pady=(0, 15))

        # Controles de Archivo
        frame_archivos = ttk.Frame(self.root)
        frame_archivos.pack(fill="x", pady=5)
        ttk.Button(frame_archivos, text="📂 Cargar Audio", command=self.cargar_audio).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(frame_archivos, text="💾 Exportar", command=self.exportar_audio).pack(side="left", padx=5, expand=True, fill="x")

        self.lbl_estado = ttk.Label(self.root, text="Estado: Esperando archivo...", foreground="gray")
        self.lbl_estado.pack(pady=5)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=10)

        # Menú de Presets
        frame_presets = ttk.Frame(self.root)
        frame_presets.pack(fill="x", pady=5)
        ttk.Label(frame_presets, text="🌟 Ediciones Profesionales:", font=('Helvetica', 10, 'bold')).pack(side="left", padx=5)
        
        self.cmb_presets = ttk.Combobox(frame_presets, values=list(self.presets.keys()), state="readonly", width=25)
        self.cmb_presets.set("Manual (Personalizado)")
        self.cmb_presets.pack(side="left", padx=10, fill="x", expand=True)
        self.cmb_presets.bind("<<ComboboxSelected>>", self.aplicar_preset)

        # Función helper para sliders
        def crear_slider(parent, label_key, label_text, from_, to, default, resolution):
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=8)
            ttk.Label(frame, text=label_text, width=20).pack(side="left")
            
            var = tk.DoubleVar(value=default)
            self.vars[label_key] = var
            
            slider = ttk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal")
            slider.pack(side="left", fill="x", expand=True, padx=10)
            
            val_lbl = ttk.Label(frame, text=str(default), width=5)
            val_lbl.pack(side="left")
            
            def update_lbl(event, v=var, l=val_lbl, res=resolution):
                l.config(text=f"{v.get():.{res}f}")
                
            def on_release(event):
                self.cmb_presets.set("Manual (Personalizado)")
                self.aplicar_efectos_en_hilo(None)
                
            slider.bind("<ButtonRelease-1>", on_release)
            slider.bind("<Motion>", update_lbl)
            
            self.controles[label_key] = {"slider": slider, "lbl": val_lbl, "res": resolution}

        # Frame de Ajustes
        frame_controles = ttk.LabelFrame(self.root, text="Ajustes de Motor de Audio", padding=15)
        frame_controles.pack(fill="both", expand=True, pady=10)

        crear_slider(frame_controles, 'velocidad', "Velocidad (x)", 0.5, 2.0, 1.0, 2)
        crear_slider(frame_controles, 'pitch', "Pitch (Semitonos)", -12.0, 12.0, 0.0, 1)
        crear_slider(frame_controles, 'calidez', "Calidez (Graves dB)", -15.0, 15.0, 2.0, 1)
        crear_slider(frame_controles, 'brillo', "Presencia (Agudos dB)", -15.0, 15.0, -1.0, 1)
        crear_slider(frame_controles, 'espacio', "Espacio (Reverb %)", 0.0, 0.6, 0.05, 2)

        # Controles de Reproducción
        frame_play = ttk.Frame(self.root)
        frame_play.pack(fill="x", pady=10)
        self.btn_play = ttk.Button(frame_play, text="▶ Escuchar Previa", command=self.toggle_play)
        self.btn_play.pack(side="left", expand=True, fill="x", padx=5)

    def aplicar_preset(self, event=None):
        seleccion = self.cmb_presets.get()
        valores = self.presets[seleccion]
        
        # Actualizar sliders en la UI
        for key, val in valores.items():
            self.vars[key].set(val)
            res = self.controles[key]['res']
            self.controles[key]['lbl'].config(text=f"{val:.{res}f}")
            
        # Disparar renderizado
        self.aplicar_efectos_en_hilo(None)

    def cargar_audio(self):
        ruta_archivo = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac")])
        if ruta_archivo:
            self.lbl_estado.config(text="Analizando motor de audio...", foreground="blue")
            self.root.update()
            try:
                self.audio_original, self.sr = librosa.load(ruta_archivo, sr=None)
                self.audio_procesado = self.audio_original.copy()
                self.lbl_estado.config(text=f"Cargado: {ruta_archivo.split('/')[-1]}", foreground="green")
                self.aplicar_efectos_en_hilo(None)
            except Exception as e:
                messagebox.showerror("Error", f"Error de decodificación: {e}")
                self.lbl_estado.config(text="Error al cargar.", foreground="red")

    def aplicar_efectos_en_hilo(self, event):
        if self.audio_original is None:
            return
        threading.Thread(target=self._procesar_audio).start()

    def _procesar_audio(self):
        # Actualización de UI segura desde hilo secundario
        self.root.after(0, lambda: self.lbl_estado.config(text="Renderizando calidad de estudio...", foreground="orange"))
        
        audio_temp = self.audio_original.copy()
        
        velocidad = self.vars['velocidad'].get()
        if velocidad != 1.0:
            audio_temp = librosa.effects.time_stretch(audio_temp, rate=velocidad)

        pitch = self.vars['pitch'].get()
        calidez = self.vars['calidez'].get()
        brillo = self.vars['brillo'].get()
        reverb_mix = self.vars['espacio'].get()

        board = Pedalboard([
            Compressor(threshold_db=-15, ratio=3.0),
            LowShelfFilter(cutoff_frequency_hz=250, gain_db=calidez),
            HighShelfFilter(cutoff_frequency_hz=4500, gain_db=brillo),
            PitchShift(semitones=pitch),
            Reverb(room_size=0.4, damping=0.6, wet_level=reverb_mix, dry_level=1.0)
        ])

        self.audio_procesado = board(audio_temp, self.sr)
        self.root.after(0, lambda: self.lbl_estado.config(text="Renderizado completado. Listo para escuchar.", foreground="green"))

    def toggle_play(self):
        if self.audio_procesado is None:
            messagebox.showwarning("Atención", "Carga un audio primero.")
            return

        if self.is_playing:
            sd.stop()
            self.is_playing = False
            self.btn_play.config(text="▶ Escuchar Previa")
        else:
            sd.play(self.audio_procesado, self.sr)
            self.is_playing = True
            self.btn_play.config(text="⏹ Detener")
            
            # Hilo de monitoreo corregido para evitar colisión con Tkinter
            def check_play():
                sd.wait()
                if self.is_playing: # Solo actualiza si no fue detenido manualmente
                    self.is_playing = False
                    self.root.after(0, lambda: self.btn_play.config(text="▶ Escuchar Previa"))
            
            threading.Thread(target=check_play, daemon=True).start()

    def exportar_audio(self):
        if self.audio_procesado is None:
            return
            
        ruta_guardado = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Studio", "*.wav")])
        if ruta_guardado:
            try:
                sf.write(ruta_guardado, self.audio_procesado, self.sr, subtype='PCM_24')
                messagebox.showinfo("Éxito", "Exportación de Alta Fidelidad completada.")
            except Exception as e:
                messagebox.showerror("Error de E/S", f"No se pudo guardar: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EditorVozPremium(root)
    root.mainloop()