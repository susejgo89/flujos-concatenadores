#!/usr/bin/env python3
"""
telegram_bot.py
Bot privado de Telegram para generación automática de videos de Misterio y Curiosidades.
- 100% Gratuito y Local (Edge-TTS + Ken Burns + FFmpeg).
- Sin dependencias de Gemini ni APIs de pago.
- Descarga paralela ultra-rápida (ThreadPoolExecutor con 8 hilos).
- Renderizado de clips en paralelo (3 núcleos simultáneos).
- Actualizaciones de estado en tiempo real en Telegram (editMessageText).
- Acumula y agrupa correctamente lotes grandes de fotos (+10, 16, 20 fotos) sin dividirlas.
- Acepta fotos normales y fotos enviadas como archivos/carpetas sin compresión.
- Soporta textos y guiones largos (sin el límite de 1024 caracteres de Telegram).
- Cancelación real inmediata con /cancelar.
- Auto-limpieza tras finalizar cada video.
- Filtro de privacidad por Whitelist.
"""

import os
import sys
import time
import json
import shutil
import threading
import concurrent.futures
import requests
import image_narration_engine

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos_listos")
TELEGRAM_DIR = os.path.join(BASE_DIR, "imagenes_telegram")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(TELEGRAM_DIR, exist_ok=True)

