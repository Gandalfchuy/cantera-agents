"""
ORQUESTADOR DE TELEGRAM - LA CANTERA 🎙️
Control de flujo de 6 fases con gestión estricta de estado por tema:
- Muestra enlaces de Investigación, Guion y Redes de cada tema existente.
- Deshabilita acciones ya generadas para cada tema.
- Bloquea el Análisis de Nicho (Fase 1) hasta que TODOS los temas del lote cumplan Fases 2, 3 y 5.
"""

import os
import sys
import time
import json
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List

# --- HEALTH CHECK HTTP SERVER (Para Coolify / Docker) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass  # Silenciar logs

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# --- CONFIGURACIÓN ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_CHAT_ID = os.getenv("AUTHORIZED_CHAT_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "")

STATE_FILE = "orchestrator_state.json"

# --- PERSISTENCIA DE ESTADO ---
def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando estado: {e}")
    return {"niche_analysis_done": False, "topics": []}

def save_state(state: Dict[str, Any]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def are_all_topics_completed(topics: List[Dict[str, Any]]) -> bool:
    if not topics:
        return True
    return all(t.get("completed", False) for t in topics)

# --- LLM: GROQ ---
def call_groq(prompt: str, system_prompt: str = "") -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=90)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Error Groq ({r.status_code}): {r.text}"
    except Exception as e:
        return f"Excepción Groq: {e}"

