#!/usr/bin/env bash
# Script para iniciar todo el sistema de creador de videos

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "🚀 INICIANDO CREADOR DE VIDEOS AUTOMÁTICO"
echo "=========================================="

# 1. Verificar si el servicio de video ya está activo
if curl -s http://localhost:5679/health > /dev/null; then
    echo "✅ Servicio de renderizado ya está corriendo en el puerto 5679."
else
    echo "🎬 Iniciando servicio de renderizado (render_service.py)..."
    nohup python3 "$DIR/render_service.py" > "$DIR/render_service.log" 2>&1 &
    sleep 2
    if curl -s http://localhost:5679/health > /dev/null; then
        echo "✅ Servicio de renderizado iniciado con éxito."
    else
        echo "⚠️ No se pudo verificar el servicio de video. Revisa render_service.log."
    fi
fi

# 2. Iniciar Docker / n8n si no está corriendo
if curl -s http://localhost:5678 > /dev/null; then
    echo "✅ n8n ya está activo en http://localhost:5678"
else
    echo "🐳 Iniciando contenedores de Docker..."
    docker compose up -d 2>/dev/null || sudo docker compose up -d
    echo "✅ n8n iniciado en http://localhost:5678"
fi

# 3. Iniciar el Bot de Telegram si no está corriendo
if pgrep -f "telegram_bot.py" > /dev/null; then
    echo "✅ Bot de Telegram ya está activo."
else
    echo "🤖 Iniciando Bot de Telegram (@Su_creador_videos_bot)..."
    nohup python3 "$DIR/telegram_bot.py" > "$DIR/telegram_bot.log" 2>&1 &
    sleep 1
    if pgrep -f "telegram_bot.py" > /dev/null; then
        echo "✅ Bot de Telegram iniciado con éxito."
    else
        echo "⚠️ No se pudo iniciar el bot de Telegram. Revisa telegram_bot.log."
    fi
fi

echo ""
echo "🎉 ¡Todo listo!"
echo "👉 n8n: http://localhost:5678"
echo "👉 Bot de Telegram: @Su_creador_videos_bot"
echo "=========================================="