def load_bot_token():
    """Carga el token desde variables de entorno o archivo .env local de forma segura."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        return token.strip()
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception as e:
            print(f"Aviso leyendo .env: {e}", flush=True)
    return None

# Token del bot (Cargado de forma segura desde .env)
BOT_TOKEN = load_bot_token()
if not BOT_TOKEN:
    print("❌ ERROR: No se encontró TELEGRAM_BOT_TOKEN.", flush=True)
    print("👉 Por favor asegúrate de tener el archivo .env con: TELEGRAM_BOT_TOKEN=tu_token", flush=True)
    sys.exit(1)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_API_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

# ==============================================================================
# LISTA BLANCA DE SEGURIDAD (SOLO USUARIOS AUTORIZADOS)
# ==============================================================================
ALLOWED_USERNAMES = {
    "aleleovazquez",
    "susejgo89",
    "susejgonza89",
    "susej",
    "rebecavictoria22"
}
ALLOWED_IDS = set()


def is_user_authorized(from_user):
    """Verifica si el usuario de Telegram está en la lista blanca."""
    if not from_user:
        return False
    user_id = from_user.get("id")
    username = (from_user.get("username") or "").lower().strip()

    if user_id in ALLOWED_IDS:
        return True
    if username in ALLOWED_USERNAMES:
        if user_id:
            ALLOWED_IDS.add(user_id)
        return True
    return False


def send_message(chat_id, text, parse_mode="HTML"):
    """Envía un mensaje de texto por Telegram."""
    try:
        url = f"{API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        res = requests.post(url, json=payload, timeout=15)
        return res.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"⚠️ Error enviando mensaje a chat {chat_id}: {e}", flush=True)
        return None


def edit_message(chat_id, message_id, text, parse_mode="HTML"):
    """Edita un mensaje existente para mostrar progreso en vivo."""
    if not message_id:
        return
    try:
        url = f"{API_URL}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


def delete_message(chat_id, message_id):
    """Elimina un mensaje de estado cuando ya se entregó el video final."""
    if not message_id:
        return
    try:
        url = f"{API_URL}/deleteMessage"
        requests.post(url, json={"chat_id": chat_id, "message_id": message_id}, timeout=10)
    except Exception:
        pass


def send_chat_action(chat_id, action="record_video"):
    """Envía acción de estado (ej: 'record_video', 'upload_video', 'typing')."""
    try:
        url = f"{API_URL}/sendChatAction"
        requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=10)
    except Exception:
        pass


def download_file(file_id, dest_path):
    """Descarga un archivo desde los servidores de Telegram con buffer optimizado de 64KB."""
    try:
        get_file_url = f"{API_URL}/getFile"
        r = requests.post(get_file_url, json={"file_id": file_id}, timeout=20)
        file_path = r.json().get("result", {}).get("file_path")
        if not file_path:
            return False

        download_url = f"{FILE_API_URL}/{file_path}"
        with requests.get(download_url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"⚠️ Error descargando archivo {file_id}: {e}", flush=True)
        return False


def send_video(chat_id, video_path, caption):
    """Sube y envía el video MP4 terminado al chat con soporte para reintentos."""
    try:
        url = f"{API_URL}/sendVideo"
        file_size = os.path.getsize(video_path)
        print(f"📤 Subiendo video a Telegram ({file_size / (1024*1024):.2f} MB)...", flush=True)

        with open(video_path, "rb") as vf:
            files = {"video": (os.path.basename(video_path), vf, "video/mp4")}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "supports_streaming": True,
                "parse_mode": "HTML"
            }
            res = requests.post(url, data=data, files=files, timeout=360)
            result_json = res.json()
            if result_json.get("ok"):
                return True
            print(f"⚠️ Telegram rechazó sendVideo: {result_json}", flush=True)

    except Exception as e:
        print(f"⚠️ Error en sendVideo {video_path}: {e}", flush=True)

    # Fallback como documento si sendVideo falló
    try:
        print("🔄 Intentando enviar como Documento...", flush=True)
        with open(video_path, "rb") as vf:
            res = requests.post(
                f"{API_URL}/sendDocument",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"document": (os.path.basename(video_path), vf)},
                timeout=360
            )
            return res.json().get("ok", False)
    except Exception as ex:
        print(f"❌ Fallback sendDocument falló: {ex}", flush=True)
        return False


def send_audio(chat_id, audio_path, caption="", title="Muestra de Voz", performer="Locutor"):
    """Envía un archivo de audio como mensaje interactivo en Telegram."""
    try:
        url = f"{API_URL}/sendAudio"
        with open(audio_path, "rb") as f:
            files = {"audio": (os.path.basename(audio_path), f, "audio/mpeg")}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
                "title": title,
                "performer": performer
            }
            res = requests.post(url, data=data, files=files, timeout=60)
            res_json = res.json()
            if not res_json.get("ok"):
                print(f"⚠️ Telegram rechazó sendAudio ({audio_path}): {res_json}", flush=True)
            return res_json.get("ok", False)
    except Exception as e:
        print(f"⚠️ Error enviando audio a chat {chat_id}: {e}", flush=True)
        return False


# ==============================================================================
# PERFILES DE VOZ Y PERSONALIZACIÓN DE NARRADOR
# ==============================================================================
VOICE_PROFILES = {
    "luis": {
        "voz": "es-EC-LuisNeural",
        "pitch": "-4Hz",
        "rate": "+0%",
        "nombre": "Luis (Hombre Maduro / Cálido)",
        "desc": "Tono profundo y cálido de hombre maduro."
    },
    "luis_abuelo": {
        "voz": "es-EC-LuisNeural",
        "pitch": "-6Hz",
        "rate": "-10%",
        "nombre": "Luis (Abuelo Sabio / Paternal)",
        "desc": "Calibrado más grave y pausado, como un patriarca sabio."
    },
    "gonzalo": {
        "voz": "es-CO-GonzaloNeural",
        "pitch": "-5Hz",
        "rate": "-10%",
        "nombre": "Gonzalo (Abuelo Dulce / Cariñoso)",
        "desc": "Voz muy tierna, serena y afectuosa de abuelito entrañable."
    },
    "manuel": {
        "voz": "es-CU-ManuelNeural",
        "pitch": "-5Hz",
        "rate": "-8%",
        "nombre": "Manuel (Abuelo de Fogata / Pueblo)",
        "desc": "Tono campechano, cercano y narrador de pueblo."
    },
    "alonso": {
        "voz": "es-US-AlonsoNeural",
        "pitch": "-5Hz",
        "rate": "-10%",
        "nombre": "Alonso (Abuelo Historiador)",
        "desc": "Voz clásica, pausada y respetable de cronista o documental."
    }
}
user_voice_selection = {}


# ==============================================================================
# GESTOR DE MEDIOS Y SESIONES POR USUARIO (CENTRALIZADO)
# ==============================================================================
incoming_media = {}
media_lock = threading.Lock()

user_sessions = {}
sessions_lock = threading.Lock()

active_jobs = {}
jobs_lock = threading.Lock()


def is_job_cancelled(chat_id):
    """Comprueba si el usuario solicitó cancelar el trabajo actual."""
    with jobs_lock:
        return active_jobs.get(chat_id, {}).get("cancel", False)


def process_video_task(chat_id, user_info, photo_file_ids, caption):
    """Procesa la creación del video con progreso en vivo, descarga paralela y auto-limpieza."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    session_id = f"sesion_{chat_id}_{timestamp}"
    session_dir = os.path.join(TELEGRAM_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    with jobs_lock:
        active_jobs[chat_id] = {"cancel": False, "session_dir": session_dir}

    status_msg_id = None
    try:
        palabras = len(caption.split())
        status_msg_id = send_message(
            chat_id,
            f"📥 <b>¡Todo recibido!</b> Descargando <b>{len(photo_file_ids)} fotos</b> en paralelo...\n"
            f"⏱️ <i>Iniciando en tu servidor local...</i>"
        )
        send_chat_action(chat_id, "upload_video")

        if is_job_cancelled(chat_id):
            print(f"🛑 Trabajo cancelado por {user_info}", flush=True)
            return

        # 1. Descarga paralela de fotos (8 conexiones concurrentes)
        print(f"📥 Descargando {len(photo_file_ids)} fotos en paralelo para {user_info}...", flush=True)
        def _download_task(item):
            if is_job_cancelled(chat_id):
                return None
            idx, fid = item
            dest = os.path.join(session_dir, f"{idx+1:02d}.jpg")
            ok = download_file(fid, dest)
            return dest if ok else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            download_results = list(executor.map(_download_task, enumerate(photo_file_ids)))

        downloaded_paths = [p for p in download_results if p is not None]
        downloaded_count = len(downloaded_paths)

        if is_job_cancelled(chat_id):
            print(f"🛑 Cancelado tras descarga para {user_info}", flush=True)
            return

        if downloaded_count == 0:
            send_message(chat_id, "❌ No se pudieron descargar las imágenes. Por favor intenta de nuevo.")
            return

        # Obtener voz seleccionada por este usuario (o default Luis)
        user_voice = user_voice_selection.get(chat_id, VOICE_PROFILES["luis"])

        # Actualizar progreso a Fase 1: Locución
        edit_message(
            chat_id, status_msg_id,
            f"🎙️ <b>[Paso 1/3]</b> Fotos listas ({downloaded_count}). Generando locución de <b>{user_voice['nombre']}</b> ({palabras} palabras)...\n"
            f"⚡ <i>Sincronizando tiempos de audio...</i>"
        )
        send_chat_action(chat_id, "record_video")

        # 2. Configuración predeterminada: Documental / Misterio / Curiosidades (Solo imágenes + narración)
        params = {
            "carpeta_imagenes": session_dir,
            "texto_narracion": caption,
            "voz": user_voice["voz"],
            "pitch": user_voice.get("pitch", "-4Hz"),
            "rate": user_voice.get("rate", "+0%"),
            "estilo_subtitulos": "documental",
            "transicion": "dissolve",
            "duracion_transicion_segundos": 0.6,
            "subtitulos": False
        }

        # Actualizar progreso a Fase 2: Animación Ken Burns
        edit_message(
            chat_id, status_msg_id,
            f"🎨 <b>[Paso 2/3]</b> Creando efectos Ken Burns (Zoom y Paneo) para las <b>{downloaded_count} imágenes</b>...\n"
            f"⚡ <i>Procesando en 3 núcleos simultáneos...</i>"
        )

        if is_job_cancelled(chat_id):
            return

        # 3. Llamar al motor de procesamiento local
        result = image_narration_engine.process_image_narration(params)

        if is_job_cancelled(chat_id):
            print(f"🛑 Cancelado tras ensamble para {user_info}", flush=True)
            return

        video_path = result.get("video_path")
        duracion = result.get("duracion_segundos", 0)

        if not video_path or not os.path.exists(video_path):
            if not is_job_cancelled(chat_id):
                send_message(chat_id, "❌ Ocurrió un error inesperado ensamblando el video.")
            return

        # Actualizar progreso a Fase 3: Subida a Telegram
        edit_message(
            chat_id, status_msg_id,
            f"🚀 <b>[Paso 3/3]</b> ¡Video ensamblado ({duracion:.1f}s)! Subiendo a Telegram...\n"
            f"📤 <i>Casi listo...</i>"
        )
        send_chat_action(chat_id, "upload_video")

        # 4. Enviar el video terminado de vuelta por Telegram
        video_caption = (
            f"🎬 <b>¡Tu video está listo!</b>\n"
            f"⏱️ Duración: <b>{duracion:.1f}s</b>\n"
            f"🖼️ Fotos usadas: <b>{downloaded_count}</b>\n"
            f"🗣️ Voz: <code>{user_voice['nombre']}</code>\n\n"
            f"✨ <i>Para hacer otro video, envía fotos o un nuevo guion cuando quieras.</i>"
        )

        sent = send_video(chat_id, video_path, video_caption)
        if sent:
            # Borrar el mensaje de progreso para dejar el chat limpio
            delete_message(chat_id, status_msg_id)
        elif not is_job_cancelled(chat_id):
            send_message(chat_id, "❌ Hubo un inconveniente en la conexión al transferir el archivo a Telegram.")

    except Exception as ex:
        if not is_job_cancelled(chat_id):
            print(f"❌ Error en process_video_task para {user_info}: {ex}", flush=True)
            send_message(chat_id, f"❌ Error creando el video: {ex}")
    finally:
        with jobs_lock:
            active_jobs.pop(chat_id, None)
        # 5. AUTO-LIMPIEZA: Eliminar la carpeta temporal de fotos
        try:
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir, ignore_errors=True)
                print(f"🧹 Carpeta temporal eliminada: {session_dir}", flush=True)
        except Exception as e:
            print(f"Aviso limpiando {session_dir}: {e}", flush=True)


