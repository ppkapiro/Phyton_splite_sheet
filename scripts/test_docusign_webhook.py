#!/usr/bin/env python
"""
Script para probar el manejo de webhooks de DocuSign.
Simula distintos tipos de notificaciones para verificar el procesamiento.
"""
import os
import sys
import json
import requests
import base64
import hmac
import hashlib
import uuid
from datetime import datetime
import dotenv
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Cargar variables de entorno
dotenv.load_dotenv()

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.WARNING}! {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def get_webhook_url():
    """Obtiene la URL del webhook a probar."""
    # Por defecto, intentar localhost
    default_url = "http://localhost:5000/api/docusign/webhook"
    
    # Si hay una variable de entorno, usarla
    api_url = os.environ.get('API_BASE_URL')
    if api_url:
        if api_url.endswith('/'):
            api_url = api_url[:-1]
        return f"{api_url}/api/docusign/webhook"
    
    return default_url

def get_hmac_key():
    """Obtiene la clave HMAC para firmar las solicitudes webhook."""
    hmac_key = os.environ.get('DOCUSIGN_HMAC_KEY')
    if not hmac_key:
        print_warning("DOCUSIGN_HMAC_KEY no está configurada")
        print_info("Usando clave de prueba '12345'")
        return "12345"
    return hmac_key

def create_test_envelope():
    """Crea un ID de sobre (envelope) de prueba."""
    return str(uuid.uuid4())

def sign_payload(payload, hmac_key):
    """Firma el payload con HMAC-SHA256."""
    payload_json = json.dumps(payload)
    signature = hmac.new(
        hmac_key.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

def simulate_webhook(payload, hmac_key, webhook_url):
    """Envía una notificación webhook simulada al endpoint."""
    # Convertir payload a JSON
    payload_json = json.dumps(payload)
    
    # Firmar payload
    signature = sign_payload(payload, hmac_key)
    
    # Preparar headers
    headers = {
        'Content-Type': 'application/json',
        'X-DocuSign-Signature-1': signature
    }
    
    print_info(f"Enviando webhook a {webhook_url}")
    print_info(f"Payload: {payload_json[:100]}...")
    
    try:
        # Enviar solicitud
        response = requests.post(
            webhook_url,
            headers=headers,
            data=payload_json,
            timeout=10
        )
        
        # Verificar respuesta
        if response.status_code == 200:
            print_success(f"Webhook aceptado: HTTP {response.status_code}")
            try:
                print_info(f"Respuesta: {response.json()}")
            except:
                print_info(f"Respuesta: {response.text[:100]}")
            return True
        else:
            print_error(f"Error en webhook: HTTP {response.status_code}")
            print_info(f"Respuesta: {response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error enviando webhook: {str(e)}")
        return False

def create_envelope_completed_payload(envelope_id):
    """Crea un payload para un evento envelope-completed."""
    current_time = datetime.utcnow().isoformat()
    return {
        "event": "envelope-completed",
        "envelopeId": envelope_id,
        "status": "completed",
        "emailSubject": "Test Split Sheet",
        "sentDateTime": current_time,
        "completedDateTime": current_time,
        "recipients": [
            {
                "recipientId": "1",
                "name": "Test User",
                "email": "test@example.com",
                "status": "completed",
                "completedDateTime": current_time
            }
        ],
        "customFields": {
            "textCustomFields": [
                {
                    "name": "projectId",
                    "value": "test-123"
                }
            ]
        }
    }

def create_recipient_declined_payload(envelope_id):
    """Crea un payload para un evento recipient-declined."""
    current_time = datetime.utcnow().isoformat()
    return {
        "event": "recipient-declined",
        "envelopeId": envelope_id,
        "status": "declined",
        "emailSubject": "Test Split Sheet",
        "sentDateTime": current_time,
        "recipients": [
            {
                "recipientId": "1",
                "name": "Test User",
                "email": "test@example.com",
                "status": "declined",
                "declinedDateTime": current_time,
                "declinedReason": "Prueba de rechazo"
            }
        ]
    }

def create_envelope_sent_payload(envelope_id):
    """Crea un payload para un evento envelope-sent."""
    current_time = datetime.utcnow().isoformat()
    return {
        "event": "envelope-sent",
        "envelopeId": envelope_id,
        "status": "sent",
        "emailSubject": "Test Split Sheet",
        "sentDateTime": current_time,
        "recipients": [
            {
                "recipientId": "1",
                "name": "Test User",
                "email": "test@example.com",
                "status": "sent"
            }
        ]
    }

def test_invalid_signature():
    """Prueba con una firma HMAC inválida."""
    print_header("Prueba con Firma Inválida")
    
    # Configurar prueba
    webhook_url = get_webhook_url()
    hmac_key = get_hmac_key()
    envelope_id = create_test_envelope()
    
    # Crear payload
    payload = create_envelope_completed_payload(envelope_id)
    
    # Firmar con clave diferente
    invalid_key = "invalid_key_123"
    signature = sign_payload(payload, invalid_key)
    
    # Preparar headers
    headers = {
        'Content-Type': 'application/json',
        'X-DocuSign-Signature-1': signature
    }
    
    # Enviar solicitud
    try:
        response = requests.post(
            webhook_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        
        # Verificar respuesta
        if response.status_code == 401:
            print_success("Verificación exitosa: Firma inválida rechazada con HTTP 401")
            return True
        else:
            print_error(f"La firma inválida debería ser rechazada con 401, pero recibió {response.status_code}")
            print_info(f"Respuesta: {response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error enviando webhook: {str(e)}")
        return False

def run_all_tests():
    """Ejecuta todas las pruebas de webhook."""
    print_header("PRUEBA DE WEBHOOKS DOCUSIGN")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configurar pruebas
    webhook_url = get_webhook_url()
    hmac_key = get_hmac_key()
    envelope_id = create_test_envelope()
    
    print_info(f"Usando URL: {webhook_url}")
    print_info(f"Envelope ID: {envelope_id}")
    print_info(f"HMAC Key: {'*' * len(hmac_key)}")
    
    # Probar webhooks
    results = {}
    
    print_header("1. Prueba de Envelope Completed")
    payload = create_envelope_completed_payload(envelope_id)
    results['envelope_completed'] = simulate_webhook(payload, hmac_key, webhook_url)
    
    print_header("2. Prueba de Recipient Declined")
    payload = create_recipient_declined_payload(envelope_id)
    results['recipient_declined'] = simulate_webhook(payload, hmac_key, webhook_url)
    
    print_header("3. Prueba de Envelope Sent")
    payload = create_envelope_sent_payload(envelope_id)
    results['envelope_sent'] = simulate_webhook(payload, hmac_key, webhook_url)
    
    print_header("4. Prueba de Firma Inválida")
    results['invalid_signature'] = test_invalid_signature()
    
    # Mostrar resumen
    print_header("RESUMEN DE PRUEBAS")
    
    all_passed = True
    for test, result in results.items():
        if result:
            print_success(f"{test}: Pasó")
        else:
            print_error(f"{test}: Falló")
            all_passed = False
    
    if all_passed:
        print_header("✅ TODAS LAS PRUEBAS EXITOSAS")
        print("El manejo de webhooks está funcionando correctamente.")
    else:
        print_header("⚠️ ALGUNAS PRUEBAS FALLARON")
        print("Revise los errores antes de usar webhooks en producción.")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()
