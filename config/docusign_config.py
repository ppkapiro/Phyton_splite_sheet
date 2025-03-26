import os
import logging
from flask import current_app

# Definición del logger
logger = logging.getLogger(__name__)

# Constantes de validación
EXPECTED_REDIRECT_URI = "http://localhost:5000/api/docusign/callback"

def validate_docusign_key(key, testing=False):
    """
    Valida que la integration key de DocuSign sea válida.
    
    Args:
        key (str): Valor de DOCUSIGN_INTEGRATION_KEY
        testing (bool): Si estamos en modo testing
        
    Returns:
        bool: True si es válida, False si no
    """
    if not key:
        return False
        
    if key == "DOCUSIGN_INTEGRATION_KEY" or key == "":
        return False
        
    # En modo testing, aceptamos el valor de prueba
    if testing and key == "test_integration_key":
        return True
        
    # Una integration key válida debe ser un UUID (36 chars con guiones)
    # o tener al menos 20 caracteres para otras configuraciones
    return len(key) >= 20

def validate_redirect_uri(uri, testing=False):
    """
    Valida que el URI de redirección de DocuSign sea válido.
    
    Args:
        uri (str): Valor de DOCUSIGN_REDIRECT_URI
        testing (bool): Si estamos en modo testing
        
    Returns:
        bool: True si es válido, False si no
    """
    if not uri:
        return False
        
    if uri == "DOCUSIGN_REDIRECT_URI" or uri == "":
        return False
    
    # En tests se permite cualquier URI que termine en "/api/docusign/callback"
    if testing:
        return uri.endswith("/api/docusign/callback")
        
    # En producción debe ser exactamente el valor esperado
    return uri == EXPECTED_REDIRECT_URI

def load_docusign_config(app):
    """Carga y valida la configuración de DocuSign en la app Flask."""
    is_testing = app.config.get('TESTING', False)
    
    # 1. Validar DOCUSIGN_INTEGRATION_KEY
    integration_key = os.getenv("DOCUSIGN_INTEGRATION_KEY", app.config.get("DOCUSIGN_INTEGRATION_KEY"))
    if not validate_docusign_key(integration_key, is_testing):
        if is_testing:
            app.logger.warning(
                "DOCUSIGN_INTEGRATION_KEY no configurada correctamente. "
                "Usando valor de prueba para entorno de testing."
            )
            integration_key = "test_integration_key"
        else:
            app.logger.error(
                "ERROR: DOCUSIGN_INTEGRATION_KEY no configurada correctamente. "
                "La integración con DocuSign no funcionará."
            )
    
    # 2. Validar DOCUSIGN_REDIRECT_URI
    redirect_uri = os.getenv("DOCUSIGN_REDIRECT_URI", app.config.get("DOCUSIGN_REDIRECT_URI"))
    if not validate_redirect_uri(redirect_uri, is_testing):
        if is_testing:
            app.logger.warning(
                f"DOCUSIGN_REDIRECT_URI '{redirect_uri}' no configurado correctamente. "
                f"Usando valor de prueba para entorno de testing."
            )
            redirect_uri = EXPECTED_REDIRECT_URI
        else:
            app.logger.error(
                f"ERROR: DOCUSIGN_REDIRECT_URI '{redirect_uri}' no configurado correctamente. "
                f"Debe ser exactamente: {EXPECTED_REDIRECT_URI}. "
                f"La integración con DocuSign no funcionará correctamente."
            )
            # No asignamos valor por defecto en producción para que falle explícitamente
    
    # 3. Establecer valores validados en la configuración
    app.config["DOCUSIGN_INTEGRATION_KEY"] = integration_key
    app.config["DOCUSIGN_REDIRECT_URI"] = redirect_uri
    
    app.logger.info("Configuración DocuSign cargada")
    
    # 4. Realizar verificación final
    if not is_testing:
        if redirect_uri != EXPECTED_REDIRECT_URI:
            app.logger.warning(
                f"⚠️ ADVERTENCIA CRÍTICA: DOCUSIGN_REDIRECT_URI='{redirect_uri}' "
                f"no coincide con el valor esperado '{EXPECTED_REDIRECT_URI}'. "
                f"Esto causará errores de autenticación en DocuSign."
            )
    
    return app.config

