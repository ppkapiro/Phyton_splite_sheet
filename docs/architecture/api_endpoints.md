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
    "email": "string (email válido)"
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

### POST /api/pdf/generate_pdf
Genera un documento PDF Split Sheet.

**Estado**: ✅ Implementado

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
    ],
    "metadata": {
        "date": "string (fecha en formato YYYY-MM-DD)",
        "project": "string (nombre del proyecto)"
    }
}
```

**Respuestas**:
- 200: PDF generado exitosamente
- 400: Datos inválidos
- 401: No autorizado
- 500: Error en generación

### POST /api/docusign/send_for_signature
Envía un documento PDF para firma mediante DocuSign.

**Estado**: ✅ Implementado

**Headers**:
- Authorization: Bearer {token}

**Parámetros**:
```json
{
    "recipient_email": "string (email del destinatario)",
    "recipient_name": "string (nombre del destinatario)"
}
```

**Respuestas**:
- 200: Documento enviado para firma
- 400: Datos incorrectos
- 401: No autorizado
- 500: Error en el servidor

### GET /api/docusign/auth
Inicia el flujo de autorización de DocuSign con OAuth 2.0 y PKCE.

**Estado**: ✅ Implementado

**Descripción**: 
Este endpoint redirige al usuario a la página de autorización de DocuSign. Implementa el flujo OAuth 2.0 con PKCE (Proof Key for Code Exchange) para mayor seguridad.

**Respuestas**:
- 302: Redirección a DocuSign
- 500: Error de configuración o del servidor

### GET /api/docusign/callback
Recibe la respuesta de autorización de DocuSign.

**Estado**: ✅ Implementado

**Parámetros de Query**:
- code: Código de autorización de DocuSign
- state: Valor para verificación CSRF

**Respuestas**:
- 200: Autorización exitosa (token obtenido)
- 302: Redirección a dashboard después de la autorización
- 400: Parámetros inválidos
- 500: Error en el intercambio de código por token

### GET /api/docusign/status
Verifica el estado de autorización con DocuSign.

**Estado**: ✅ Implementado

**Respuestas**:
- 200: Estado de autenticación (JSON)

### POST /api/webhook
Recibe notificaciones de DocuSign sobre cambios de estado.

**Estado**: ⚠️ Parcialmente implementado

**Headers**:
- X-DocuSign-Signature-1: {signature}

**Respuestas**:
- 200: Notificación procesada
- 401: Firma inválida
- 500: Error procesando la notificación

## Estado

### GET /api/status
Verifica el estado de la API.

**Estado**: ✅ Implementado

**Respuestas**:
- 200: Estado de la API (JSON)
