#!/usr/bin/env bash
# Script para detener ordenadamente n8n, postgres y el servicio de video

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "🛑 DETENIENDO CREADOR DE VIDEOS Y N8N"
echo "=========================================="

# 1. Detener el servicio de renderizado de video
if pgrep -f "render_service.py" > /dev/null; then
    echo "🎬 Deteniendo servicio de renderizado (render_service.py)..."
    pkill -f "render_service.py"
    echo "✅ Servicio de renderizado detenido."
else
    echo "ℹ️ El servicio de renderizado ya estaba detenido."
fi

# 2. Detener el bot de Telegram
if pgrep -f "telegram_bot.py" > /dev/null; then
    echo "🤖 Deteniendo bot de Telegram..."
    pkill -f "telegram_bot.py"
    echo "✅ Bot de Telegram detenido."
else
    echo "ℹ️ El bot de Telegram ya estaba detenido."
fi

# 3. Detener los contenedores de Docker
echo "🐳 Deteniendo contenedores de Docker..."
docker compose stop 2>/dev/null || sudo docker compose stop

echo ""
echo "✅ Todo ha sido detenido correctamente y tus datos están guardados."
echo "=========================================="