def media_monitor_worker():
    """
    Monitorea las fotos entrantes por chat_id.
    Espera 3.5 segundos de silencio para asegurar que llegaron TODAS las fotos
    (incluso si Telegram dividió el álbum en 10 + 6, o si se enviaron como archivos).
    """
    while True:
        time.sleep(0.5)
        ready_batches = []
        now = time.time()

        with media_lock:
            for chat_id, data in list(incoming_media.items()):
                if now - data["last_received"] >= 3.5:
                    ready_batches.append((chat_id, data))
                    del incoming_media[chat_id]

        for chat_id, data in ready_batches:
            user_info = data["user_info"]
            incoming_photos = data["photos"]
            incoming_caption = data.get("caption", "").strip()

            with sessions_lock:
                sess = user_sessions.setdefault(chat_id, {"photos": [], "user_info": user_info, "text": ""})
                sess["user_info"] = user_info

                sess["photos"].extend(incoming_photos)
                total_photos = len(sess["photos"])

                script_text = incoming_caption or sess.get("text", "").strip()

                if script_text:
                    photos_to_render = list(sess["photos"])
                    sess["photos"] = []
                    sess["text"] = ""

                    t = threading.Thread(
                        target=process_video_task,
                        args=(chat_id, user_info, photos_to_render, script_text),
                        daemon=True
                    )
                    t.start()
                else:
                    send_message(
                        chat_id,
                        f"📸 ¡Recibí tus <b>{total_photos} fotos</b> con éxito!\n\n"
                        f"✍️ Ahora por favor envíame el <b>texto de la narración</b> como un <b>mensaje normal de chat</b> (o un archivo .txt).\n\n"
                        f"💡 <i>Aquí no hay límite de caracteres. (O puedes enviar más fotos si te faltó alguna, o escribir /cancelar).</i>"
                    )


