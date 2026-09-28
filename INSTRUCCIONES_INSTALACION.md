# 🎬 Creador de Videos Automático con n8n, IA y FFmpeg

Este paquete contiene 3 flujos de automatización listos para usar en **n8n** junto a un motor de procesamiento de video en **Python + FFmpeg**:

1. 🧒 **Videos Infantiles y Cuentos:** Transforma ilustraciones en video vertical (9:16) con animación suave Ken Burns, voz latina femenina de Edge-TTS y subtítulos en morado y azul celeste.
2. 🎙️ **Videos Documentales / Misterio:** Transforma fotos en video vertical con voz latina masculina profunda, transiciones y subtítulos de alto impacto en rojo y negro.
3. ✂️ **Concatenador de Clips con Subtítulos Dinámicos:** Une múltiples videos cortos con transiciones fluidas y subtítulos estilo TikTok / Reels.

---

## 💻 Requisitos Previos

En la computadora donde se vaya a usar (Linux, macOS o Windows con WSL2):
1. **Docker y Docker Compose** instalados (para levantar n8n).
2. **Python 3.9+** instalado.
3. **FFmpeg** instalado en el sistema operativo:
   - Ubuntu / Debian: `sudo apt install -y ffmpeg`
   - MacOS: `brew install ffmpeg`
   - Windows (WSL2): `sudo apt install -y ffmpeg`

---

## 🚀 Instalación en 3 Pasos

### Paso 1: Instalar dependencias de Python
Abre una terminal en esta carpeta y ejecuta:
```bash
pip install -r requirements.txt
```
*(Instala `edge-tts` para las voces gratuitas y `Pillow` para procesar imágenes).*

### Paso 2: Iniciar n8n y el motor de video
Ejecuta el script de inicio:
```bash
./iniciar.sh
```
Esto arrancará:
- El microservicio de video en segundo plano (`http://localhost:5679`).
- El contenedor de Docker con n8n (`http://localhost:5678`).

*(Para apagar todo cuando termines tu jornada, solo ejecuta `./detener.sh`).*

### Paso 3: Importar los flujos en n8n
1. Abre tu navegador en **`http://localhost:5678`**.
2. Crea una cuenta local de n8n si es tu primera vez.
3. Crea un flujo nuevo y presiona `Ctrl + V` copiando el contenido de cualquiera de los archivos en la carpeta **`database/`**:
   - `modelo_videos_infantiles.json`
   - `modelo_imagenes_narracion.json`
   - `modelo_concatenar_subtitulos.json`
4. En el primer nodo ("Configuración..."), actualiza la ruta de tu PC donde tienes esta carpeta (por ejemplo: `/home/usuario/creador_videos/imagenes_infantiles`).
5. Agrega tu API Key gratuita de Google Gemini en el nodo de Gemini (puedes obtener una gratis en [Google AI Studio](https://aistudio.google.com/)).

¡Y listo! Ya puedes generar videos ilimitados de forma 100% gratuita.