def init_app(app):
    """
    Inicializa la configuración de DocuSign en la aplicación Flask.
    
    Args:
        app (Flask): La aplicación Flask
    """
    # Cargar variables de DocuSign desde el entorno
    app.config.update(
        # Valores críticos para la autenticación
        DOCUSIGN_INTEGRATION_KEY=os.getenv('DOCUSIGN_INTEGRATION_KEY'),
        DOCUSIGN_CLIENT_SECRET=os.getenv('CLIENT_SECRET'),  # Leer CLIENT_SECRET desde .env
        DOCUSIGN_ACCOUNT_ID=os.getenv('DOCUSIGN_ACCOUNT_ID'),
        DOCUSIGN_USER_ID=os.getenv('DOCUSIGN_USER_ID'),
        
        # URLs y endpoints
        DOCUSIGN_AUTH_SERVER=os.getenv('DOCUSIGN_AUTH_SERVER', 'account-d.docusign.com'),
        DOCUSIGN_BASE_URL=os.getenv('DOCUSIGN_BASE_URL', 'https://demo.docusign.net/restapi'),
        DOCUSIGN_REDIRECT_URI=os.getenv('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/api/docusign/callback'),
        
        # Configuración adicional
        DOCUSIGN_PRIVATE_KEY_PATH=os.getenv('DOCUSIGN_PRIVATE_KEY_PATH', 'private.key'),
        DOCUSIGN_WEBHOOK_SECRET=os.getenv('DOCUSIGN_WEBHOOK_SECRET'),
        DOCUSIGN_HMAC_KEY=os.getenv('DOCUSIGN_HMAC_KEY'),
        
        # Alcance y duración de tokens
        DOCUSIGN_JWT_SCOPE=os.getenv('DOCUSIGN_JWT_SCOPE', 'signature impersonation'),
        DOCUSIGN_JWT_LIFETIME=int(os.getenv('DOCUSIGN_JWT_LIFETIME', 3600)),
        DOCUSIGN_CACHE_TOKEN=os.getenv('DOCUSIGN_CACHE_TOKEN', 'True').lower() in ('true', '1', 't'),
        DOCUSIGN_CACHE_DURATION=int(os.getenv('DOCUSIGN_CACHE_DURATION', 3600))
    )
    
    # Validar configuración crítica
    validate_docusign_config(app)
    
def validate_docusign_config(app):
    """
    Valida que la configuración de DocuSign esté completa.
    
    Args:
        app (Flask): La aplicación Flask
    """
    # Variables críticas para la integración
    critical_vars = [
        ('DOCUSIGN_INTEGRATION_KEY', 'Integration Key (Client ID)'),
        ('DOCUSIGN_CLIENT_SECRET', 'Client Secret'),
        ('DOCUSIGN_ACCOUNT_ID', 'Account ID'),
        ('DOCUSIGN_REDIRECT_URI', 'Redirect URI')
    ]
    
    missing = []
    insecure = []
    
    for var_name, description in critical_vars:
        if not app.config.get(var_name):
            missing.append(f"{description} ({var_name})")
        elif var_name in ['DOCUSIGN_CLIENT_SECRET'] and app.config[var_name] in ['your_client_secret', 'client_secret_here']:
            insecure.append(f"{description} ({var_name}) contiene un valor placeholder")
    
    if missing:
        logger.warning(f"⚠️ Configuración de DocuSign incompleta. Faltan las siguientes variables: {', '.join(missing)}")
        
    if insecure:
        logger.warning(f"⚠️ Configuración de DocuSign insegura. Las siguientes variables contienen valores placeholder: {', '.join(insecure)}")

    # Log informativo sobre la configuración
    if not missing and not insecure:
        logger.info("✓ Configuración de DocuSign validada correctamente")
        logger.debug(f"  - Integration Key: {app.config.get('DOCUSIGN_INTEGRATION_KEY')[:8]}...")
        logger.debug(f"  - Redirect URI: {app.config.get('DOCUSIGN_REDIRECT_URI')}")

# Configuración por defecto para DocuSign
DOCUSIGN_DEFAULT_CONFIG = {
    'DOCUSIGN_HMAC_KEY': os.environ.get('DOCUSIGN_HMAC_KEY', 'default_test_hmac_key_12345'),
}
