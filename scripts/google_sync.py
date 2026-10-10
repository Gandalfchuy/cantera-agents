import requests
import json
import os
from typing import Optional, Dict, Any

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "")

def create_google_doc(title: str, content: str, folder_name: str = "La Cantera", subfolder: Optional[str] = None) -> Dict[str, Any]:
    """Crea un documento de Google Docs en la carpeta especificada de Google Drive."""
    payload = {
        "action": "create_doc",
        "title": title,
        "content": content,
        "folder_name": folder_name,
        "subfolder": subfolder
    }
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error creando documento en Drive: {e}")
        return {"status": "error", "message": str(e)}

def rename_google_doc(file_id: str, new_title: str) -> Dict[str, Any]:
    """Renombra un archivo en Google Drive."""
    payload = {
        "action": "rename_doc",
        "file_id": file_id,
        "new_title": new_title
    }
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
        return response.json()
    except Exception as e:
        print(f"Error renombrando documento en Drive: {e}")
        return {"status": "error", "message": str(e)}

def update_sheet(ep_number: int, status: str = "Aceptado") -> Dict[str, Any]:
    """Actualiza la columna de estado en el Google Sheet central."""
    payload = {
        "action": "update_sheet_status",
        "ep_number": ep_number,
        "status": status
    }
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
        return response.json()
    except Exception as e:
        print(f"Error actualizando Google Sheet: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test rápido de conectividad
    res = create_google_doc("Test Connectivity", "Prueba de módulo google_sync")
    print(res)
