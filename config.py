import os

class Config:
    # Configuración de la aplicación
    DEBUG = os.getenv('FLASK_DEBUG', True)
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))

    # DocuSign Configuration
    DOCUSIGN_ACCOUNT_ID = os.getenv('DOCUSIGN_ACCOUNT_ID')
    DOCUSIGN_INTEGRATION_KEY = os.getenv('DOCUSIGN_INTEGRATION_KEY')
    DOCUSIGN_CLIENT_SECRET = os.getenv('DOCUSIGN_CLIENT_SECRET')
    DOCUSIGN_USER_ID = os.getenv('DOCUSIGN_USER_ID')
    DOCUSIGN_RSA_KEY = os.getenv('DOCUSIGN_PRIVATE_KEY_PATH')
    DOCUSIGN_AUTH_SERVER = os.getenv('DOCUSIGN_AUTH_SERVER', 'account-d.docusign.com')
    DOCUSIGN_BASE_URL = os.getenv('DOCUSIGN_BASE_URL')
    # Asegurar que el redirect_uri sea consistente
    DOCUSIGN_REDIRECT_URI = os.getenv('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/api/callback')
    DOCUSIGN_CONSENT_URL = f"https://{DOCUSIGN_AUTH_SERVER}/oauth/auth"
    DOCUSIGN_TOKEN_URL = f"https://{DOCUSIGN_AUTH_SERVER}/oauth/token"

    # DocuSign Webhook Configuration
    DOCUSIGN_HMAC_KEY = os.getenv('DOCUSIGN_HMAC_KEY')
    DOCUSIGN_WEBHOOK_EVENTS = [
        'envelope-sent',
        'envelope-delivered',
        'envelope-completed',
        'envelope-declined',
        'recipient-completed'
    ]