# Agente IA – Videos Infantiles y Cuentos (Voz Latina Femenina + Efectos)

Este agente de n8n está especialmente diseñado para crear **cuentos y videos infantiles verticales (9:16)** a partir de ilustraciones o imágenes, listo para YouTube Kids, YouTube Shorts, TikTok y Reels familiares.

---

## 🌟 Características Especiales para Niños

1. **Carpeta Dedicada de Ilustraciones:** Guarda tus dibujos o imágenes de cuentos en `imagenes_infantiles/` (así no se mezclan con los videos documentales ni generales).
2. **Voz Latina Femenina Tierna y Divertida (100% Gratuita):**
   - `es-MX-DaliaNeural` (México): Alegre, dinámica y divertida, ideal para aventuras y captar la atención de los más pequeños.
   - `es-CO-SalomeNeural` (Colombia): Dulce, suave y acogedora, perfecta para cuentos antes de dormir.
   - `es-MX-BeatrizNeural` (México): Cálida y maternal.
3. **Subtítulos Infantiles en Azul Celeste y Morado Mágico:**
   - Palabras base en **Azul Celeste brillante** (`#4FD5FF`).
   - Palabras clave destacadas en **Morado Mágico** (`#B040F0`).
   - Borde grueso oscuro para máxima legibilidad sobre cualquier dibujo o fondo colorido.