# --- GOOGLE DRIVE & SHEETS ---
def create_drive_doc(title: str, content: str, folder: str = "La Cantera", subfolder: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "action": "create_doc",
        "title": title,
        "content": content,
        "folder_name": folder,
        "subfolder": subfolder
    }
    try:
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=40)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def rename_drive_doc(file_id: str, new_title: str) -> Dict[str, Any]:
    payload = {
        "action": "rename_doc",
        "file_id": file_id,
        "new_title": new_title
    }
    try:
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_sheet_status(ep: int, status: str = "Aceptado") -> Dict[str, Any]:
    payload = {
        "action": "update_sheet_status",
        "ep_number": ep,
        "status": status
    }
    try:
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- TELEGRAM HELPERS ---
def send_telegram(text: str, reply_markup: Optional[Dict[str, Any]] = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": AUTHORIZED_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

# --- PANELES Y TECLADOS DINÁMICOS ---
def build_main_menu():
    state = load_state()
    topics = state.get("topics", [])
    all_done = are_all_topics_completed(topics)
    completed_count = sum(1 for t in topics if t.get("completed", False))
    total_count = len(topics)

    texto = "🎙️ *PANEL DE CONTROL GENERAL: LA CANTERA*\n\n"
    if total_count > 0:
        texto += f"📊 *Progreso del lote actual:* {completed_count}/{total_count} episodios completados\n\n"
        for t in topics:
            ep = t.get("ep_number", "?")
            title = t.get("title", "")
            # Iconos de fases
            f2_icon = "✅" if t.get("research_done") else "⏳"
            f3_icon = "✅" if t.get("script_approved") else ("📝" if t.get("script_done") else "⏳")
            f5_icon = "✅" if t.get("social_done") else "⏳"
            
            texto += f"• *EP{ep}:* {title[:48]}...\n"
            texto += f"  ↳ F2(Inv): {f2_icon} | F3(Guion): {f3_icon} | F5(Redes): {f5_icon}\n"
    else:
        texto += "ℹ️ No hay temas en cola actualmente. Puedes iniciar un nuevo análisis de nicho.\n"

    # Construcción de botones
    buttons = []
    
    # Botón Análisis de Nicho: BLOQUEADO si faltan temas por completar
    if all_done:
        buttons.append([{"text": "🔍 1. Análisis de Nicho (Fase 1) [Desbloqueado]", "callback_data": "act_nicho"}])
    else:
        buttons.append([{"text": f"🔒 1. Análisis de Nicho (Bloqueado: faltan {total_count - completed_count} temas)", "callback_data": "act_nicho_bloqueado"}])

    # Botones para gestionar cada tema individual
    if topics:
        buttons.append([{"text": "--- SELECCIONA UN TEMA PARA GESTIONAR ---", "callback_data": "noop"}])
        for t in topics:
            ep = t.get("ep_number", "?")
            status_tag = "✅" if t.get("completed") else "⏳"
            btn_title = f"{status_tag} EP{ep}: {t.get('title')[:32]}..."
            buttons.append([{"text": btn_title, "callback_data": f"ver_tema_{t['id']}"}])

    buttons.append([{"text": "📊 Auditoría Mensual (Fase 6)", "callback_data": "act_auditoria"}])

    return texto, {"inline_keyboard": buttons}

def build_topic_view(topic_id: int):
    state = load_state()
    topics = state.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return "⚠️ Tema no encontrado.", {"inline_keyboard": [[{"text": "🔙 Volver al Menú", "callback_data": "cmd_menu"}]]}

    ep = topic.get("ep_number", "?")
    title = topic.get("title", "")
    
    # Enlaces generados
    inv_url = topic.get("research_url")
    script_url = topic.get("script_url")
    social_url = topic.get("social_url")

    texto = f"📌 *GESTIÓN DEL EP{ep}*\n"
    texto += f"*{title}*\n\n"
    texto += "📁 *ENTREGABLES Y ENLACES DE GOOGLE DRIVE:*\n"
    
    # 1. Investigación
    if topic.get("research_done") and inv_url:
        texto += f"• 📄 *Fase 2 (Investigación):* [Abrir en Google Drive]({inv_url}) ✅\n"
    else:
        texto += "• 📄 *Fase 2 (Investigación):* ⏳ _No generada aún_\n"

    # 2. Guion
    if topic.get("script_approved") and script_url:
        texto += f"• ✍️ *Fase 3 y 4 (Guion con SEO):* [Abrir en Google Drive]({script_url}) ✅\n"
    elif topic.get("script_done") and script_url:
        texto += f"• ✍️ *Fase 3 (Guion Borrador):* [Abrir en Google Drive]({script_url}) 🟡 _Pendiente Aprobación_\n"
    else:
        texto += "• ✍️ *Fase 3 (Guion):* ⏳ _No generado aún_\n"

    # 3. Redes
    if topic.get("social_done") and social_url:
        texto += f"• 📱 *Fase 5 (Plan de Redes):* [Abrir en Google Drive]({social_url}) ✅\n"
    else:
        texto += "• 📱 *Fase 5 (Plan de Redes):* ⏳ _No generado aún_\n"

    texto += "\n⚙️ *ACCIONES DISPONIBLES (Las fases ya listas están deshabilitadas):*\n"

    buttons = []

    # REGLA: Si NO tiene investigación -> botón disponible
    if not topic.get("research_done"):
        buttons.append([{"text": f"📝 Iniciar Fase 2: Investigar EP{ep}", "callback_data": f"do_inv_{topic_id}"}])
    else:
        # Ya tiene investigación: Fase 2 deshabilitada
        # Si NO tiene guion -> botón de guion disponible
        if not topic.get("script_done"):
            buttons.append([{"text": f"✍️ Iniciar Fase 3: Redactar Guion EP{ep}", "callback_data": f"do_guion_{topic_id}"}])
        elif not topic.get("script_approved"):
            # Guion generado, pendiente aprobar
            buttons.append([{"text": f"✅ Aprobar Guion y Anexar SEO para YouTube", "callback_data": f"do_aprobar_{topic_id}"}])
        else:
            # Guion ya aprobado con SEO:
            # Si NO tiene redes -> botón de redes disponible
            if not topic.get("social_done"):
                buttons.append([{"text": f"🎬 Iniciar Fase 5: Extraer Clips y Plan de Redes", "callback_data": f"do_redes_{topic_id}"}])
            else:
                # Todo completado
                buttons.append([{"text": "🎉 ¡Episodio 100% Completado!", "callback_data": "noop"}])

    buttons.append([{"text": "🔙 Volver al Menú Principal", "callback_data": "cmd_menu"}])
    return texto, {"inline_keyboard": buttons}

# --- EJECUCIÓN DE FASES ---
def ejecutar_investigacion(topic_id: int):
    state = load_state()
    topics = state.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return

    ep = topic.get("ep_number", "?")
    tema = topic.get("title", "")

    send_telegram(f"🕵️‍♂️ *Agente 1:* Investigando a fondo *EP{ep}: {tema}*...")

    prompt = f"""
    Investiga a fondo el tema: '{tema}' para el episodio EP{ep} del podcast La Cantera.
    Elabora un reporte exhaustivo:
    1. Tesis central y planteamiento del problema en hombres de México y LATAM.
    2. Marco teórico y psicológico (estudios, conceptos clínicos, contrastes).
    3. Costo físico y emocional de la conducta.
    4. Puntos clave y reflexiones para el guionista.
    5. OBLIGATORIO: Sección final titulada 'Bibliografía' con referencias académicas y enlaces.
    """
    system_prompt = "Eres el Agente 1 (Investigador y Estratega) de La Cantera. Rigor académico estricto y bibliografía obligatoria."
    investigacion = call_groq(prompt, system_prompt)

    title = f"Investigación EP{ep}. {tema}"
    drive_res = create_drive_doc(title, investigacion, "La Cantera")
    doc_url = drive_res.get("url", "")

    topic["research_done"] = True
    topic["research_url"] = doc_url
    topic["research_content"] = investigacion
    save_state(state)

    msg = (
        f"🕵️‍♂️ *Investigación del EP{ep} lista y cargada en Google Drive.*\n\n"
        f"📄 [Abrir Documento en Google Drive]({doc_url})\n\n"
        "La Fase 2 ha quedado completada. Ahora puedes avanzar a la redacción del guion."
    )
    # Volver a la vista del tema con las opciones actualizadas
    texto_tema, teclado = build_topic_view(topic_id)
    send_telegram(msg)
    send_telegram(texto_tema, reply_markup=teclado)

def ejecutar_guion(topic_id: int):
    state = load_state()
    topics = state.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return

    ep = topic.get("ep_number", "?")
    tema = topic.get("title", "")
    inv = topic.get("research_content", "")

    send_telegram(f"✍️ *Agente 2:* Redactando guion conversacional para *EP{ep}: {tema}*...")

    prompt = f"""
    Redacta el guion completo para el podcast La Cantera: EP{ep}. {tema}.
    Basado en esta investigación:
    {inv[:3000]}

    Directrices:
    - Locutor individual.
    - Tono: Un compa reflexivo, cercano, que invita al diálogo. Prohibido sonar frío o sermoneador.
    - Estructura: Gancho emocional de apertura, desarrollo con ejemplos cotidianos (trabajo, gimnasio, pareja, soledad), herramientas prácticas y cierre fraternal.
    - Acotaciones de voz: [Pausa], [Tono reflexivo], [Subir intensidad].
    """
    system_prompt = "Eres el Agente 2 (Guionista Principal) de La Cantera. Voz reflexiva, humana, cálida y directa."
    guion = call_groq(prompt, system_prompt)

    doc_title = f"A_R_EP{ep}. {tema}"
    drive_res = create_drive_doc(doc_title, guion, "La Cantera")
    doc_url = drive_res.get("url", "")
    file_id = drive_res.get("fileId", "")

    topic["script_done"] = True
    topic["script_url"] = doc_url
    topic["script_file_id"] = file_id
    topic["script_content"] = guion
    save_state(state)

    msg = (
        f"✍️ *El guion del EP{ep} está listo para tu revisión:*\n\n"
        f"📄 [Abrir Guion Borrador en Google Drive]({doc_url})\n\n"
        "Revisa el guion. Pulsa *'Aprobar Guion'* para renombrarlo, registrarlo en el Sheet y anexar la descripción SEO de YouTube."
    )
    texto_tema, teclado = build_topic_view(topic_id)
    send_telegram(msg)
    send_telegram(texto_tema, reply_markup=teclado)

def ejecutar_aprobacion_y_seo(topic_id: int):
    state = load_state()
    topics = state.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return

    ep = topic.get("ep_number", "?")
    tema = topic.get("title", "")
    file_id = topic.get("script_file_id", "")
    guion = topic.get("script_content", "")

    send_telegram(f"✍️ Renombrando archivo a definitivo y actualizando Google Sheet a 'Aceptado'...")
    if file_id:
        rename_drive_doc(file_id, f"EP{ep}. {tema}")
    update_sheet_status(ep, "Aceptado")

    send_telegram(f"🚀 *Agente 3:* Generando descripción SEO y timestamps para YouTube...")
    prompt = f"""
    Genera la descripción de YouTube para el episodio EP{ep}. {tema} de La Cantera.
    Guion:
    {guion[:2500]}

    Incluye:
    - Gancho y sinopsis rica en palabras clave sobre masculinidad consciente y salud mental.
    - Timestamps (marcas de tiempo).
    - Hashtags estratégicos.
    Formato encabezado con: --- DESCRIPCIÓN PARA YOUTUBE ---
    """
    system_prompt = "Eres el Agente 3 (SEO y Content Manager) de La Cantera."
    seo_desc = call_groq(prompt, system_prompt)

    # Crear versión definitiva consolidada
    final_content = f"{guion}\n\n\n{seo_desc}"
    drive_res = create_drive_doc(f"EP{ep}. {tema}", final_content, "La Cantera")
    final_url = drive_res.get("url", topic.get("script_url", ""))

    topic["script_approved"] = True
    topic["script_url"] = final_url
    topic["script_content"] = final_content
    save_state(state)

    msg = (
        f"🚀 *Guion y SEO de YouTube finalizados para EP{ep}.*\n\n"
        f"📄 [Abrir Guion Definitivo en Drive]({final_url})\n\n"
        "Fases 3 y 4 completadas. Ahora puedes generar los guiones para TikTok, Reels y el carrusel."
    )
    texto_tema, teclado = build_topic_view(topic_id)
    send_telegram(msg)
    send_telegram(texto_tema, reply_markup=teclado)

def ejecutar_redes(topic_id: int):
    state = load_state()
    topics = state.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return

    ep = topic.get("ep_number", "?")
    tema = topic.get("title", "")
    guion = topic.get("script_content", "")

    send_telegram(f"🚀 *Agente 3:* Extrayendo momentos clave y diseñando clips para TikTok e Instagram...")

    prompt = f"""
    Genera el Plan de Redes completo para el episodio EP{ep}. {tema} de La Cantera:
    Basado en este guion:
    {guion[:3000]}

    Incluye:
    1. 3 Guiones de video corto (30-45s) con Gancho (0-3s), Desarrollo conciso y Cierre/CTA.
    2. Copys diferenciados:
       - Versión TikTok (SEO y retención).
       - Versión Instagram (Comunidad y guardados).
    3. Carrusel para Instagram de 4 diapositivas de texto sobre el concepto central.
    4. Estrategia semanal: Mejores días y horarios en LATAM, dinámicas de historias de Instagram.
    """
    system_prompt = "Eres el Agente 3 (Content Manager) de La Cantera."
    plan_redes = call_groq(prompt, system_prompt)

    drive_res = create_drive_doc(f"Redes_EP{ep}", plan_redes, "La Cantera", subfolder="instagram/tiktok")
    doc_url = drive_res.get("url", "")

    topic["social_done"] = True
    topic["social_url"] = doc_url
    topic["completed"] = True  # Cumplió Fases 2, 3 y 5
    save_state(state)

    msg = (
        f"🚀 *Plan de Redes para EP{ep} listo y guardado en Drive.*\n\n"
        f"📱 [Abrir Redes_EP{ep} en Google Drive]({doc_url})\n\n"
        f"🎉 *¡EP{ep} COMPLETADO AL 100%!* (Fases 2, 3 y 5 listas)."
    )
    texto_tema, teclado = build_topic_view(topic_id)
    send_telegram(msg)
    send_telegram(texto_tema, reply_markup=teclado)

def ejecutar_fase_1_nuevo_lote():
    state = load_state()
    topics = state.get("topics", [])
    if not are_all_topics_completed(topics):
        send_telegram("🔒 *Acción bloqueada:* Aún tienes episodios pendientes en el lote actual.")
        return

    send_telegram("🕵️‍♂️ *Agente 1:* Analizando macrotendencias y redes en LATAM para generar 5 nuevos temas...")

    prompt = """
    Realiza un análisis de nicho en masculinidad saludable para México y LATAM.
    Entrega EXACTAMENTE 5 nuevos títulos de episodios potentes, que no sean repetidos.
    Formato estricto (una línea por tema):
    1. [Título del tema 1]
    2. [Título del tema 2]
    3. [Título del tema 3]
    4. [Título del tema 4]
    5. [Título del tema 5]
    """
    system_prompt = "Eres el Agente 1 (Investigador y Estratega) de La Cantera."
    res = call_groq(prompt, system_prompt)

    # Subir reporte a Drive
    create_drive_doc(f"Analisis_Nicho_{int(time.time())}", res, "La Cantera")

    # Parsear temas y sumarlos al lote
    lineas = [l.strip() for l in res.splitlines() if l.strip() and l[0].isdigit() and "." in l]
    next_ep = max([t.get("ep_number", 4) for t in topics] or [4]) + 1
    
    new_topics = []
    tid = 1
    for linea in lineas[:5]:
        partes = linea.split(".", 1)
        titulo = partes[1].strip() if len(partes) > 1 else linea
        new_topics.append({
            "id": tid,
            "ep_number": next_ep,
            "title": titulo,
            "research_done": False,
            "research_url": None,
            "script_done": False,
            "script_approved": False,
            "script_url": None,
            "script_file_id": None,
            "social_done": False,
            "social_url": None,
            "completed": False
        })
        next_ep += 1
        tid += 1

    if new_topics:
        state["topics"] = new_topics
        save_state(state)

    send_telegram("✅ *Nuevo análisis de nicho completado y 5 temas agregados al lote.*")
    texto, teclado = build_main_menu()
    send_telegram(texto, reply_markup=teclado)

# --- LOOP PRINCIPAL DE TELEGRAM ---
def responder_callback(cb_id: str, text: Optional[str] = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = True
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def procesar_callback(data: str, cb_id: str):
    if data == "noop":
        responder_callback(cb_id)
        return
    elif data == "cmd_menu":
        responder_callback(cb_id)
        texto, teclado = build_main_menu()
        send_telegram(texto, reply_markup=teclado)
    elif data == "act_nicho_bloqueado":
        state = load_state()
        topics = state.get("topics", [])
        faltan = sum(1 for t in topics if not t.get("completed", False))
        responder_callback(
            cb_id,
            f"🔒 El Análisis de Nicho está deshabilitado.\n\nDebes completar las Fases 2, 3 y 5 de los {faltan} temas pendientes antes de generar un nuevo lote."
        )
    elif data == "act_nicho":
        responder_callback(cb_id)
        ejecutar_fase_1_nuevo_lote()
    elif data.startswith("ver_tema_"):
        responder_callback(cb_id)
        tid = int(data.split("_")[-1])
        texto, teclado = build_topic_view(tid)
        send_telegram(texto, reply_markup=teclado)
    elif data.startswith("do_inv_"):
        responder_callback(cb_id)
        tid = int(data.split("_")[-1])
        ejecutar_investigacion(tid)
    elif data.startswith("do_guion_"):
        responder_callback(cb_id)
        tid = int(data.split("_")[-1])
        ejecutar_guion(tid)
    elif data.startswith("do_aprobar_"):
        responder_callback(cb_id)
        tid = int(data.split("_")[-1])
        ejecutar_aprobacion_y_seo(tid)
    elif data.startswith("do_redes_"):
        responder_callback(cb_id)
        tid = int(data.split("_")[-1])
        ejecutar_redes(tid)
    elif data == "act_auditoria":
        responder_callback(cb_id)
        send_telegram("📊 *Agente 4:* Ejecutando auditoría mensual...")
        rep = call_groq("Genera una auditoría mensual para La Cantera con CTR, retención y órdenes para el próximo mes.")
        create_drive_doc("Reporte_Auditoria_Mensual", rep, "La Cantera", subfolder="Analiticas_Mensuales")
        send_telegram(f"📊 *Auditoría completada y guardada en Drive:*\n\n{rep[:3000]}")
        texto, teclado = build_main_menu()
        send_telegram(texto, reply_markup=teclado)

def main():
    print("Iniciando Orquestador de Telegram con Reglas Estrictas de Lote...")
    
    # Iniciar servidor de Healthcheck HTTP para Coolify (puerto 8080)
    try:
        t_health = threading.Thread(target=run_health_server, daemon=True)
        t_health.start()
        print("Servidor HTTP de Health Check activo en puerto 8080 para Coolify.")
    except Exception as e:
        print(f"Aviso health server: {e}")

    offset = 0
    texto, teclado = build_main_menu()
    send_telegram(texto, reply_markup=teclado)

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            r = requests.get(url, timeout=25)
            if r.status_code == 200:
                for u in r.json().get("result", []):
                    offset = u["update_id"] + 1
                    if "message" in u and "text" in u["message"]:
                        msg = u["message"]
                        if str(msg["chat"]["id"]) == AUTHORIZED_CHAT_ID:
                            t, k = build_main_menu()
                            send_telegram(t, reply_markup=k)
                    elif "callback_query" in u:
                        cb = u["callback_query"]
                        if str(cb["from"]["id"]) == AUTHORIZED_CHAT_ID:
                            procesar_callback(cb["data"], cb["id"])
            time.sleep(1)
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
