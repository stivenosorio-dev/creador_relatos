import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import sys
import queue
from pathlib import Path
from datetime import datetime

# Importar lógica del proyecto
from config import (
    PLATAFORMAS,
    VOCES_DISPONIBLES,
    VOZ_DEFAULT,
    OUTPUT_DIR,
    MOTORES_TTS,
    narrador_tts_kwargs_para_voz,
)
from core.narrador_tts import NarradorTTS
from core.transcriptor import Transcriptor
from core.script_director import ScriptDirector
from utils.memory_manager import memory_manager
from utils.logger import get_logger

logger = get_logger("gui")

class AppParanormal(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🎬 Creador de Relatos Paranormales V1")
        self.geometry("900x750")
        self.configure(bg="#0f0f0f")  # Fondo oscuro profundo

        # Estilo de la aplicación
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#0f0f0f", foreground="#e0e0e0", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#0f0f0f")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#ff3333")

        self._build_ui()
        self._on_motor_changed()
        self.queue = queue.Queue()
        self.after(100, self._process_queue)

    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self, bg="#1a1a1a", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = tk.Label(header_frame, text="CREADOR DE RELATOS PARANORMALES", 
                              bg="#1a1a1a", foreground="#ff3b3b", font=("Impact", 24))
        title_label.pack(pady=10)
        subtitle_label = tk.Label(header_frame, text="V1.0 - Director IA & Narración Premium", 
                                 bg="#1a1a1a", foreground="#ffffff", font=("Segoe UI", 9, "italic"))
        subtitle_label.pack()

        main_container = tk.Frame(self, bg="#0f0f0f")
        main_container.pack(fill="both", expand=True, padx=30)

        # Izquierda: Configuración
        config_frame = tk.LabelFrame(main_container, text=" Configuración ", bg="#0f0f0f", fg="#ff3b3b", font=("Segoe UI", 10, "bold"), padx=15, pady=15)
        config_frame.pack(side="left", fill="y", padx=(0, 20))

        tk.Label(config_frame, text="Motor TTS:", bg="#0f0f0f", fg="#e0e0e0").pack(anchor="w")
        self.motor_var = tk.StringVar(value="edge-tts")
        self.motor_menu = ttk.Combobox(config_frame, textvariable=self.motor_var, values=MOTORES_TTS, state="readonly", width=25)
        self.motor_menu.pack(pady=(0, 5))
        self.motor_menu.bind("<<ComboboxSelected>>", self._on_motor_changed)

        tk.Label(config_frame, text="Voz del Narrador:", bg="#0f0f0f", fg="#e0e0e0").pack(anchor="w")
        self.voz_var = tk.StringVar(value=VOZ_DEFAULT)
        self.voz_values = list(VOCES_DISPONIBLES.keys())
        self.voz_menu = ttk.Combobox(config_frame, textvariable=self.voz_var, values=self.voz_values, state="readonly", width=25)
        self.voz_menu.pack(pady=(0, 15))

        tk.Label(config_frame, text="Plataforma Destino:", bg="#0f0f0f", fg="#e0e0e0").pack(anchor="w")
        self.plat_var = tk.StringVar()
        plat_values = ["Auto-recomendar"] + list(PLATAFORMAS.keys())
        self.plat_menu = ttk.Combobox(config_frame, textvariable=self.plat_var, values=plat_values, state="readonly", width=25)
        self.plat_menu.current(0)
        self.plat_menu.pack(pady=(0, 15))

        tk.Label(config_frame, text="Modelo Ollama:", bg="#0f0f0f", fg="#e0e0e0").pack(anchor="w")
        self.modelo_var = tk.StringVar(value="llama3.2")
        self.modelo_entry = tk.Entry(config_frame, textvariable=self.modelo_var, bg="#1e1e1e", fg="#ffffff", insertbackground="white", borderwidth=0, highlightthickness=1)
        self.modelo_entry.pack(pady=(0, 15), fill="x")

        # Botón Directorio
        self.output_dir_var = tk.StringVar(value=str(OUTPUT_DIR))
        tk.Label(config_frame, text="Carpeta de Salida:", bg="#0f0f0f", fg="#e0e0e0").pack(anchor="w")
        tk.Entry(config_frame, textvariable=self.output_dir_var, state="readonly", bg="#1e1e1e", fg="#888").pack(fill="x")
        self.btn_dir = tk.Button(config_frame, text="Cambiar Carpeta", command=self._select_dir, bg="#333", fg="white", activebackground="#444", cursor="hand2")
        self.btn_dir.pack(pady=(5, 20))

        self.btn_generar = tk.Button(config_frame, text="EJECUTAR DIRECTOR", command=self._start_generation, 
                                    bg="#ff3b3b", fg="white", font=("Segoe UI", 12, "bold"), 
                                    padx=20, pady=10, relief="flat", activebackground="#ff5555", cursor="hand2")
        self.btn_generar.pack(fill="x")

        # Derecha: Texto y Logs
        right_frame = tk.Frame(main_container, bg="#0f0f0f")
        right_frame.pack(side="right", fill="both", expand=True)

        tk.Label(right_frame, text="Relato / Historia Paranormal:", bg="#0f0f0f", fg="#ff3b3b", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.relato_text = tk.Text(right_frame, height=12, bg="#121212", fg="#e0e0e0", 
                                   insertbackground="white", font=("Consolas", 11), 
                                   padx=10, pady=10, borderwidth=0, highlightbackground="#333", highlightthickness=1)
        self.relato_text.pack(fill="x", pady=(0, 20))
        self.relato_text.insert("1.0", "Escribe o pega aquí tu relato de terror...")

        tk.Label(right_frame, text="Estado del Pipeline:", bg="#0f0f0f", fg="#ff3b3b", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.status_text = tk.Text(right_frame, height=15, bg="#050505", fg="#00ff00", 
                                   font=("Consolas", 10), state="disabled", 
                                   padx=10, pady=10, borderwidth=0)
        self.status_text.pack(fill="both", expand=True)

    def _log(self, message):
        self.queue.put(lambda: self._ui_log(message))

    def _ui_log(self, message):
        self.status_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert("end", f"[{timestamp}] {message}\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")

    def _select_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir_var.set(dir_path)

    def _on_motor_changed(self, event=None):
        motor = self.motor_var.get()
        voces_filtradas = [k for k, v in VOCES_DISPONIBLES.items() if v.motor == motor]
        self.voz_menu.config(values=voces_filtradas)
        if self.voz_var.get() not in voces_filtradas:
            self.voz_var.set(voces_filtradas[0] if voces_filtradas else "")

    def _process_queue(self):
        try:
            while True:
                callback = self.queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    def _start_generation(self):
        texto = self.relato_text.get("1.0", "end-1c").strip()
        if not texto or len(texto) < 10:
            messagebox.showwarning("Relato insuficiente", "Por favor ingresa un relato válido.")
            return

        self.btn_generar.config(state="disabled", text="PROCESANDO...", bg="#888")
        threading.Thread(target=self._generation_thread, args=(texto,), daemon=True).start()

    def _generation_thread(self, texto):
        try:
            self._log("🚀 Iniciando pipeline paranormal...")
            
            # Preparar entorno
            titulo_relato = texto[:20].strip().replace(" ", "_")
            out_root = Path(self.output_dir_var.get())
            out_dir = out_root / f"gui_{datetime.now().strftime('%m%d_%H%M')}"
            out_dir.mkdir(parents=True, exist_ok=True)

            voz_config = VOCES_DISPONIBLES[self.voz_var.get()]
            plataforma = self.plat_var.get()
            modelo = self.modelo_var.get()

            # --- AUDIO ---
            self._log(f"🎙️ Paso 1: Generando narración premium ({voz_config.nombre} / {voz_config.motor})...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            narrador = NarradorTTS(voz_config, **narrador_tts_kwargs_para_voz(voz_config))
            audio_path = loop.run_until_complete(narrador.generar(texto, out_dir))
            duracion_seg = narrador.obtener_duracion(audio_path)
            duracion_str = f"{int(duracion_seg // 60):02d}:{int(duracion_seg % 60):02d}"
            self._log(f"✅ Audio generado: {duracion_str}")
            memory_manager.post_module_cleanup("NarradorTTS")

            # --- SUBTÍTULOS ---
            self._log("📝 Paso 2: Transcribiendo subtítulos (faster-whisper)...")
            transcriptor = Transcriptor()
            srt_path, ass_path = transcriptor.generar(audio_path, out_dir, plataforma=plataforma)
            self._log("✅ Subtítulos sincronizados (.srt y .ass)")
            memory_manager.post_module_cleanup("Transcriptor")

            # --- GUION ---
            if plataforma == "Auto-recomendar":
                from config import recomendar_plataforma
                recs = recomendar_plataforma(duracion_seg)
                plataforma = recs[0]["plataforma"] if recs else "youtube_largo"
                self._log(f"💡 Sugerencia: Plataforma {plataforma} seleccionada.")

            self._log(f"🧠 Paso 3: Director IA ({modelo}) orquestando guion...")
            director = ScriptDirector(modelo=modelo)
            guion_path = director.generar(texto, duracion_str, plataforma, out_dir)
            self._log("✅ Guion JSON completo.")
            memory_manager.post_module_cleanup("ScriptDirector")

            self._log(f"✨ PROCESO COMPLETADO EXITOSAMENTE.")
            self._log(f"📁 Ubicación: {out_dir}")
            
            self.queue.put(lambda: messagebox.showinfo("Éxito", f"Todos los activos han sido generados en:\n{out_dir}"))

        except Exception as e:
            err_msg = str(e)
            self._log(f"❌ ERROR: {err_msg}")
            self.queue.put(lambda msg=err_msg: messagebox.showerror("Error en el Pipeline", msg))
        finally:
            self.queue.put(lambda: self.btn_generar.config(state="normal", text="EJECUTAR DIRECTOR", bg="#ff3b3b"))

if __name__ == "__main__":
    app = AppParanormal()
    app.mainloop()
