import os
import sys
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CHAT_ID = os.getenv("AUTHORIZED_CHAT_ID", "")

def send_telegram(text: str, chat_id: str = DEFAULT_CHAT_ID):
    """Envía un mensaje formateado en Markdown a Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        res = send_telegram(message)
        print(res)
    else:
        print("Uso: python notify_telegram.py <MENSAJE>")
