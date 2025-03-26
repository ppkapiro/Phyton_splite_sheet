# Configuración de DocuSign

## Variables de Entorno Requeridas

| Parámetro | Descripción | Estado |
|-----------|--------------|---------|
| DOCUSIGN_ACCOUNT_ID | ID de cuenta DocuSign | ✅ Configurado |
| DOCUSIGN_INTEGRATION_KEY | Clave de integración | ✅ Configurado |
| DOCUSIGN_CLIENT_SECRET | Secret de cliente OAuth | ✅ Configurado |
| DOCUSIGN_USER_ID | ID de usuario impersonado | ✅ Configurado |
| DOCUSIGN_PRIVATE_KEY_PATH | Ruta a la clave privada RSA | ✅ Configurado |
| DOCUSIGN_HMAC_KEY | Clave HMAC para validación | ✅ Configurado |
| DOCUSIGN_AUTH_SERVER | Servidor de autenticación | ✅ Configurado |
| DOCUSIGN_BASE_URL | URL base de la API | ✅ Configurado |
| DOCUSIGN_WEBHOOK_SECRET | Secret para webhooks | ✅ Configurado |
| DOCUSIGN_REDIRECT_URI | URI de redirección OAuth | ✅ Configurado |

## Proceso de Configuración

### 1. Crear cuenta en DocuSign

1. Registrarse en [DocuSign Developer](https://developers.docusign.com/)
2. Crear una aplicación de integración
3. Configurar los permisos (scopes) necesarios:
   - `signature`
   - `impersonation`
   - `openid` (opcional)

### 2. Generar Par de Claves RSA

```bash
# Generar clave privada
openssl genrsa -out private.key 2048

# Generar clave pública
openssl rsa -in private.key -pubout -out public.key
```

### 3. Configurar OAuth en DocuSign

1. En el dashboard de DocuSign, ir a "Apps and Keys"
2. Subir la clave pública generada
3. Anotar Integration Key y otros IDs necesarios
4. Configurar URI de redirección: `http://localhost:5000/api/docusign/callback`

### 4. Configurar Webhooks

1. Crear listener en `https://{su-dominio}/api/docusign/webhook`
2. Configurar autenticación HMAC
3. Seleccionar eventos a recibir:
   - `envelope-sent`
   - `envelope-delivered`
   - `envelope-completed`
   - `envelope-declined`
   - `recipient-completed`

### 5. Verificación

Para verificar la configuración correcta:

```bash
# Verificar configuración general
python scripts/verify_docusign_connection.py

# Test específicos de DocuSign
pytest tests/unit/test_docusign_endpoints.py
pytest tests/unit/test_docusign_pkce.py
pytest tests/integration/test_docusign_flow.py
```

## Flujo de Autorización OAuth 2.0 con PKCE

### 1. Inicio del Flujo

El flujo comienza cuando un usuario accede a `/api/docusign/auth`. La aplicación:

1. Genera un `code_verifier` aleatorio (mínimo 43 caracteres)
2. Calcula el `code_challenge` usando SHA-256
3. Almacena el `code_verifier` en la sesión del usuario
4. Redirige al usuario a DocuSign con el `code_challenge`

### 2. Autorización en DocuSign

El usuario completa la autorización en DocuSign, que luego redirige de vuelta a nuestro callback con un código de autorización.

### 3. Intercambio de Código por Token

En `/api/docusign/callback`:

1. Se recupera el `code_verifier` de la sesión
2. Se envía el código de autorización y el `code_verifier` a DocuSign
3. DocuSign verifica el `code_verifier` y devuelve tokens de acceso y refresh
4. Los tokens se almacenan en la sesión o base de datos

## Tests de Integración

Los siguientes tests deben pasar tras la configuración:

- ✅ Test de autorización OAuth
- ✅ Test de validación PKCE
- ✅ Test de callbacks
- ✅ Test de validación de state
- ✅ Test de intercambio de tokens
- ✅ Test de flujo completo OAuth
- ⚠️ Test de webhooks (requiere ambiente real)

## Referencias

- [Documentación oficial DocuSign](https://developers.docusign.com/docs/)
- [Guía de implementación JWT](https://developers.docusign.com/platform/auth/jwt/jwt-get-token/)
- [Guía de Webhooks](https://developers.docusign.com/platform/webhooks/)
- [OAuth 2.0 con PKCE](https://oauth.net/2/pkce/)
