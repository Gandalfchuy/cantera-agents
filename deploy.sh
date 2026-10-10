#!/bin/bash
# ========================================================
# SCRIPT DE INSTALACIÓN Y DESPLIEGUE: LA CANTERA 🎙️
# Para servidores Ubuntu / Debian
# ========================================================

set -e

echo "🚀 Iniciando despliegue de La Cantera Bot en el servidor..."

APP_DIR="/root/cantera"

# 1. Instalar dependencias del sistema
echo "📦 Actualizando paquetes e instalando Python..."
apt update -y
apt install -y python3 python3-pip python3-venv git

# 2. Asegurar directorio
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 3. Crear entorno virtual
echo "🐍 Configurando entorno virtual de Python..."
if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi

# 4. Instalar librerías
echo "📥 Instalando requerimientos..."
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. Instalar y configurar servicio systemd
echo "⚙️ Configurando servicio de auto-arranque systemd..."
cp "$APP_DIR/cantera-bot.service" /etc/systemd/system/cantera-bot.service

systemctl daemon-reload
systemctl enable cantera-bot
systemctl restart cantera-bot

echo ""
echo "✅ ¡DESPLIEGUE COMPLETADO CON ÉXITO!"
echo "El bot ya está corriendo 24/7 en segundo plano."
echo "Para ver el estado en tiempo real ejecuta:"
echo "   systemctl status cantera-bot"
echo "Para ver los logs en vivo:"
echo "   journalctl -u cantera-bot -f"
echo "========================================================"
