# Webhooks de DocuSign

## Introducción

Los webhooks permiten a DocuSign enviar notificaciones en tiempo real sobre eventos relacionados con sobres (envelopes) y firmantes. Esta guía explica cómo configurar, validar y procesar webhooks de DocuSign en Split Sheet API.

## Configuración de Webhook en DocuSign

### Paso 1: Acceder a Configuración de Webhooks

1. Inicie sesión en su [cuenta de DocuSign](https://account.docusign.com/)
2. Vaya a **Settings** > **Connect** > **Add Configuration**
3. Seleccione **Custom**

### Paso 2: Configurar Endpoint

1. Nombre de configuración: `Split Sheet API Webhook`
2. URL: `https://your-domain.com/api/docusign/webhook`
3. Autenticación: Seleccione **HMAC Signature Authentication**
4. Secret: Genere un valor aleatorio y seguro (mínimo 32 caracteres)
   ```bash
   python -c "import os; import base64; print(base64.b64encode(os.urandom(32)).decode())"
   ```
5. Guarde el mismo secret en la variable de entorno `DOCUSIGN_HMAC_KEY`

### Paso 3: Seleccionar Eventos

Seleccione los eventos que desea recibir:

- **Envelope Events**:
  - `Envelope Sent`
  - `Envelope Delivered`
  - `Envelope Completed`
  - `Envelope Declined`
  - `Envelope Voided`

- **Recipient Events**:
  - `Recipient Completed`
  - `Recipient Declined`

### Paso 4: Configuración Adicional

1. **Envelope Data**: Seleccione los datos a incluir en las notificaciones
   - Envelope: `envelopeId`, `status`, `emailSubject`, `sentDateTime`, `completedDateTime`
   - Recipients: `recipientId`, `name`, `email`, `status`, `completedDateTime`
   - Custom Fields: `all` (si usa campos personalizados)

2. **Retry on Failure**: Active esta opción para que DocuSign reintente en caso de error

3. **Logging**: Active esta opción para diagnóstico durante el desarrollo

## Endpoint de Webhook en la API

El endpoint `/api/docusign/webhook` está configurado para recibir y procesar las notificaciones:

```python
@docusign_bp.route('/webhook', methods=['POST'])
def docusign_webhook():
    # Validar firma HMAC
    validator = DocuSignHMACValidator(current_app.config['DOCUSIGN_HMAC_KEY'])
    is_valid = validator.validate_request(request)
    
    if not is_valid:
        current_app.logger.warning("Webhook con firma inválida recibido")
        return jsonify({"error": "Firma inválida"}), 401
    
    # Procesar eventos
    data = request.get_json()
    envelope_id = data.get('envelopeId')
    status = data.get('status')
    
    current_app.logger.info(f"Webhook DocuSign: envelope={envelope_id}, status={status}")
    
    # Actualizar estado del documento
    document = get_document_by_envelope(envelope_id)
    if document:
        document.status = status
        document.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Opcionalmente: notificar al usuario del cambio
        notify_user(document.user_id, {
            'document_id': document.id,
            'status': status
        })
    else:
        current_app.logger.warning(f"Webhook para envelope desconocido: {envelope_id}")
    
    # Siempre responder con éxito, incluso si no se encontró el documento
    return jsonify({"status": "success"})
```

## Validación de Firma HMAC

La seguridad de los webhooks se garantiza mediante firma HMAC:

```python
class DocuSignHMACValidator:
    """Validador de firmas HMAC para webhooks de DocuSign."""
    
    def __init__(self, hmac_key):
        self.hmac_key = hmac_key
    
    def validate_request(self, request):
        """Valida la firma HMAC de una solicitud webhook de DocuSign."""
        # Extraer firma de headers
        signature = request.headers.get('X-DocuSign-Signature-1')
        if not signature:
            return False
        
        # Obtener cuerpo de la solicitud
        body = request.get_data()
        
        # Calcular HMAC-SHA256
        expected_hmac = hmac.new(
            self.hmac_key.encode(),
            body,
            hashlib.sha256
        ).digest()
        
        # Comparación segura para prevenir timing attacks
        try:
            received_hmac = base64.b64decode(signature)
            return hmac.compare_digest(expected_hmac, received_hmac)
        except Exception:
            return False
```

## Estructura de Datos en Webhooks

### Envelope Completed

```json
{
  "event": "envelope-completed",
  "envelopeId": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "emailSubject": "Split Sheet para Proyecto X",
  "sentDateTime": "2025-03-14T15:30:45.000Z",
  "completedDateTime": "2025-03-15T10:22:01.000Z",
  "recipients": [
    {
      "recipientId": "1",
      "name": "John Doe",
      "email": "john@example.com",
      "status": "completed",
      "completedDateTime": "2025-03-15T10:22:01.000Z"
    }
  ],
  "customFields": {
    "textCustomFields": [
      {
        "name": "projectId",
        "value": "proj-123"
      }
    ]
  }
}
```

### Recipient Declined

```json
{
  "event": "recipient-declined",
  "envelopeId": "123e4567-e89b-12d3-a456-426614174000",
  "status": "declined",
  "emailSubject": "Split Sheet para Proyecto X",
  "sentDateTime": "2025-03-14T15:30:45.000Z",
  "recipients": [
    {
      "recipientId": "1",
      "name": "John Doe",
      "email": "john@example.com",
      "status": "declined",
      "declinedDateTime": "2025-03-15T09:45:30.000Z",
      "declinedReason": "No estoy de acuerdo con los términos"
    }
  ]
}
```

## Flujo de Procesamiento

1. DocuSign envía una notificación cuando ocurre un evento
2. El endpoint `/api/docusign/webhook` recibe la notificación
3. Se valida la firma HMAC para garantizar autenticidad
4. Se procesa el evento según su tipo:
   - `envelope-completed`: Se actualiza el documento como completado
   - `envelope-declined`: Se marca como rechazado
   - Otros eventos: Se actualizan los estados correspondientes
5. Se notifica al usuario del cambio de estado (opcional)

## Pruebas y Verificación

### Test Local con Webhook Simulado

Para probar localmente sin tener que exponer un endpoint público:

```python
# Simular un webhook de DocuSign
def simulate_docusign_webhook(envelope_id, status, hmac_key):
    """Simula una notificación webhook de DocuSign."""
    # Crear payload
    payload = {
        "event": f"envelope-{status}",
        "envelopeId": envelope_id,
        "status": status,
        "emailSubject": "Test Split Sheet",
        "sentDateTime": datetime.utcnow().isoformat(),
        "completedDateTime": datetime.utcnow().isoformat()
    }
    
    # Convertir a JSON
    payload_json = json.dumps(payload)
    
    # Calcular firma HMAC
    signature = hmac.new(
        hmac_key.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature).decode()
    
    # Crear headers
    headers = {
        'Content-Type': 'application/json',
        'X-DocuSign-Signature-1': signature_b64
    }
    
    # Enviar solicitud
    response = requests.post(
        'http://localhost:5000/api/docusign/webhook',
        headers=headers,
        data=payload_json
    )
    
    return response
```

### Verificar Configuración con `test_webhook.py`

Puede ejecutar el script `scripts/test_docusign_webhook.py` para probar el manejo de webhooks:

```bash
python scripts/test_docusign_webhook.py
```

## Solución de Problemas

### Webhook No Recibido

1. Verifique que la URL configurada en DocuSign sea accesible públicamente
2. Compruebe que la URL coincide exactamente con el endpoint de la API
3. Revise los logs de DocuSign para ver si hay intentos de envío fallidos
4. Asegúrese de que su servidor permite solicitudes POST a la ruta configurada

### Error de Validación HMAC

1. Verifique que `DOCUSIGN_HMAC_KEY` coincide con el secreto configurado en DocuSign
2. Compruebe que el body de la solicitud no se modifica antes de la validación
3. Verifique que está utilizando el header correcto (`X-DocuSign-Signature-1`)

### Error en Procesamiento

1. Revise los logs del servidor para identificar errores específicos
2. Verifique que el `envelopeId` existe en la base de datos
3. Compruebe que el formato del webhook coincide con lo esperado

## Referencias

- [Documentación oficial de webhooks DocuSign](https://developers.docusign.com/platform/webhooks/)
- [Guía de autenticación HMAC](https://developers.docusign.com/platform/webhooks/connect/hmac/)
- [Lista de eventos de DocuSign Connect](https://developers.docusign.com/platform/webhooks/connect/events/)
