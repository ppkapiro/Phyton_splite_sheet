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

## Proceso de Configuración

### 1. Crear cuenta en DocuSign

1. Registrarse en [DocuSign Developer](https://developers.docusign.com/)
2. Crear una aplicación de integración
3. Configurar los permisos (scopes) necesarios:
   - `signature`
   - `impersonation`

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
4. Configurar URI de redirección: `http://localhost:5000/api/callback`

### 4. Configurar Webhooks

1. Crear listener en `https://{su-dominio}/api/docusign/webhook`
2. Configurar autenticación HMAC
3. Seleccionar eventos a recibir:
   - `envelope-sent`
   - `envelope-delivered`
   - `envelope-completed`
   - `envelope-declined`

### 5. Verificación

Para verificar la configuración correcta:

```bash
# Verificar configuración general
python scripts/verificar_entorno.py

# Test específicos de DocuSign
pytest tests/test_docusign.py
```

## Tests de Integración

Los siguientes tests deben pasar tras la configuración:

- ✅ Test de autenticación OAuth
- ✅ Test de validación HMAC
- ✅ Test de callbacks
- ✅ Test de estados de documento

## Referencias

- [Documentación oficial DocuSign](https://developers.docusign.com/docs/)
- [Guía de implementación JWT](https://developers.docusign.com/platform/auth/jwt/jwt-get-token/)
- [Guía de Webhooks](https://developers.docusign.com/platform/webhooks/)
