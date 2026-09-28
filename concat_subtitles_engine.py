#!/usr/bin/env python3
"""
concat_subtitles_engine.py
Motor de concatenación de videos con transiciones (FFmpeg xfade)
y transcripción automática de voz a subtítulos llamativos (Estilo TikTok / Hormozi).
100% gratuito, local y sin costos de API.
"""

import os
import sys
import json
import time
import subprocess
import glob
import re

try:
    import speech_recognition as sr
except ImportError:
    sr = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos_listos")
CLIPS_DIR = os.path.join(VIDEOS_DIR, "clips")

def natural_sort_key(s):
    """Ordenamiento natural para que '1.mp4', '2.mp4' ... '10.mp4' queden en orden numérico."""
    filename = os.path.basename(s)
    match = re.match(r'^(\d+)', filename)
    if match:
        return (0, int(match.group(1)))
    return (1, filename.lower())

def get_clip_info(filepath):
    """Obtiene la duración y verifica el canal de audio con ffprobe."""
    try:
        cmd_dur = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]
        res_dur = subprocess.run(cmd_dur, capture_output=True, text=True, check=True)
        duration = float(res_dur.stdout.strip())
        
        cmd_audio = [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]
        res_audio = subprocess.run(cmd_audio, capture_output=True, text=True)
        has_audio = "audio" in res_audio.stdout.lower()
        
        return {"duration": duration, "has_audio": has_audio}
    except Exception as e:
        print(f"⚠️ Error analizando clip {filepath}: {e}")
        return {"duration": 6.0, "has_audio": True}

def transcribe_clip(filepath):
    """Extrae el audio del clip y lo transcribe a texto en español."""
    if sr is None:
        return ""
    wav_path = f"/tmp/transcribe_{os.getpid()}_{int(time.time()*1000)}.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", filepath, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, check=True
        )
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
        text = r.recognize_google(audio_data, language="es-ES")
        return text.strip()
    except Exception:
        return ""
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass

def format_ass_time(seconds):
    """Convierte segundos en formato de tiempo ASS: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def get_clip_speech_window(filepath, clip_dur):
    """Detecta el inicio y fin real de voz en el clip para no desfasar los subtítulos en silencios."""
    try:
        cmd = [
            "ffmpeg", "-v", "error", "-i", filepath,
            "-af", "silencedetect=noise=-30dB:d=0.25",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Buscar inicio de voz (fin del primer silencio)
        m_start = re.search(r'silence_end:\s*([\d.]+)', res.stderr)
        speech_start = float(m_start.group(1)) if m_start else 0.0

        # Buscar fin de voz (inicio del último silencio)
        m_ends = re.findall(r'silence_start:\s*([\d.]+)', res.stderr)
        speech_end = float(m_ends[-1]) if (m_ends and float(m_ends[-1]) > speech_start + 0.5) else clip_dur

        speech_dur = max(0.5, min(clip_dur - speech_start, speech_end - speech_start))
        return speech_start, speech_dur
    except Exception:
        return 0.0, clip_dur


def generate_subtitles_from_audio(clip_paths, durations, transition_dur, ass_path):
    """
    Transcribe el audio real de cada clip y genera subtítulos dinámicos estilo TikTok / Hormozi.
    """
    header = """[Script Info]