4. **Animaciones Suaves Ken Burns:** Acercamientos, alejamientos y paneos suaves en cada ilustración como si fuera un libro animado.
5. **Transiciones Mágicas:** Disolución suave (`dissolve`) entre cada página o escena del cuento.
6. **Copywriting Infantil con IA (Gemini):** Título llamativo con emojis amigables (ej: 🐉 ✨), descripción tierna y hashtags infantiles (#cuentosinfantiles, #historiasparaniños).
7. **Salida Independiente en `videos_listos/`:** Genera `video_infantil_final.mp4` sin sobreescribir tus videos documentales (`video_narrado_final.mp4`).

---

## 📋 JSON para importar en n8n

Copia el siguiente bloque y pégalo directamente en tu lienzo de n8n (`Ctrl + V`):

```json
{
  "name": "Agente IA – Videos Infantiles y Cuentos (Voz Latina Femenina + Efectos)",
  "nodes": [
    {
      "parameters": {},
      "id": "trigger_manual_infantil",
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
        "jsCode": "// ==========================================================================\n// CONFIGURACIÓN DE CUENTOS Y VIDEOS INFANTILES\n// ==========================================================================\n\n// 1. CARPETA EXCLUSIVA PARA IMÁGENES INFANTILES:\n// Coloca aquí las ilustraciones de tu cuento (ej. 1.png, 2.jpg, 3.jpg...)\nconst carpetaImagenes = '/media/susej/C06E72656E72545E/Users/PC/Desktop/creador_videos/imagenes_infantiles';\n\n// 2. LISTA DE IMÁGENES (OPCIONAL):\n// - Si dejas [] (vacío), tomará TODAS las imágenes de la carpeta en orden numérico/alfabético.\n// - O puedes especificar los nombres: ['escena1.jpg', 'escena2.jpg']\nconst imagenes = [];\n\n// 3. TEXTO DE LA NARRACIÓN DEL CUENTO:\n// - OPCIÓN A: Pega aquí la historia infantil o cuento.\n// - OPCIÓN B: Déjalo vacío ('') y guarda un archivo 'narracion.txt' en la carpeta de imágenes.\nconst textoNarracion = `Había una vez un pequeño dragón que le temía al fuego, pero descubrió un secreto mágico que salvó a todo su bosque.`;\n\n// 4. VOZ FEMENINA EN ESPAÑOL LATINOAMERICANO (100% Gratuita, Tierna y Divertida):\n// - 'es-MX-DaliaNeural'   -> México (Alegre, divertida, expresiva - ¡Recomendada para niños!)\n// - 'es-CO-SalomeNeural'  -> Colombia (Dulce, tierna y acogedora para cuentos de dormir)\n// - 'es-MX-BeatrizNeural' -> México (Cálida y amigable)\nconst voz = 'es-MX-DaliaNeural';\n\n// 5. ESTILO DE SUBTÍTULOS PARA NIÑOS:\n// 'infantil' = Letras en Azul Celeste y Morado Mágico con borde oscuro contrastado.\nconst subtitulos = true;\nconst estiloSubtitulos = 'infantil';\n\n// 6. TRANSICIONES SUAVES:\n// 'dissolve' (desvanecimiento cruzado mágico entre páginas/imágenes) o 'fade'\nconst transicion = 'dissolve';\nconst duracionTransicionSegundos = 0.7;\n\nreturn [{\n  json: {\n    accion: 'video_infantil',\n    carpeta_imagenes: carpetaImagenes,\n    imagenes: imagenes,\n    texto_narracion: textoNarracion,\n    voz: voz,\n    transicion: transicion,\n    duracion_transicion_segundos: duracionTransicionSegundos,\n    subtitulos: subtitulos,\n    estilo_subtitulos: estiloSubtitulos\n  }\n}];"
      },
      "id": "config_infantil_node",
      "name": "Configuración Cuento Infantil",
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
      "id": "ffmpeg_infantil_node",
      "name": "Renderizar Cuento (FFmpeg + Voz Latina + Ken Burns)",
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
        "text": "=NARRACIÓN DEL CUENTO:\n\"{{ $json.texto_narracion || $('Configuración Cuento Infantil').first().json.texto_narracion }}\"\n\nDURACIÓN DEL VIDEO: {{ $json.duracion_segundos }} segundos ({{ $json.total_imagenes }} ilustraciones animadas con zoom y transiciones mágicas).\n\nDiseña el copy perfecto para publicar este cuento infantil en YouTube Kids, Shorts, TikTok y Reels familiares.",
        "options": {
          "systemMessage": "Eres un Director Creativo especialista en Cuentos Infantiles y Contenido Educativo Familiar para Redes Sociales.\n\nTU MISIÓN:\nAnalizar la narración del cuento infantil recién renderizado y generar el copy perfecto y familiar para publicarlo.\n\nREGLAS DE COPYWRITING:\n1. TÍTULO / GANCHO: Un título divertido, llamativo y con emojis amigables para niños y padres (ej: 🐉 ¡El pequeño dragón que salvó el bosque!).\n2. DESCRIPCIÓN: 2 a 3 líneas tiernas y emocionantes explicando la aventura o moraleja del cuento.\n3. PREGUNTA / CTA: Una pregunta dulce para que los niños o sus papás respondan en los comentarios.\n4. HASHTAGS: De 6 a 10 hashtags familiares relevantes (ej: #cuentosinfantiles, #historiasparaniños, #cuentosparadormir, #animacion, #paraniños).\n\nSALIDA OBLIGATORIA (Exclusivamente formato JSON válido, sin backticks ni texto adicional):\n{\n  \"titulo_gancho\": \"[TÍTULO CON EMOJIS]\",\n  \"descripcion\": \"[Descripción tierna del cuento]\",\n  \"cta\": \"[¿Te gustaría conocer más aventuras de este dragón? ¡Cuéntanos en los comentarios!]\",\n  \"hashtags\": [\"#cuentosinfantiles\", \"#historiasparaniños\", \"#paraniños\", \"#cuentosparadormir\", \"#shorts\"]\n}"
        }
      },
      "id": "agent_copy_infantil_node",
      "name": "Agente IA – Copy Infantil y Hashtags",
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
      "id": "lm_gemini_infantil_node",
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
        "jsCode": "const videoInfo = $('Renderizar Cuento (FFmpeg + Voz Latina + Ken Burns)').first().json;\nconst aiRaw = $input.first().json.output || $input.first().json.text || '';\n\nlet copyData = {};\ntry {\n  const match = aiRaw.match(/\\{[\\s\\S]*\\}/);\n  copyData = JSON.parse(match ? match[0] : aiRaw);\n} catch (e) {\n  copyData = {\n    titulo_gancho: '✨ UN CUENTO MÁGICO PARA SOÑAR 🌟',\n    descripcion: 'Acompaña a nuestros personajes en esta tierna y divertida historia llena de magia y aprendizaje.',\n    cta: '¿Cuál fue tu parte favorita del cuento? ¡Dinos en los comentarios y suscríbete para más cuentos!',\n    hashtags: ['#cuentosinfantiles', '#historiasparaniños', '#paraniños', '#cuentosparadormir', '#shorts']\n  };\n}\n\nreturn [{\n  json: {\n    status: '🎉 ¡Video infantil generado con éxito!',\n    archivo_final: videoInfo.video_final_path || videoInfo.video_path || '/media/susej/C06E72656E72545E/Users/PC/Desktop/creador_videos/videos_listos/video_infantil_final.mp4',\n    duracion_segundos: videoInfo.duracion_segundos || 0,\n    total_ilustraciones: videoInfo.total_imagenes || 0,\n    voz_narradora: videoInfo.voz_utilizada || 'es-MX-DaliaNeural (Femenina Latina Infantil)',\n    estilo_subtitulos: 'Azul Celeste y Morado Mágico',\n    transicion_utilizada: videoInfo.transicion_utilizada || 'dissolve',\n    subtitulos_incluidos: videoInfo.subtitulos_incluidos !== false,\n    copy_para_redes: {\n      titulo_gancho: copyData.titulo_gancho,\n      descripcion: copyData.descripcion,\n      cta: copyData.cta,\n      hashtags: copyData.hashtags || []\n    },\n    carpeta_en_tu_pc: 'creador_videos/videos_listos/'\n  }\n}];"
      },
      "id": "resultado_infantil_node",
      "name": "Resultado Final (.mp4 Infantil + Copy)",
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
            "node": "Configuración Cuento Infantil",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Configuración Cuento Infantil": {
      "main": [
        [
          {
            "node": "Renderizar Cuento (FFmpeg + Voz Latina + Ken Burns)",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Renderizar Cuento (FFmpeg + Voz Latina + Ken Burns)": {
      "main": [
        [
          {
            "node": "Agente IA – Copy Infantil y Hashtags",
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
            "node": "Agente IA – Copy Infantil y Hashtags",
            "type": "ai_languageModel",
            "index": 0
          }
        ]
      ]
    },
    "Agente IA – Copy Infantil y Hashtags": {
      "main": [
        [
          {
            "node": "Resultado Final (.mp4 Infantil + Copy)",
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
  "versionId": "d3c4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
  "meta": {
    "instanceId": "7360062f295944471577ac697535dbd144cef4df05828e5474e3d7af599a06d4"
  },
  "nodeGroups": [],
  "id": "AgenteVideosInfantilesVozFemenina",
  "tags": []
}
```

---

## 🚀 ¿Cómo usar este flujo para cuentos de niños?

1. **Copia el JSON:** Selecciona el bloque de arriba y cópialo.
2. **Pégalo en n8n:** Abre tu n8n en el navegador (`http://localhost:5678`), crea un nuevo flujo y pulsa `Ctrl + V`.
3. **Coloca las imágenes:** Pon las ilustraciones de tu cuento en la carpeta:
   `creador_videos/imagenes_infantiles/`
4. **Escribe el cuento:** Abre el nodo **"Configuración Cuento Infantil"** y escribe o pega el texto en `textoNarracion` (o crea un archivo `narracion.txt` en la carpeta `imagenes_infantiles`).
5. **Ejecuta el flujo:** Haz clic en **"Test workflow"** o **"Probar ahora"**.
6. **¡Listo!** En unos segundos encontrarás tu video infantil listo en:
   - `creador_videos/videos_listos/video_infantil_final.mp4`
