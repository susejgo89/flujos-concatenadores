#!/usr/bin/env python3
"""
Servicio local de renderizado de video para n8n (Puerto 5679)
Permite a n8n ejecutar Edge-TTS, Pollinations y FFmpeg sin requerir nodos de terminal bloqueados.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import subprocess
import sys
import re

PORT = 5679
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"video_render_service"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            data = json.loads(body)
        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"JSON invalido: {e}"}).encode("utf-8"))
            return

        output_dir = os.path.join(BASE_DIR, "videos_listos")
        os.makedirs(output_dir, exist_ok=True)
        
        accion = data.get("accion", "")
        if accion in ("imagenes_narracion", "video_infantil") or data.get("tipo") in ("imagenes_narracion", "video_infantil") or "carpeta_imagenes" in data or "texto_narracion" in data:
            # Modo 3: Crear video con imágenes + narración en off + animaciones
            estilo = data.get("estilo_subtitulos", "documental")
            tipo_archivo = "video_infantil" if (accion == "video_infantil" or estilo == "infantil") else "video_narrado"
            print(f"🎬 Solicitud de {tipo_archivo} (imágenes + narración en off) recibida.")
            param_path = os.path.join(output_dir, f"{tipo_archivo}_datos.json")
            with open(param_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            engine_script = os.path.join(BASE_DIR, "image_narration_engine.py")
            cmd = [sys.executable, engine_script, param_path]
            expected_video = os.path.join(output_dir, f"{tipo_archivo}_final.mp4")
        elif accion == "concatenar_subtitulos" or "clips" in data or data.get("tipo") == "concatenar":
            # Modo 2: Concatenar videos con transiciones y subtítulos llamativos
            print(f"🎬 Solicitud de concatenación y subtitulado recibida.")
            param_path = os.path.join(output_dir, "concat_datos.json")
            with open(param_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            engine_script = os.path.join(BASE_DIR, "concat_subtitles_engine.py")
            cmd = [sys.executable, engine_script, param_path]
            expected_video = os.path.join(output_dir, "video_unido_final.mp4")
        else:
            # Modo 1: Generación automática completa (Shorts de Finanzas)
            print(f"🎬 Solicitud de video generativo recibida: '{data.get('titulo_video', 'Video')}'")
            guion_path = os.path.join(output_dir, "guion_datos.json")
            with open(guion_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            engine_script = os.path.join(BASE_DIR, "render_engine.py")
            cmd = [sys.executable, engine_script, guion_path]
            expected_video = os.path.join(output_dir, "video_final_60s.mp4")
        
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
            
            if proc.returncode == 0:
                # Intentar parsear el JSON que imprime el script
                try:
                    match = re.search(r'(\{[\s\S]*\})\s*$', proc.stdout)
                    if match:
                        resp_payload = json.loads(match.group(1))
                    else:
                        resp_payload = json.loads(proc.stdout.strip().split("\n")[-1])
                except Exception:
                    resp_payload = {
                        "status": "success",
                        "mensaje": "¡Video procesado y renderizado exitosamente!",
                        "video_path": expected_video,
                        "consola": proc.stdout[-500:]
                    }
                self.send_response(200)
            else:
                resp_payload = {
                    "status": "error",
                    "mensaje": "FFmpeg o procesamiento falló",
                    "stderr": proc.stderr[-500:],
                    "stdout": proc.stdout[-500:]
                }
                self.send_response(500)
        except Exception as ex:
            resp_payload = {"status": "error", "mensaje": str(ex)}
            self.send_response(500)

        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(resp_payload).encode("utf-8"))

def run():
    server = HTTPServer(("0.0.0.0", PORT), RenderHandler)
    print(f"🚀 Servicio de renderizado escuchando en http://0.0.0.0:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
