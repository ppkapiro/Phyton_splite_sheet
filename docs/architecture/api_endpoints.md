# Documentación de Endpoints API

## Visión General
La API Split Sheet proporciona endpoints para gestionar usuarios, generar documentos PDF y gestionar el proceso de firma a través de DocuSign.

## Autenticación

### POST /api/register
Registro de nuevos usuarios.

**Estado**: ✅ Completo

**Parámetros**:
```json
{
    "username": "string (3-30 caracteres)",
    "password": "string (6-128 caracteres)",
    "email": "string (email válido)",
    "full_name": "string (2-100 caracteres)"
}
```

**Respuestas**:
- 201: Usuario creado exitosamente
- 400: Datos inválidos
- 409: Usuario ya existe

### POST /api/login
Inicio de sesión.

**Estado**: ✅ Completo

**Parámetros**:
```json
{
    "username": "string",
    "password": "string"
}
```

**Respuestas**:
- 200: Login exitoso + token JWT
- 401: Credenciales inválidas

### POST /api/logout
Cierre de sesión (invalidación de token).

**Estado**: ✅ Completo

**Headers**:
- Authorization: Bearer {token}

**Respuestas**:
- 200: Logout exitoso
- 401: No autorizado

## Documentos

### POST /api/generate_pdf
Genera un documento PDF Split Sheet.

**Estado**: ⚠️ Parcialmente implementado

**Headers**:
- Authorization: Bearer {token}

**Parámetros**:
```json
{
    "title": "string (título del proyecto)",
    "participants": [
        {
            "name": "string (nombre del participante)",
            "role": "string (rol: Compositor, Productor, etc)",
            "share": "number (porcentaje)"
        }
    ]
}
```

**Respuestas**:
- 200: PDF generado exitosamente
- 400: Datos inválidos
- 500: Error en generación

### POST /api/send_for_signature
Envía un documento PDF para firma mediante DocuSign.

**Estado**: △ Parcialmente implementado

**Headers**:
- Authorization: Bearer {token}

**Parámetros**:
```json
{
    "document_id": "string",
    "recipient_email": "string",
    "recipient_name": "string"
}
```

**Respuestas**:
- 200: Documento enviado para firma
- 400: Datos incorrectos
- 503: Servicio DocuSign no disponible

### GET /api/signature_status/{envelope_id}
Consulta el estado de un documento enviado para firma.

**Estado**: △ Parcialmente implementado

**Headers**:
- Authorization: Bearer {token}

**Respuestas**:
- 200: Estado del documento
- 404: Documento no encontrado

### POST /api/webhook
Recibe notificaciones de DocuSign sobre cambios de estado.

**Estado**: △ Parcialmente implementado

**Headers**:
- X-DocuSign-Signature-1: {signature}

**Respuestas**:
- 200: Notificación procesada
- 401: Firma inválida
