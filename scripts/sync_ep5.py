import os
from google_sync import create_google_doc
from notify_telegram import send_telegram

def run():
    print("Subiendo Guion EP5...")
    with open("EP5. El estoicismo mal entendido.md", "r", encoding="utf-8") as f:
        script_content = f.read()
    r_script = create_google_doc("EP5. El estoicismo mal entendido", script_content, "La Cantera")
    print("Guion resultado:", r_script)

    print("Subiendo Redes EP5...")
    with open(os.path.join("instagram", "tiktok", "Redes_EP5.md"), "r", encoding="utf-8") as f:
        redes_content = f.read()
    r_redes = create_google_doc("Redes_EP5", redes_content, "La Cantera", subfolder="instagram/tiktok")
    print("Redes resultado:", r_redes)

    # Enviar resumen a Telegram con los enlaces de Drive
    msg = (
        "🎙️ *¡Entregables de EP5 Sincronizados con Google Drive!* 📁\n\n"
        f"📄 *Guion con SEO:* [Abrir en Drive]({r_script.get('url')})\n"
        f"📱 *Plan de Redes (IG/TikTok):* [Abrir en Drive]({r_redes.get('url')})\n\n"
        "💡 *NotebookLM:* Ya puedes ir a tu cuaderno de NotebookLM y pulsar 'Añadir fuente ➔ Google Drive' para cargar la investigación."
    )
    send_telegram(msg)
    print("Notificación enviada a Telegram.")

if __name__ == "__main__":
    run()