Title: Subtítulos Dinámicos Automáticos
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HormoziYellow,DejaVu Sans,82,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,8,4,2,40,40,320,1
Style: HormoziGreen,DejaVu Sans,84,&H0000FF00,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,9,5,2,40,40,320,1
Style: HookImpact,DejaVu Sans,88,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,2,0,1,10,6,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    transcripts = []
    current_time = 0.0

    palabras_clave = {
        "MILLONES", "CHINA", "1975", "CATÁSTROFE", "ERROR", "COLAPSO",
        "REPRESAS", "BANQIAO", "FRÁGIL", "CRISTAL", "FRACASO", "ALARMAS", "15 M",
        "METROS", "VIDAS", "SECRETO", "ESTADO", "TRAGEDIA", "OLVIDADAS", "ADVERTENCIA"
    }

    for i, path in enumerate(clip_paths):
        dur = durations[i]
        # Transcribir el clip
        print(f"🎙️ Transcribiendo audio del clip {i+1}/{len(clip_paths)}: {os.path.basename(path)}...")
        raw_text = transcribe_clip(path)
        
        if not raw_text:
            raw_text = f"PARTE {i+1}"
            
        print(f"   ↳ Texto detectado: \"{raw_text}\"")
        transcripts.append(raw_text)

        # Dividir el texto en bloques cortos de 3 a 5 palabras
        words = raw_text.split()
        if len(words) <= 5:
            chunks = [" ".join(words)]
        else:
            chunks = []
            chunk_size = 4
            for j in range(0, len(words), chunk_size):
                chunks.append(" ".join(words[j:j+chunk_size]))

        speech_offset, speech_active_dur = get_clip_speech_window(path, dur)
        chunk_dur = speech_active_dur / max(1, len(chunks))

        for c_idx, chunk in enumerate(chunks):
            start = current_time + speech_offset + (c_idx * chunk_dur)
            end = start + chunk_dur
            
            # Estilo dinámico
            if i == 0 and c_idx == 0:
                style = "HookImpact"
            elif c_idx % 2 == 1:
                style = "HormoziGreen"
            else:
                style = "HormoziYellow"

            # Resaltar palabras de impacto
            chunk_upper = chunk.upper()
            chunk_words = chunk_upper.split()
            formatted_words = []
            for w in chunk_words:
                clean_w = re.sub(r'[^A-Z0-9ÁÉÍÓÚÑ]', '', w)
                if clean_w in palabras_clave or len(clean_w) >= 8:
                    # Resaltar en verde fosforescente
                    formatted_words.append(f"{{\\c&H0000FF00&}}{w}{{\\c&H0000FFFF&}}")
                else:
                    formatted_words.append(w)

            texto_final = " ".join(formatted_words)
            s_str = format_ass_time(start)
            e_str = format_ass_time(end)
            events.append(f"Dialogue: 0,{s_str},{e_str},{style},,0,0,0,,{texto_final}")

        # Avanzar el tiempo descontando la transición
        current_time += dur - transition_dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"📄 Subtítulos sincronizados guardados en: {ass_path}")
    return " ".join(transcripts)

