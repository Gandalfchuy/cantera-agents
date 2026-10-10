# Guía de Despliegue en Servidor VPS (Hetzner / DigitalOcean / AWS) 🌐
**Proyecto:** La Cantera 🎙️  
**Archivo principal:** `bot_orchestrator.py`

Esta guía te muestra cómo dejar corriendo el bot de Telegram de forma continua 24/7 en cualquier servidor privado virtual (VPS) económico (~$3.50 a $5 USD/mes) sin depender de Google Cloud.

---

## 1. Crear el VPS
1. Entra a **Hetzner Cloud** ([hetzner.com](https://www.hetzner.com/cloud)) o **DigitalOcean** ([digitalocean.com](https://www.digitalocean.com/)).
2. Crea un servidor básico:
   * **Sistema Operativo:** Ubuntu 22.04 o 24.04 LTS.
   * **Tamaño:** El plan más pequeño (1 vCPU, 1 GB o 2 GB RAM es más que suficiente).

---

## 2. Conectarte al Servidor
Abre tu terminal en Windows (PowerShell) y conéctate por SSH:
```bash
ssh root@IP_DE_TU_SERVIDOR
```

---

## 3. Instalar Python y Descargar el Proyecto
En la terminal de tu servidor, ejecuta:
```bash
# Actualizar el sistema e instalar Python
apt update && apt install -y python3 python3-pip git

# Crear carpeta del proyecto
mkdir -p /root/cantera && cd /root/cantera

# Instalar librería requests
pip3 install requests
```

Copia o sube los archivos de este proyecto:
* `bot_orchestrator.py`
* `scripts/google_sync.py`
* `scripts/notify_telegram.py`

---

## 4. Dejar el Bot Corriendo 24/7 (En segundo plano)

### Opción Rápida (nohup):
```bash
nohup python3 bot_orchestrator.py > bot.log 2>&1 &
```
*(El bot seguirá funcionando aunque cierres la terminal o apagues tu computadora).*

### Opción Profesional (Servicio del Sistema - Auto-reinicio si se cae):
Crea un servicio systemd:
```bash
nano /etc/systemd/system/cantera-bot.service
```

Pega este contenido:
```ini
[Unit]
Description=Orquestador de Telegram La Cantera
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/cantera
ExecStart=/usr/bin/python3 /root/cantera/bot_orchestrator.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Guarda y activa el servicio:
```bash
systemctl daemon-reload
systemctl enable cantera-bot
systemctl start cantera-bot
```

Para verificar que esté corriendo:
```bash
systemctl status cantera-bot
```

¡Listo! A partir de ese momento, tu equipo de agentes estará vivo 24/7 en la nube y todo lo manejarás tocando botones en Telegram desde tu teléfono.
