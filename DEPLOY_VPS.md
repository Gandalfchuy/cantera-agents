# Guía de Despliegue en Servidor VPS / VPC 🌐
**Proyecto:** La Cantera 🎙️  
**Estado:** 100% Listo para Producción

Esta guía contiene los pasos exactos para subir este proyecto a cualquier servidor Linux en la nube (Hetzner, DigitalOcean, AWS Lightsail, Linode, etc.) y dejarlo corriendo de forma ininterrumpida las 24 horas del día.

---

## 📋 Resumen de Archivos Preparados para el Servidor

* ⚙️ `.env` — Archivo con tus credenciales y tokens (Telegram, Groq, Google Apps Script).
* 🐍 `bot_orchestrator.py` — Código principal del bot y sus agentes con la lógica de lotes y bloqueo.
* 📦 `requirements.txt` — Dependencias de Python (`requests`, `python-dotenv`).
* 🚀 `deploy.sh` — Script de despliegue automático en 1 solo paso.
* 🛠️ `cantera-bot.service` — Configuración de auto-arranque systemd (se reinicia solo si el servidor se reinicia).
* 🐳 `Dockerfile` y `docker-compose.yml` — Alternativa opcional para correr con Docker.

---

## 🚀 Paso 1: Subir los Archivos a tu Servidor

Elige la forma que te resulte más cómoda:

### Opción A: Vía WinSCP o FileZilla (Interfaz Gráfica - Muy Fácil)
1. Descarga e instala [WinSCP](https://winscp.net/) o FileZilla.
2. Conéctate a tu servidor usando:
   * **Host:** La IP pública de tu VPS (ej. `195.201.x.x`).
   * **Usuario:** `root`
   * **Contraseña** o Llave SSH de tu VPS.
3. En el servidor, crea la carpeta `/root/cantera`.
4. Arrastra todos los archivos de tu carpeta local `cantera` hacia `/root/cantera/`.

### Opción B: Vía Terminal PowerShell (SCP)
Desde tu computadora, abre PowerShell y ejecuta:
```powershell
scp -r "c:\Users\Dare Jeezuz\Documents\cantera\*" root@TU_IP_DEL_VPS:/root/cantera/
```

### Opción C: Vía GitHub
Si usas Git, clónalo directamente en tu servidor:
```bash
git clone https://github.com/tu-usuario/cantera.git /root/cantera
cd /root/cantera
```

---

## ⚡ Paso 2: Ejecutar el Instalador Automático

1. Conéctate a tu servidor por SSH desde PowerShell o tu terminal:
   ```bash
   ssh root@TU_IP_DEL_VPS
   ```
2. Entra a la carpeta del proyecto y dale permisos de ejecución a `deploy.sh`:
   ```bash
   cd /root/cantera
   chmod +x deploy.sh
   ./deploy.sh
   ```

El script hará todo en automático:
* Instalará Python y librerías necesarias.
* Creará el entorno virtual `.venv`.
* Configurará el servicio `cantera-bot` en Linux.
* Activará el inicio automático al encender el servidor.
* Dejará el bot corriendo 24/7.

---

## 🔍 Comandos Útiles para Monitorear tu Bot en el VPS

Una vez desplegado, puedes gestionar el servicio con estos comandos estándar de Linux:

* **Ver si el bot está corriendo:**
  ```bash
  systemctl status cantera-bot
  ```
* **Ver los registros/logs de actividad en vivo:**
  ```bash
  journalctl -u cantera-bot -f
  ```
* **Reiniciar el bot:**
  ```bash
  systemctl restart cantera-bot
  ```
* **Detener el bot temporalmente:**
  ```bash
  systemctl stop cantera-bot
  ```

---

## 🐳 Alternativa con Docker (Si tu VPS usa Docker)

Si prefieres usar Docker en lugar de systemd:
```bash
cd /root/cantera
docker compose up -d --build
```
Para ver logs con Docker:
```bash
docker compose logs -f
```
