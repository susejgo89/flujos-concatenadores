#!/usr/bin/env python3
"""
image_narration_engine.py
Motor de generación de video a partir de imágenes fijas y texto de narración en off.
- 100% gratuito y local, sin costos de API.
- Voz masculina en español latinoamericano (Edge-TTS es-MX-JorgeNeural).
- Efecto Ken Burns suave (Zoom In, Zoom Out, Paneo horizontal y vertical alternados).
- Transiciones fluidas entre imágenes (dissolve, fade, wipe, slide).
- Subtítulos dinámicos llamativos estilo TikTok / Alex Hormozi (opcional).
- Formato vertical 9:16 (1080x1920) optimizado para TikTok, Shorts y Reels.
"""

import os
import sys
import json
import time
import subprocess
import glob
import re
import math
import shutil
import asyncio
import concurrent.futures
import edge_tts

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos_listos")
DEFAULT_IMAGES_DIR = os.path.join(BASE_DIR, "imagenes_para_video")
TEMP_DIR = os.path.join(VIDEOS_DIR, "temp_render")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(DEFAULT_IMAGES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def natural_sort_key(s):
    """Ordenamiento natural para que '1.jpg', '2.jpg' ... '10.jpg' queden en orden numérico."""
    filename = os.path.basename(s)
    match = re.match(r'^(\d+)', filename)
    if match:
        return (0, int(match.group(1)))
    return (1, filename.lower())


def get_audio_duration(filepath):
    """Obtiene la duración exacta de un archivo de audio con ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as e:
        print(f"⚠️ Error leyendo duración de audio {filepath}: {e}")
        return 10.0


async def _async_generate_tts_with_word_timings(text, output_mp3, voice, pitch="+0Hz", rate="+0%"):
    """Genera audio MP3 y captura marcas de tiempo exactas palabra por palabra con Edge-TTS."""
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary", pitch=pitch, rate=rate)
    words_timing = []
    with open(output_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                offset_sec = chunk["offset"] / 10_000_000
                dur_sec = chunk["duration"] / 10_000_000
                words_timing.append({
                    "word": chunk["text"],
                    "start": offset_sec,
                    "end": offset_sec + dur_sec
                })
    return words_timing


def generate_tts_voice(text, output_mp3, voice="es-EC-LuisNeural", pitch="-6Hz", rate="-10%"):
    """
    Genera la locución de voz con Edge-TTS y captura marcas de tiempo palabra por palabra
    (WordBoundary) para lograr sincronización milimétrica de subtítulos (Opción 1).
    """
    print(f"🎙️ Generando narración en off con voz ({voice}, pitch: {pitch}, rate: {rate}) y marcas de tiempo exactas...")
    words_timing = []
    try:
        words_timing = asyncio.run(_async_generate_tts_with_word_timings(text, output_mp3, voice, pitch, rate))
    except Exception as e:
        print(f"⚠️ Aviso en generación asíncrona: {e}. Usando fallback CLI...")
        cmd = [
            "edge-tts",
            "--voice", voice,
            "--text", text,
            "--pitch", pitch,
            "--rate", rate,
            "--write-media", output_mp3
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(output_mp3) or os.path.getsize(output_mp3) == 0:
            raise RuntimeError(f"Fallo al generar audio con Edge-TTS: {res.stderr}")

    if not os.path.exists(output_mp3) or os.path.getsize(output_mp3) == 0:
        raise RuntimeError(f"El archivo de audio generado {output_mp3} está vacío o no existe.")

    print(f"✅ Locución generada con éxito ({os.path.getsize(output_mp3)} bytes, {len(words_timing)} palabras sincronizadas).")
    return words_timing


def format_ass_time(seconds):
    """Formatea segundos en formato ASS: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_synced_chunks(words_timing, max_words=4):
    """
    Agrupa palabras con tiempos reales en frases cortas y naturales (Opción 1),
    respetando pausas de respiración y signos de puntuación.
    """
    if not words_timing:
        return []

    chunks = []
    current_chunk = []

    for i, item in enumerate(words_timing):
        current_chunk.append(item)
        word_text = item["word"].strip()

        # Comprobar si termina en signo de puntuación (pausa natural)
        has_punct = bool(re.search(r'[.,!?;:]$', word_text))

        # Comprobar si hay una pausa de silencio antes de la siguiente palabra
        has_pause = False
        if i + 1 < len(words_timing):
            pause = words_timing[i + 1]["start"] - item["end"]
            if pause >= 0.30:
                has_pause = True

        if len(current_chunk) >= max_words or has_punct or has_pause or i == len(words_timing) - 1:
            chunks.append(current_chunk)
            current_chunk = []

    # Asignar tiempos de inicio y fin exactos a cada bloque
    synced_events = []
    for idx, c in enumerate(chunks):
        start = c[0]["start"]
        end = c[-1]["end"]

        # Suavizado de bordes para evitar parpadeos si la siguiente palabra empieza de inmediato
        if idx + 1 < len(chunks):
            next_start = chunks[idx + 1][0]["start"]
            if next_start - end < 0.25:
                end = next_start
            else:
                end = end + 0.10
        else:
            end = end + 0.20

        text = " ".join(w["word"] for w in c)
        synced_events.append({"start": start, "end": end, "text": text})

    return synced_events


def generate_subtitles_file(text, total_duration, ass_path, estilo="documental", words_timing=None):
    """
    Genera archivo de subtítulos ASS dinámicos sincronizados con la narración.
    - estilo 'documental': Blanco y Rojo Intenso con borde negro grueso (estilo Misterio/Crimen/Impacto).
    - estilo 'infantil': Azul Celeste y Morado Mágico con borde oscuro (alegre, divertido y acogedor).
    - Utiliza 'words_timing' exactos si están disponibles (Opción 1: Frases con sincronización real).
    """
    if estilo == "infantil":
        header = """[Script Info]
Title: Subtítulos Infantiles Divertidos
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KidsBlue,DejaVu Sans,84,&H00FFD54F&,&H000000FF,&H00351025&,&HA0000000,-1,0,0,0,100,100,1,0,1,8,4,2,40,40,320,1
Style: KidsPurple,DejaVu Sans,86,&H00F040B0&,&H000000FF,&H00251035&,&HA0000000,-1,0,0,0,100,100,1,0,1,8,4,2,40,40,320,1
Style: KidsImpact,DejaVu Sans,88,&H00FFFFFF&,&H000000FF,&H00451035&,&HA0000000,-1,0,0,0,100,100,2,0,1,9,5,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        color_base = "\\c&H00FFD54F&"
        color_highlight = "\\c&H00F040B0&"
        style_alt1 = "KidsBlue"
        style_alt2 = "KidsPurple"
        style_hook = "KidsImpact"
    else:
        # Estilo Documental / Misterio (Rojo y Negro)
        # Base blanca con resaltado en Rojo Intenso (&H001414FF&) y borde negro grueso (&H00000000&)
        header = """[Script Info]
Title: Subtítulos Documental Misterio
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocWhite,DejaVu Sans,84,&H00FFFFFF&,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,8,4,2,40,40,320,1
Style: DocRed,DejaVu Sans,86,&H001414FF&,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,8,4,2,40,40,320,1
Style: DocImpact,DejaVu Sans,88,&H00FFFFFF&,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,2,0,1,9,5,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        color_base = "\\c&H00FFFFFF&"
        color_highlight = "\\c&H001414FF&"
        style_alt1 = "DocWhite"
        style_alt2 = "DocRed"
        style_hook = "DocImpact"

    events = []

    if words_timing and len(words_timing) > 0:
        synced_chunks = build_synced_chunks(words_timing, max_words=4)
        for idx, sc in enumerate(synced_chunks):
            start = sc["start"]
            end = min(total_duration, sc["end"])

            # Estilo dinámico
            if idx == 0:
                style = style_hook
            elif idx % 2 == 1:
                style = style_alt2
            else:
                style = style_alt1

            chunk_upper = sc["text"].upper()
            chunk_words = chunk_upper.split()
            formatted_words = []
            for w in chunk_words:
                clean_w = re.sub(r'[^A-Z0-9ÁÉÍÓÚÑ]', '', w)
                if len(clean_w) >= 6:
                    # Resaltar palabra clave con el color secundario
                    formatted_words.append(f"{{{color_highlight}}}{w}{{{color_base}}}")
                else:
                    formatted_words.append(w)

            texto_final = " ".join(formatted_words)
            s_str = format_ass_time(start)
            e_str = format_ass_time(end)
            events.append(f"Dialogue: 0,{s_str},{e_str},{style},,0,0,0,,{texto_final}")
    else:
        # Fallback de división lineal si no hay marcas de tiempo por palabra
        words = text.split()
        if not words:
            return

        chunks = []
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            chunks.append(" ".join(words[i:i + chunk_size]))

        chunk_dur = total_duration / max(1, len(chunks))

        for idx, chunk in enumerate(chunks):
            start = idx * chunk_dur
            end = min(total_duration, start + chunk_dur)

            # Estilo dinámico
            if idx == 0:
                style = style_hook
            elif idx % 2 == 1:
                style = style_alt2
            else:
                style = style_alt1

            chunk_upper = chunk.upper()
            chunk_words = chunk_upper.split()
            formatted_words = []
            for w in chunk_words:
                clean_w = re.sub(r'[^A-Z0-9ÁÉÍÓÚÑ]', '', w)
                if len(clean_w) >= 6:
                    formatted_words.append(f"{{{color_highlight}}}{w}{{{color_base}}}")
                else:
                    formatted_words.append(w)

            texto_final = " ".join(formatted_words)
            s_str = format_ass_time(start)
            e_str = format_ass_time(end)
            events.append(f"Dialogue: 0,{s_str},{e_str},{style},,0,0,0,,{texto_final}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"📄 Subtítulos sincronizados guardados en: {ass_path} (Estilo: {estilo}, Eventos: {len(events)})")


def create_animated_clip(image_path, duration, effect_index, output_clip, fps=30, width=1080, height=1920):
    """
    Convierte una imagen estática en un clip animado de video con efecto Ken Burns suave.
    Efectos según effect_index % 5:
    - 0: Zoom In suave (1.0 -> 1.25)
    - 1: Zoom Out suave (1.25 -> 1.0)
    - 2: Paneo horizontal suave Izquierda a Derecha (1.20)
    - 3: Paneo horizontal suave Derecha a Izquierda (1.20)
    - 4: Paneo vertical ascendente Abajo a Arriba (1.20)
    """
    total_frames = int(round(duration * fps))
    if total_frames < 10:
        total_frames = 10

    # Resolución previa ligeramente mayor para mantener nitidez durante el zoom
    pre_w = int(width * 1.33)
    pre_h = int(height * 1.33)

    effect_type = effect_index % 5
    
    if effect_type == 0:
        # Zoom In suave hacia el centro
        step = 0.22 / total_frames
        zoom_expr = f"min(zoom+{step:.6f},1.25)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect_type == 1:
        # Zoom Out suave alejándose del centro
        step = 0.22 / total_frames
        zoom_expr = f"max(1.25-{step:.6f}*on,1.0)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect_type == 2:
        # Paneo horizontal de Izquierda a Derecha
        zoom_expr = "1.20"
        x_expr = f"(on/{total_frames})*(iw-iw/zoom)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif effect_type == 3:
        # Paneo horizontal de Derecha a Izquierda
        zoom_expr = "1.20"
        x_expr = f"(1-(on/{total_frames}))*(iw-iw/zoom)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        # Paneo vertical ascendente (Abajo hacia Arriba)
        zoom_expr = "1.20"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(1-(on/{total_frames}))*(ih-ih/zoom)"

    vf = (
        f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase,"
        f"crop={pre_w}:{pre_h},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={width}x{height}:fps={fps},"
        f"setsar=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", image_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        output_clip
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error animando imagen {image_path}: {res.stderr[-500:]}")


def process_image_narration(params):
    """
    Flujo principal:
    1. Lee las imágenes de la carpeta o lista.
    2. Genera la locución de voz con Edge-TTS (es-MX-JorgeNeural).
    3. Anima cada imagen con zoom in/out/paneo suave.
    4. Concatena los clips con transiciones xfade (dissolve).
    5. Quema subtítulos dinámicos de voz y acopla el audio.
    """
    # 1. Configuración de entrada
    carpeta_imagenes = params.get("carpeta_imagenes") or DEFAULT_IMAGES_DIR
    texto_narracion = params.get("texto_narracion") or params.get("narracion") or params.get("guion") or ""
    voz = params.get("voz")
    if not voz:
        if params.get("accion") == "video_infantil" or "infantil" in str(carpeta_imagenes).lower():
            voz = "es-VE-PaolaNeural"
        else:
            voz = "es-EC-LuisNeural"
    transicion = params.get("transicion") or "dissolve"
    transicion_dur = float(params.get("duracion_transicion_segundos") or 0.6)
    activar_subtitulos = params.get("subtitulos", True)

    # Detectar estilo de subtítulos ('documental' para rojo/negro o 'infantil' para azul/morado)
    estilo_subtitulos = params.get("estilo_subtitulos")
    if not estilo_subtitulos:
        if "infantil" in voz.lower() or "infantil" in str(carpeta_imagenes).lower() or params.get("tipo") == "infantil" or params.get("accion") == "video_infantil":
            estilo_subtitulos = "infantil"
        else:
            estilo_subtitulos = "documental"

    if not texto_narracion.strip():
        # Buscar si el usuario guardó un archivo de texto en la carpeta (ej. narracion.txt, guion.txt, texto.txt)
        txt_candidates = [
            os.path.join(carpeta_imagenes, "narracion.txt"),
            os.path.join(carpeta_imagenes, "guion.txt"),
            os.path.join(carpeta_imagenes, "texto.txt"),
            os.path.join(DEFAULT_IMAGES_DIR, "narracion.txt"),
            os.path.join(DEFAULT_IMAGES_DIR, "guion.txt")
        ]
        for tc in txt_candidates:
            if os.path.exists(tc):
                try:
                    with open(tc, "r", encoding="utf-8") as f:
                        contenido = f.read().strip()
                    if contenido:
                        texto_narracion = contenido
                        print(f"📄 Narración cargada automáticamente desde archivo: {tc}")
                        break
                except Exception as e:
                    print(f"Aviso leyendo {tc}: {e}")

    if not texto_narracion.strip():
        texto_narracion = (
            "En un mundo lleno de misterios y maravillas, cada imagen guarda una historia "
            "esperando ser contada. Observa con atención los detalles que casi nadie nota."
        )

    # 2. Localizar imágenes
    image_paths = []
    imagenes_solicitadas = params.get("imagenes") or []

    if isinstance(imagenes_solicitadas, list) and len(imagenes_solicitadas) > 0:
        for img in imagenes_solicitadas:
            if os.path.isabs(img) and os.path.exists(img):
                image_paths.append(img)
            elif os.path.exists(os.path.join(carpeta_imagenes, img)):
                image_paths.append(os.path.join(carpeta_imagenes, img))
            elif os.path.exists(os.path.join(DEFAULT_IMAGES_DIR, img)):
                image_paths.append(os.path.join(DEFAULT_IMAGES_DIR, img))

    if not image_paths:
        exts = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"]
        encontradas = []
        for ext in exts:
            encontradas.extend(glob.glob(os.path.join(carpeta_imagenes, ext)))
        if not encontradas and carpeta_imagenes != DEFAULT_IMAGES_DIR:
            for ext in exts:
                encontradas.extend(glob.glob(os.path.join(DEFAULT_IMAGES_DIR, ext)))
        if encontradas:
            image_paths = sorted(encontradas, key=natural_sort_key)

    if not image_paths:
        raise FileNotFoundError(
            f"No se encontraron imágenes en '{carpeta_imagenes}'. "
            f"Por favor coloca tus imágenes (.jpg, .png, etc.) en esa carpeta o indica sus nombres."
        )

    n_images = len(image_paths)
    print(f"🖼️ Se encontraron {n_images} imágenes para crear el video:")
    for idx, imp in enumerate(image_paths):
        print(f"   {idx + 1}. {os.path.basename(imp)}")

    # 3. Generar la narración en off con Edge-TTS
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(VIDEOS_DIR, f"audio_narracion_{timestamp}.mp3")
    pitch = params.get("pitch") or ("-6Hz" if "luis" in voz.lower() else "+0Hz")
    rate = params.get("rate") or ("-10%" if "luis" in voz.lower() else "+0%")
    words_timing = generate_tts_voice(texto_narracion, audio_path, voice=voz, pitch=pitch, rate=rate)
    audio_duration = get_audio_duration(audio_path)
    print(f"⏱️ Duración exacta de la narración de audio: {audio_duration:.2f} segundos.")

    # 4. Calcular duración de cada clip animado
    # Formula con transiciones xfade: Total = N * D - (N - 1) * T  =>  D = (Total + (N - 1) * T) / N
    if n_images == 1:
        clip_dur = audio_duration
    else:
        clip_dur = (audio_duration + (n_images - 1) * transicion_dur) / n_images
        # Asegurar un mínimo de 1.5s por imagen
        clip_dur = max(clip_dur, transicion_dur + 0.5)

    print(f"🎬 Duración por imagen animada: {clip_dur:.2f}s (Transición: {transicion} {transicion_dur}s)")

    # 5. Generar los clips animados individuales (Ken Burns en paralelo)
    temp_clips = [None] * n_images
    print("🎨 Creando efectos suaves de Zoom y Paneo para cada imagen (procesamiento en paralelo)...")

    def _render_single_clip(item):
        i, imp = item
        clip_file = os.path.join(TEMP_DIR, f"clip_anim_{timestamp}_{i:03d}.mp4")
        print(f"   ↳ Procesando imagen {i + 1}/{n_images}: {os.path.basename(imp)}...")
        create_animated_clip(imp, clip_dur, i, clip_file, fps=30, width=1080, height=1920)
        return i, clip_file

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for idx, cfile in executor.map(_render_single_clip, enumerate(image_paths)):
            temp_clips[idx] = cfile

    tipo_video = "infantil" if estilo_subtitulos == "infantil" else "narrado"

    # 6. Generar subtítulos sincronizados si está habilitado
    ass_path = os.path.join(VIDEOS_DIR, f"subtitulos_{tipo_video}_{timestamp}.ass")
    if activar_subtitulos:
        generate_subtitles_file(texto_narracion, audio_duration, ass_path, estilo=estilo_subtitulos, words_timing=words_timing)

    # 7. Unir los clips con FFmpeg xfade + Audio + Subtítulos
    output_mp4 = os.path.join(VIDEOS_DIR, f"video_{tipo_video}_{timestamp}.mp4")
    video_final_shortcut = os.path.join(VIDEOS_DIR, f"video_{tipo_video}_final.mp4")

    inputs = []
    for c in temp_clips:
        inputs.extend(["-i", c])
    # Agregar el audio
    inputs.extend(["-i", audio_path])
    audio_idx = len(temp_clips)

    filter_complex = []
    if n_images == 1:
        last_v = "[0:v]"
    else:
        current_v = "[0:v]"
        accum_offset = clip_dur - transicion_dur
        for i in range(1, n_images):
            next_v = f"[{i}:v]"
            out_v = f"[vx{i}]" if i < n_images - 1 else "[v_merged]"
            offset = max(0.1, accum_offset)
            filter_complex.append(
                f"{current_v}{next_v}xfade=transition={transicion}:duration={transicion_dur}:offset={offset:.2f}{out_v}"
            )
            current_v = out_v
            if i < n_images - 1:
                accum_offset = accum_offset + clip_dur - transicion_dur
        last_v = "[v_merged]"

    # Subtítulos opcionales
    if activar_subtitulos and os.path.exists(ass_path):
        escaped_ass = ass_path.replace(":", "\\:").replace("'", "\\'")
        filter_complex.append(f"{last_v}ass='{escaped_ass}'[v_final]")
        final_video_label = "[v_final]"
    else:
        final_video_label = last_v

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";\n".join(filter_complex),
        "-map", final_video_label,
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "24",
        "-maxrate", "3500k",
        "-bufsize", "7000k",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_mp4
    ]

    print("🚀 Ensamblando video completo con locución y transiciones en FFmpeg...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"❌ Error de FFmpeg: {proc.stderr[-1000:]}")
        raise RuntimeError(f"FFmpeg falló al ensamblar el video: código {proc.returncode}")

    # Copiar a acceso directo permanente
    try:
        if os.path.exists(video_final_shortcut):
            os.remove(video_final_shortcut)
        shutil.copy2(output_mp4, video_final_shortcut)
    except Exception as e:
        print(f"Aviso actualizando {video_final_shortcut}: {e}")

    # Limpiar temporales
    for tc in temp_clips:
        try:
            if os.path.exists(tc):
                os.remove(tc)
        except Exception:
            pass

    final_duration = get_audio_duration(output_mp4)
    file_size = os.path.getsize(output_mp4)
    print(f"✅ ¡Video ({tipo_video}) generado con éxito! ({file_size} bytes, {final_duration:.2f}s): {output_mp4}")

    return {
        "status": "success",
        "mensaje": f"¡Video ({tipo_video}) de {n_images} imágenes con animaciones, transiciones y narración generado exitosamente!",
        "video_path": output_mp4,
        "video_final_path": video_final_shortcut,
        "tipo_video": tipo_video,
        "total_imagenes": n_images,
        "duracion_segundos": round(final_duration, 2),
        "voz_utilizada": voz,
        "estilo_subtitulos": estilo_subtitulos,
        "transicion_utilizada": transicion,
        "tamano_bytes": file_size,
        "subtitulos_incluidos": activar_subtitulos,
        "carpeta": VIDEOS_DIR
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        with open(param_file, "r", encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = {}

    res = process_image_narration(params)
    print(json.dumps(res, indent=2, ensure_ascii=False))