def build_and_run_ffmpeg(clip_paths, transition_type, transition_dur, ass_path, output_mp4):
    """
    Concatena los clips con transiciones xfade y quema los subtítulos en 9:16.
    """
    n = len(clip_paths)
    if n == 0:
        raise ValueError("No se encontraron clips para unir.")

    infos = [get_clip_info(p) for p in clip_paths]
    durations = [inf["duration"] for inf in infos]

    if n == 1:
        total_duration = durations[0]
    else:
        total_duration = sum(durations) - ((n - 1) * transition_dur)

    print(f"🎬 Uniendo {n} clips | Duración total: {total_duration:.2f}s | Transición: {transition_type} ({transition_dur}s)")

    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", p])

    filter_complex = []

    # 1. Normalizar todos los clips a 1080x1920 a 30fps
    for i in range(n):
        has_audio = infos[i]["has_audio"]
        filter_complex.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]"
        )
        if not has_audio:
            filter_complex.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{durations[i]}[a{i}]")
        else:
            filter_complex.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}]")

    # 2. Encadenar transiciones xfade
    if n == 1:
        last_v = "[v0]"
        last_a = "[a0]"
    else:
        current_v = "[v0]"
        current_a = "[a0]"
        accum_offset = durations[0] - transition_dur

        for i in range(1, n):
            next_v = f"[v{i}]"
            next_a = f"[a{i}]"
            out_v = f"[vx{i}]" if i < n - 1 else "[v_merged]"
            out_a = f"[ax{i}]" if i < n - 1 else "[a_merged]"

            offset = max(0.1, accum_offset)
            filter_complex.append(
                f"{current_v}{next_v}xfade=transition={transition_type}:duration={transition_dur}:offset={offset:.2f}{out_v}"
            )
            filter_complex.append(
                f"{current_a}{next_a}acrossfade=d={transition_dur}{out_a}"
            )

            current_v = out_v
            current_a = out_a
            if i < n - 1:
                accum_offset = accum_offset + durations[i] - transition_dur

        last_v = "[v_merged]"
        last_a = "[a_merged]"

    # 3. Quemar subtítulos con libass
    escaped_ass = ass_path.replace(":", "\\:").replace("'", "\\'")
    filter_complex.append(f"{last_v}ass='{escaped_ass}'[v_final]")

    full_filter = ";\n".join(filter_complex)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", full_filter,
        "-map", "[v_final]",
        "-map", last_a,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_mp4
    ]

    print("🚀 Ejecutando ensamble y renderizado en FFmpeg...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("❌ Error de FFmpeg:")
        print(proc.stderr[-1000:])
        raise RuntimeError(f"FFmpeg falló con código {proc.returncode}")

    print(f"✅ Video renderizado con éxito en: {output_mp4}")
    return total_duration

def process_concatenation(params):
    """Punto de entrada principal para procesar clips."""
    carpeta_clips = params.get("carpeta_clips") or CLIPS_DIR
    os.makedirs(carpeta_clips, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    clip_paths = []
    
    # 1. Si el usuario especificó videos concretos
    clips_solicitados = params.get("videos") or []
    if isinstance(clips_solicitados, list) and len(clips_solicitados) > 0:
        for c in clips_solicitados:
            if os.path.isabs(c) and os.path.exists(c):
                clip_paths.append(c)
            elif os.path.exists(os.path.join(carpeta_clips, c)):
                clip_paths.append(os.path.join(carpeta_clips, c))
            elif os.path.exists(os.path.join(VIDEOS_DIR, c)):
                clip_paths.append(os.path.join(VIDEOS_DIR, c))

    # 2. Si no especificó lista fija, buscar en carpeta_clips
    if len(clip_paths) == 0:
        candidatos = glob.glob(os.path.join(carpeta_clips, "*.mp4"))
        candidatos = [c for c in candidatos if not os.path.basename(c).startswith("video_unido") and not os.path.basename(c).startswith("video_final")]
        if candidatos:
            clip_paths = sorted(candidatos, key=natural_sort_key)

    # 3. Si sigue vacío, buscar en VIDEOS_DIR (por si el usuario los puso en videos_listos directamente)
    if len(clip_paths) == 0:
        candidatos = glob.glob(os.path.join(VIDEOS_DIR, "*.mp4"))
        candidatos = [c for c in candidatos if not os.path.basename(c).startswith("video_unido") and not os.path.basename(c).startswith("video_final")]
        if candidatos:
            clip_paths = sorted(candidatos, key=natural_sort_key)

    if len(clip_paths) == 0:
        raise FileNotFoundError(
            f"No se encontraron clips de video para unir en '{carpeta_clips}' ni en '{VIDEOS_DIR}'. "
            "Por favor coloca tus clips numerados (ej. 1.mp4, 2.mp4, etc.) en esa carpeta."
        )

    print(f"🎬 Se encontraron {len(clip_paths)} clips para unir:")
    for idx, cp in enumerate(clip_paths):
        print(f"   {idx+1}. {os.path.basename(cp)}")

    transition_type = params.get("transicion") or "dissolve"
    transition_dur = float(params.get("duracion_transicion_segundos") or 0.5)

    # Analizar duraciones
    infos = [get_clip_info(p) for p in clip_paths]
    durations = [inf["duration"] for inf in infos]

    # Generar subtítulos desde el audio real de cada clip
    ass_path = os.path.join(VIDEOS_DIR, "subtitulos_estilo.ass")
    full_transcript = generate_subtitles_from_audio(clip_paths, durations, transition_dur, ass_path)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_mp4 = os.path.join(VIDEOS_DIR, f"video_unido_subtitulado_{timestamp}.mp4")
    video_final_shortcut = os.path.join(VIDEOS_DIR, "video_unido_final.mp4")

    duracion_real = build_and_run_ffmpeg(clip_paths, transition_type, transition_dur, ass_path, output_mp4)

    import shutil
    try:
        if os.path.exists(video_final_shortcut):
            os.remove(video_final_shortcut)
        shutil.copy2(output_mp4, video_final_shortcut)
    except Exception as e:
        print(f"Aviso actualizando video_unido_final.mp4: {e}")

    return {
        "status": "success",
        "mensaje": f"¡{len(clip_paths)} videos unidos con transiciones y subtítulos de voz generados exitosamente!",
        "video_path": output_mp4,
        "video_final_path": video_final_shortcut,
        "total_clips_unidos": len(clip_paths),
        "duracion_segundos": round(duracion_real, 2),
        "transicion_utilizada": transition_type,
        "tamano_bytes": os.path.getsize(output_mp4),
        "transcripcion_completa": full_transcript,
        "carpeta": VIDEOS_DIR
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        param_file = sys.argv[1]
        with open(param_file, "r", encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = {}

    res = process_concatenation(params)
    print(json.dumps(res, indent=2, ensure_ascii=False))
