class Config:
    """
    Archivo de ejemplo para la configuración.
    Copiar como config.py y actualizar con valores reales.
    """
    # Flask Configuration
    DEBUG = True  # True para desarrollo, False para producción
    CORS_HEADERS = 'Content-Type'
    SECRET_KEY = 'CAMBIAR_POR_CLAVE_SEGURA'  # Generar una clave segura aleatoria
    
    # DocuSign Configuration - Reemplazar con tus credenciales
    DOCUSIGN_ACCOUNT_ID = ''      # Ejemplo: 7299e9a9-8a24-43d8-bd9e-10c84be0846
    DOCUSIGN_CLIENT_ID = ''       # Ejemplo: 8b8bc56f-808c-47f0-918e-10c84be0846
    DOCUSIGN_CLIENT_SECRET = ''   # Ejemplo: 21da586d-64da-4821-939a-770147c19e28
    DOCUSIGN_AUTH_SERVER = 'account-d.docusign.com'  # Usar account.docusign.com para producción
    DOCUSIGN_REDIRECT_URI = 'http://localhost:5000/callback'
    DOCUSIGN_PRIVATE_KEY_PATH = 'private.key'