# Iniciar monitor de fotos
threading.Thread(target=media_monitor_worker, daemon=True).start()


# ==============================================================================
# BUCLE PRINCIPAL DE TELEGRAM (LONG POLLING)
# ==============================================================================
def run_telegram_bot():
    print("=" * 60, flush=True)
    print("🤖 BOT DE TELEGRAM PARA VIDEOS DE MISTERIO Y CURIOSIDADES", flush=True)
    print("=" * 60, flush=True)
    print("✅ Conectado a Telegram con el token oficial.", flush=True)
    print(f"🔒 Usuarios autorizados: {', '.join(sorted(ALLOWED_USERNAMES))}", flush=True)
    print("🚀 Esperando mensajes de usuarios autorizados...", flush=True)

    offset = 0
    while True:
        try:
            url = f"{API_URL}/getUpdates?offset={offset}&timeout=25"
            resp = requests.get(url, timeout=35)
            if resp.status_code != 200:
                time.sleep(3)
                continue

            updates = resp.json().get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1

                msg = upd.get("message")
                if not msg:
                    continue

                from_user = msg.get("from", {})
                chat_id = msg.get("chat", {}).get("id")
                user_id = from_user.get("id")
                username = from_user.get("username", "") or from_user.get("first_name", "Desconocido")
                user_label = f"@{username}" if from_user.get("username") else f"{username} (ID: {user_id})"

                # 1. Comprobación de seguridad (Whitelist)
                if not is_user_authorized(from_user):
                    print(f"⛔ Intento de acceso bloqueado: {user_label} (ID: {user_id})", flush=True)
                    send_message(
                        chat_id,
                        f"⛔ <b>Acceso denegado</b>\n\n"
                        f"Este bot es de uso privado y exclusivo.\n"
                        f"Tu ID: <code>{user_id}</code>\n"
                        f"Tu usuario: <code>@{from_user.get('username', 'sin_alias')}</code>"
                    )
                    continue

                text = (msg.get("text") or "").strip()
                text_lower = text.lower().strip()
                if text:
                    print(f"📩 Mensaje de {user_label} ({chat_id}): '{text}'", flush=True)

                # 2. Comando /start o /ayuda
                if text_lower.startswith("/start") or text_lower.startswith("/help") or text_lower.startswith("/ayuda") or text_lower == "ayuda":
                    print(f"👋 Usuario autorizado conectado: {user_label}", flush=True)
                    send_message(
                        chat_id,
                        f"👋 ¡Hola <b>{from_user.get('first_name', '')}</b>! Bienvenido a tu Creador de Videos de <b>Misterio y Curiosidades</b>.\n\n"
                        f"🎬 <b>¿Cómo crear tu video?</b>\n\n"
                        f"1️⃣ Envía todas tus <b>fotos</b> (como álbum, sueltas o carpeta de archivos sin comprimir).\n"
                        f"2️⃣ Envíame el guion largo como un <b>mensaje normal de chat</b> (o un archivo .txt).\n"
                        f"<i>(¡O también puedes enviar el texto primero y las fotos después!)</i>\n\n"
                        f"🎙️ <i>Escribe /voces o /abuelo para escuchar muestras y elegir a tu narrador.</i>\n"
                        f"🛑 <i>Escribe /cancelar en cualquier momento para reiniciar todo.</i>"
                    )
                    continue

                # 3. Comando /cancelar o /nuevo
                if text_lower in ["/cancelar", "/nuevo", "/reset", "/limpiar", "cancelar", "reiniciar"]:
                    with media_lock:
                        incoming_media.pop(chat_id, None)
                    with sessions_lock:
                        user_sessions.pop(chat_id, None)
                    with jobs_lock:
                        if chat_id in active_jobs:
                            active_jobs[chat_id]["cancel"] = True

                    send_message(
                        chat_id,
                        "🛑 <b>Proceso cancelado y sesión reiniciada.</b>\nSe han limpiado las fotos y guiones pendientes. Puedes empezar de nuevo cuando quieras."
                    )
                    continue

                # 4. Comando /voces o /abuelo (Audición interactiva directa en Telegram)
                is_abuelo_request = (
                    text_lower.startswith("/voces")
                    or text_lower.startswith("/abuelo")
                    or text_lower.startswith("/muestras")
                    or text_lower.startswith("/narrador")
                    or text_lower in ["abuelo", "voces", "muestras", "abuelito", "abuelos", "narrador", "escuchar voces"]
                    or "tipo abuelo" in text_lower
                    or "voz de abuelo" in text_lower
                    or "como abuelo" in text_lower
                )
                if is_abuelo_request:
                    current_v = user_voice_selection.get(chat_id, VOICE_PROFILES["luis"])
                    send_message(
                        chat_id,
                        f"👴 <b>Audición de Voces Tipo Abuelo / Narrador Sabio</b>\n\n"
                        f"📌 Tu voz activa actual es: <b>{current_v['nombre']}</b>\n\n"
                        f"A continuación te envío <b>4 muestras de audio</b> con estilo abuelo/historiador para que las escuches y toques cuál prefieres:"
                    )

                    samples = [
                        (
                            os.path.join(BASE_DIR, "muestras_abuelo", "gonzalo_abuelo.mp3"),
                            "👴 <b>1. Gonzalo (Colombia)</b>\n"
                            "• <i>Estilo:</i> Dulce, tierno, pausado y afectuoso (el abuelo entrañable).\n"
                            "• Para activarlo toca 👉 /usar_gonzalo",
                            "Gonzalo - Abuelo Dulce"
                        ),
                        (
                            os.path.join(BASE_DIR, "muestras_abuelo", "luis_abuelo.mp3"),
                            "👴 <b>2. Luis (Ecuador - Calibrado Abuelo)</b>\n"
                            "• <i>Estilo:</i> Grave, paternal, sereno y sabio (el abuelo patriarca).\n"
                            "• Para activarlo toca 👉 /usar_luis_abuelo",
                            "Luis - Abuelo Sabio"
                        ),
                        (
                            os.path.join(BASE_DIR, "muestras_abuelo", "manuel_abuelo.mp3"),
                            "👴 <b>3. Manuel (Cuba)</b>\n"
                            "• <i>Estilo:</i> Maduro, campechano, cálido y narrador de fogata.\n"
                            "• Para activarlo toca 👉 /usar_manuel",
                            "Manuel - Abuelo Fogata"
                        ),
                        (
                            os.path.join(BASE_DIR, "muestras_abuelo", "alonso_abuelo.mp3"),
                            "👴 <b>4. Alonso (Neutro)</b>\n"
                            "• <i>Estilo:</i> Clásico, respetable, pausado (cronista / historiador veterano).\n"
                            "• Para activarlo toca 👉 /usar_alonso",
                            "Alonso - Abuelo Historiador"
                        ),
                    ]

                    for s_path, s_cap, s_title in samples:
                        if os.path.exists(s_path):
                            send_audio(chat_id, s_path, caption=s_cap, title=s_title, performer="Creador de Videos")
                            time.sleep(0.4)
                        else:
                            print(f"⚠️ Archivo de muestra no encontrado: {s_path}", flush=True)

                    send_message(
                        chat_id,
                        "💡 <i>Para volver a la voz original de Luis maduro toca 👉 /usar_luis</i>"
                    )
                    continue

                # 5. Comandos para cambiar de voz (/usar_...)
                if text_lower in ["/usar_gonzalo", "/usar_luis_abuelo", "/usar_luis", "/usar_manuel", "/usar_alonso"]:
                    key = text_lower.replace("/usar_", "")
                    if key in VOICE_PROFILES:
                        user_voice_selection[chat_id] = VOICE_PROFILES[key]
                        v = VOICE_PROFILES[key]
                        send_message(
                            chat_id,
                            f"✅ <b>¡Voz cambiada exitosamente!</b>\n\n"
                            f"🗣️ <b>Voz activa:</b> {v['nombre']}\n"
                            f"📖 <i>{v['desc']}</i>\n\n"
                            f"Tus próximos videos se crearán automáticamente con esta voz."
                        )
                    continue

                # 6. Comando /voz (Consultar voz actual)
                if text_lower in ["/voz", "voz", "mi voz", "/voces_actual"]:
                    current_v = user_voice_selection.get(chat_id, VOICE_PROFILES["luis"])
                    send_message(
                        chat_id,
                        f"🎙️ <b>Voz actual de tu narrador:</b>\n"
                        f"👉 <b>{current_v['nombre']}</b>\n"
                        f"<i>{current_v['desc']}</i>\n\n"
                        f"Para escuchar muestras y cambiarla escribe /voces o /abuelo."
                    )
                    continue

                # 4. Recepción de fotos normales (comprimidas)
                if "photo" in msg:
                    highest_photo = msg["photo"][-1]["file_id"]
                    caption = (msg.get("caption") or "").strip()

                    with media_lock:
                        if chat_id not in incoming_media:
                            incoming_media[chat_id] = {
                                "photos": [],
                                "caption": "",
                                "user_info": user_label,
                                "last_received": time.time()
                            }
                        incoming_media[chat_id]["photos"].append(highest_photo)
                        incoming_media[chat_id]["last_received"] = time.time()
                        if caption and not incoming_media[chat_id]["caption"]:
                            incoming_media[chat_id]["caption"] = caption

                # 5. Recepción de documentos (archivos de imagen o archivos .txt)
                elif "document" in msg:
                    doc = msg["document"]
                    file_name = (doc.get("file_name") or "").lower()
                    mime = (doc.get("mime_type") or "").lower()
                    caption = (msg.get("caption") or "").strip()

                    is_image_file = (
                        any(file_name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif"])
                        or mime.startswith("image/")
                    )

                    if is_image_file:
                        with media_lock:
                            if chat_id not in incoming_media:
                                incoming_media[chat_id] = {
                                    "photos": [],
                                    "caption": "",
                                    "user_info": user_label,
                                    "last_received": time.time()
                                }
                            incoming_media[chat_id]["photos"].append(doc["file_id"])
                            incoming_media[chat_id]["last_received"] = time.time()
                            if caption and not incoming_media[chat_id]["caption"]:
                                incoming_media[chat_id]["caption"] = caption

                    elif file_name.endswith(".txt") or "text" in mime:
                        file_id = doc["file_id"]
                        info_resp = requests.get(f"{API_URL}/getFile?file_id={file_id}", timeout=15).json()
                        if info_resp.get("ok"):
                            rel_path = info_resp["result"]["file_path"]
                            file_content = requests.get(f"{FILE_API_URL}/{rel_path}", timeout=30).content
                            doc_text = file_content.decode("utf-8", errors="ignore").strip()

                            if doc_text:
                                with sessions_lock:
                                    sess = user_sessions.setdefault(chat_id, {"photos": [], "user_info": user_label, "text": ""})
                                    sess["user_info"] = user_label

                                    if sess.get("photos"):
                                        photos_to_render = list(sess["photos"])
                                        sess["photos"] = []
                                        sess["text"] = ""
                                        t = threading.Thread(
                                            target=process_video_task,
                                            args=(chat_id, user_label, photos_to_render, doc_text),
                                            daemon=True
                                        )
                                        t.start()
                                    else:
                                        sess["text"] = doc_text
                                        palabras = len(doc_text.split())
                                        send_message(
                                            chat_id,
                                            f"📄 <b>Guion recibido desde archivo ({doc.get('file_name', 'guion.txt')}):</b>\n"
                                            f"📊 {palabras} palabras ({len(doc_text)} caracteres).\n\n"
                                            f"📸 Ahora envíame las <b>fotos</b> para ensamblar tu video."
                                        )

                # 6. Recepción de texto normal en el chat
                elif text:
                    with sessions_lock:
                        sess = user_sessions.setdefault(chat_id, {"photos": [], "user_info": user_label, "text": ""})
                        sess["user_info"] = user_label

                        if sess.get("photos"):
                            photos_to_render = list(sess["photos"])
                            sess["photos"] = []
                            sess["text"] = ""
                            t = threading.Thread(
                                target=process_video_task,
                                args=(chat_id, user_label, photos_to_render, text),
                                daemon=True
                            )
                            t.start()
                        else:
                            sess["text"] = text
                            palabras = len(text.split())
                            send_message(
                                chat_id,
                                f"📝 <b>Guion guardado:</b> {palabras} palabras ({len(text)} caracteres).\n\n"
                                f"📸 Ahora envíame las <b>fotos</b> (todas juntas o sueltas) para ensamblar tu video.\n"
                                f"<i>(O escribe /cancelar si deseas cambiarlo)</i>"
                            )

        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as ex:
            print(f"⚠️ Error en bucle principal: {ex}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    run_telegram_bot()
