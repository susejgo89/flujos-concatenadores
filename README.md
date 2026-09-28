# 🎬 Creador y Concatenador de Videos Automático (n8n + FFmpeg + IA)

Sistema completo de automatización para generar videos verticales de alta retención (9:16) para **TikTok, YouTube Shorts, Reels y YouTube Kids** utilizando **n8n**, **Edge-TTS** (locución neural gratuita en español latino) y **FFmpeg**.

---

## 🌟 Características y Flujos Incluidos

1. 🧒 **Cuentos y Videos Infantiles (`modelo_videos_infantiles`):**
   - Transforma ilustraciones en historias animadas con efecto Ken Burns suave.
   - Locución femenina en español latino (Dalia / Salomé - 100% gratuita).
   - Subtítulos dinámicos en **Azul Celeste** y **Morado Mágico** con sincronización palabra por palabra (WordBoundary).
   - Generación de copy y ganchos con emojis amigables mediante Google Gemini.

2. 🎙️ **Videos Documentales / Misterio (`modelo_imagenes_narracion`):**
   - Transforma fotos en documentales verticales de alto impacto.
   - Locución masculina profunda (Jorge - México / Gonzalo - Colombia).
   - Subtítulos cinematográficos de alto contraste en **Blanco** y **Rojo Intenso** sobre borde negro grueso.

3. ✂️ **Concatenador de Clips con Subtítulos Dinámicos (`modelo_concatenar_subtitulos`):**
   - Une clips de video cortos con transiciones fluidas de disolución cruzada (`dissolve`).
   - Transcripción y subtitulado dinámico centrado en las zonas de voz activa.

---

## 📋 Requisitos Previos

- **Docker y Docker Compose** (para ejecutar n8n).
- **Python 3.9+**
- **FFmpeg** instalado en el sistema operativo:
  ```bash
  # Ubuntu / Debian
  sudo apt update && sudo apt install -y ffmpeg

  # macOS
  brew install ffmpeg
  ```

---

## 🚀 Inicio Rápido

### 1. Instalar dependencias de Python
```bash
pip install -r requirements.txt
```

### 2. Iniciar el servicio y n8n
```bash
./iniciar.sh
```
*Esto iniciará el microservicio de renderizado en `http://localhost:5679` y la interfaz de n8n en `http://localhost:5678`.*

### 3. Importar los flujos en n8n
1. Abre tu navegador en **`http://localhost:5678`**.
2. Crea un nuevo flujo en blanco y presiona `Ctrl + V` copiando el contenido de cualquiera de los archivos dentro de la carpeta **`database/`**:
   - `modelo_videos_infantiles.json`
   - `modelo_imagenes_narracion.json`
   - `modelo_concatenar_subtitulos.json`
3. Ajusta la ruta de la carpeta de imágenes o clips a la ruta de tu máquina.
4. Conecta tu API Key gratuita de Google Gemini en el nodo correspondiente.
5. ¡Haz clic en **"Probar ahora"** o **"Test workflow"**!

### 4. Detener los servicios
Cuando termines de trabajar:
```bash
./detener.sh
```

---

## 📁 Estructura del Proyecto

```text
├── database/                    # Flujos listos para importar en n8n (.json y .md)
├── imagenes_infantiles/         # Carpeta de entrada para ilustraciones de cuentos
├── imagenes_para_video/         # Carpeta de entrada para imágenes de documentales
├── videos_listos/               # Carpeta donde se guardan los videos MP4 generados
│   └── clips/                   # Carpeta de entrada para clips a unir
├── render_service.py            # Servidor HTTP local (puerto 5679) que orquesta los renders
├── image_narration_engine.py    # Motor de animación Ken Burns, locución Edge-TTS y subtítulos
├── concat_subtitles_engine.py   # Motor de unión xfade y subtitulado
├── docker-compose.yml           # Configuración de contenedor para n8n
├── iniciar.sh                   # Script de encendido en 1 clic
├── detener.sh                   # Script de apagado en 1 clic
└── requirements.txt             # Dependencias de Python (edge-tts, Pillow)
```
