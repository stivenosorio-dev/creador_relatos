# 🎬 Creador de Relatos Paranormales V1

El **Creador de Relatos Paranormales** es un software de automatización y dirección IA que actúa como el cerebro creativo detrás de canales inmersivos de terror. 

A partir de un relato en texto, el software produce tres entregables de calidad premium: un audio narrativo inmersivo sin rastros de voz sintética, subtítulos sincronizados listos para redes sociales, y un guion de dirección cinematográfica detallando cada imagen, pista de fondo y efecto de sonido.

## 📦 Entregables V1

1. **`audio_narrativo.mp3`**: Voz generada por `edge-tts` (Microsoft Neural Voices) procesada con una cadena de 8 efectos profesionales (EQ, compresión, saturación armónica, reverb, de-esser) usando la tecnología de Spotify (`pedalboard`) para producir una voz de narrador de hoguera profunda y natural.
2. **`subtitulos.srt` y `subtitulos.ass`**: Subtítulos transcritos a nivel de palabra usando `faster-whisper` (optimizados para bajo consumo de RAM). El formato `.ass` incluye un estilo animado progresivo de color rojo, ideal para impacto visual en videos verticales.
3. **`guion.json`**: Un script de estructuración JSON validado estrictamente mediante Pydantic y generado con inteligencia artificial local (Ollama). Incluye prompts súper detallados en inglés para IAs visuales, transiciones, recomendaciones de música real sin copyright, efectos de sonido y reglas de ritmo emocional.

## 🚀 Instalación y Prerrequisitos

El software está optimizado para funcionar en entornos de **8GB de RAM**. No requiere GPUs de gama alta para la V1.

1. Instalar dependencias puras de Python:
```bash
pip install -r requirements.txt
pip install audioop-lts  # Necesario para pydub en Python 3.13+
```

2. Prerrequisitos externos:
- **FFmpeg**: Debes tener FFmpeg instalado y agregado al PATH de tu sistema operativo (requerido por `pydub`).
- **Ollama**: Debes tener instalado y corriendo [Ollama](https://ollama.com/) en tu máquina local.
- **Model Ollama**: Baja el modelo necesario (por defecto `llama3.2`):
  ```bash
  ollama pull llama3.2:3b
  ```

## 🎮 Comandos (CLI)

Todo el flujo se controla mediante una interfaz CLI amigable (usando `click` y `rich`):

### Ver voces y plataformas recomendadas
- `python main.py voces`
  Verás las opciones de narración (recomendamos Jorge para relatos de terror).
- `python main.py plataformas --duracion 450`
  El sistema te recomendará en qué red social subir tu historia dependiendo de su tiempo (TikTok, YT Shorts, FB, YT Largo, etc.)

### Ejecutar Pipeline Completo
Recibe un relato `.txt` y produce todo en la carpeta `output/`:
```bash
python main.py crear --relato historias/casa_abandonada.txt --plataforma youtube_largo
```

### Comandos Modulares
Si ya tienes una parte y solo quieres generar la otra:
- Generar solo Audio: `python main.py audio -r relato.txt --voz jorge`
- Generar solo Subtítulos a partir del audio final: `python main.py subtitulos --audio output/relato/audio_narrativo.mp3`
- Generar solo el Guion de dirección: `python main.py guion -r relato.txt --duracion "10:30"`

## 🧠 Arquitectura Cognitiva y Memoria

Para garantizar su funcionamiento en **8GB RAM**, se emplea un procesador secuencial asíncrono supervisado por el `memory_manager.py`. Cada nodo "pesado" (como *Whisper* o el *LLM* en *Ollama*) se libera de la memoria forzando una recolección de basura una vez finaliza, blindando al sistema de desbordamientos y caídas. 

## 📂 Directorios de Salida
Todos los recursos y resultados se alojarán limpios y listos para edición en la carpeta contenedora con el nombre de tu proyecto: `output/{nombre_del_relato}/`.
