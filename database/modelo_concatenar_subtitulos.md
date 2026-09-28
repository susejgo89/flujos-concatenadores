# Agente IA – Concatenador de Videos y Subtítulos Llamativos (9:16)

Este flujo de n8n toma tus clips de video (`1.mp4`, `2.mp4` ... `13.mp4` o los que tengas en tu carpeta), extrae y transcribe automáticamente la **voz real** de cada escena sin costo, genera **subtítulos dinámicos de alto impacto estilo TikTok / Alex Hormozi** (con resaltado neón amarillo y verde fosforescente con borde negro grueso), los une con transiciones suaves de video (`dissolve`) y audio (`acrossfade`), y genera el **copy viral (título de gancho, descripción y hashtags)** con Gemini para publicar en TikTok, YouTube Shorts e Instagram Reels.

---

## 📋 JSON para importar en n8n

Copia todo el bloque siguiente y pégalo directamente en el lienzo de tu n8n (`Ctrl + V`):

```json
{
  "name": "Agente IA – Concatenador de Videos y Subtítulos Llamativos (9:16)",
  "nodes": [
    {
      "parameters": {},
      "id": "trigger_manual_concat",
      "name": "Probar ahora",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [
        0,
        200
      ]
    },
    {
      "parameters": {
        "jsCode": "// ==========================================================================\n// CONFIGURACIÓN DE TUS CLIPS Y TRANSICIONES\n// ==========================================================================\n\n// 1. CARPETA DONDE ESTÁN TUS VIDEOS:\n// Coloca tus clips de video (ej. 1.mp4, 2.mp4, ... 13.mp4) en esta carpeta.\nconst carpetaClips = '/media/susej/C06E72656E72545E/Users/PC/Desktop/creador_videos/videos_listos';\n\n// 2. LISTA DE VIDEOS A UNIR (OPCIONAL):\n// - Si dejas [] (vacío), unirá automáticamente TODOS los videos .mp4 en orden numérico (1, 2, 3...).\n// - O puedes especificar una lista exacta en orden: ['1.mp4', '2.mp4', ...]\nconst videos = [];\n\n// 3. TIPO DE TRANSICIÓN ENTRE CLIPS (FFmpeg xfade):\n// Opciones disponibles: 'dissolve' (disolución suave), 'fade' (fundido a negro),\n// 'wipeleft', 'wiperight', 'slideup', 'slidedown'\nconst transicion = 'dissolve';\nconst duracionTransicionSegundos = 0.5;\n\nreturn [{\n  json: {\n    accion: 'concatenar_subtitulos',\n    carpeta_clips: carpetaClips,\n    videos: videos,\n    transicion: transicion,\n    duracion_transicion_segundos: duracionTransicionSegundos\n  }\n}];"
      },
      "id": "config_clips_node",
      "name": "Configuración de Clips",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        260,
        200
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://172.17.0.1:5679",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json) }}",
        "options": {
          "timeout": 900000
        }
      },
      "id": "ffmpeg_concat_node",
      "name": "Renderizar Video y Subtítulos (FFmpeg + IA Voz)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        540,
        200
      ]
    },
    {
      "parameters": {
        "promptType": "define",
        "text": "=TRANSCRIPCIÓN REAL DEL AUDIO DEL VIDEO:\n\"{{ $json.transcripcion_completa }}\"\n\nDURACIÓN TOTAL: {{ $json.duracion_segundos }} segundos ({{ $json.total_clips_unidos }} escenas unidas).\n\nAnaliza la historia narrada en el video y genera el copy viral definitivo para publicarlo en TikTok, Instagram Reels y YouTube Shorts.",
        "options": {
          "systemMessage": "Eres un Director Creativo y Estratega de Contenido Viral para Redes Sociales (TikTok, YouTube Shorts, Instagram Reels).\n\nTU MISIÓN:\nAnalizar la transcripción real del video que acaba de ser procesado y diseñar el copy viral perfecto para publicar el video.\n\nREGLAS DE COPYWRITING:\n1. TÍTULO / GANCHO (Hook): Debe ser una sola línea en MAYÚSCULAS ultra llamativa que genere curiosidad o sorpresa en los primeros 3 segundos.\n2. DESCRIPCIÓN: Un texto persuasivo de 2 a 3 líneas que resuma el misterio o drama de la historia e invite a interactuar.\n3. LLAMADO A LA ACCIÓN (CTA): Una pregunta o invitación para comentar y seguir la cuenta.\n4. HASHTAGS: De 6 a 10 hashtags virales en tendencia relacionados con el tema real del video.\n\nSALIDA OBLIGATORIA (Exclusivamente en formato JSON válido, sin backticks ni texto adicional):\n{\n  \"titulo_gancho\": \"[TÍTULO VIRAL EN MAYÚSCULAS]\",\n  \"descripcion\": \"[Descripción intrigante del video]\",\n  \"cta\": \"[¿Conocías esta historia? Comenta abajo y síguenos para más]\",\n  \"hashtags\": [\"#historia\", \"#catastrofe\", \"#misterio\", \"#datoscuriosos\", \"#documental\"]\n}"
        }
      },
      "id": "agent_copy_node",
      "name": "Agente IA – Copy Viral y Hashtags",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.7,
      "position": [
        820,
        200
      ]
    },
    {
      "parameters": {
        "modelName": "models/gemini-1.5-flash",
        "options": {}
      },
      "id": "lm_gemini_copy",
      "name": "Google Gemini Chat Model",
      "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
      "typeVersion": 1,
      "position": [
        820,
        420
      ],
      "credentials": {
        "googlePalmApi": {
          "id": "lExZUtWLTVrA0gd6",
          "name": "Google Gemini(PaLM) Api account"
        }
      }
    },
    {
      "parameters": {
        "jsCode": "const videoInfo = $('Renderizar Video y Subtítulos (FFmpeg + IA Voz)').first().json;\nconst aiRaw = $input.first().json.output || $input.first().json.text || '';\n\nlet copyData = {};\ntry {\n  const match = aiRaw.match(/\\{[\\s\\S]*\\}/);\n  copyData = JSON.parse(match ? match[0] : aiRaw);\n} catch (e) {\n  copyData = {\n    titulo_gancho: 'HISTORIA IMPACTANTE QUE FUE BORRADA',\n    descripcion: 'Descubre el impactante suceso histórico que casi nadie conoce.',\n    cta: '¿Conocías esta historia? Comenta y síguenos para más.',\n    hashtags: ['#historia', '#documental', '#shorts', '#viral']\n  };\n}\n\nreturn [{\n  json: {\n    status: '🎉 ¡Video unido, subtitulado y copy viral generado con éxito!',\n    archivo_final: videoInfo.video_final_path || videoInfo.video_path || '/media/susej/C06E72656E72545E/Users/PC/Desktop/creador_videos/videos_listos/video_unido_final.mp4',\n    duracion_segundos: videoInfo.duracion_segundos || 0,\n    total_clips_unidos: videoInfo.total_clips_unidos || 0,\n    transicion_utilizada: videoInfo.transicion_utilizada || 'dissolve',\n    transcripcion_audio: videoInfo.transcripcion_completa || '',\n    copy_para_publicar: {\n      titulo_gancho: copyData.titulo_gancho || copyData.titulo_viral,\n      descripcion: copyData.descripcion,\n      cta: copyData.cta,\n      hashtags: copyData.hashtags || []\n    },\n    carpeta_en_tu_pc: 'creador_videos/videos_listos/'\n  }\n}];"
      },
      "id": "resultado_concat_node",
      "name": "Resultado Final (.mp4 + Copy)",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        1100,
        200
      ]
    }
  ],
  "pinData": {},
  "connections": {
    "Probar ahora": {
      "main": [
        [
          {
            "node": "Configuración de Clips",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Configuración de Clips": {
      "main": [
        [
          {
            "node": "Renderizar Video y Subtítulos (FFmpeg + IA Voz)",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Renderizar Video y Subtítulos (FFmpeg + IA Voz)": {
      "main": [
        [
          {
            "node": "Agente IA – Copy Viral y Hashtags",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Google Gemini Chat Model": {
      "ai_languageModel": [
        [
          {
            "node": "Agente IA – Copy Viral y Hashtags",
            "type": "ai_languageModel",
            "index": 0
          }
        ]
      ]
    },
    "Agente IA – Copy Viral y Hashtags": {
      "main": [
        [
          {
            "node": "Resultado Final (.mp4 + Copy)",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1",
    "binaryMode": "separate",
    "timezone": "America/Mexico_City"
  },
  "versionId": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6e",
  "meta": {
    "instanceId": "7360062f295944471577ac697535dbd144cef4df05828e5474e3d7af599a06d4"
  },
  "nodeGroups": [],
  "id": "AgenteConcatSubtitulos916",
  "tags": []
}
```
