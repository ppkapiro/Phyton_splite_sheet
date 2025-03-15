from datetime import timedelta
from flask import jsonify, abort
import os

class Config:
    # ...existing code...
    
    # Configuración JWT para respuestas consistentes
    JWT_ERROR_MESSAGE_KEY = 'error'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Callbacks para errores de autenticación
    JWT_INVALID_TOKEN_CALLBACK = lambda x: abort(401, description="Token inválido")
    JWT_MISSING_TOKEN_CALLBACK = lambda x: abort(401, description="Token requerido")
    JWT_EXPIRED_TOKEN_CALLBACK = lambda x: abort(401, description="Token expirado")

    # Configuración DocuSign
    DOCUSIGN_INTEGRATION_KEY = os.environ.get('DOCUSIGN_INTEGRATION_KEY')
    DOCUSIGN_AUTH_SERVER = os.environ.get('DOCUSIGN_AUTH_SERVER', 'account-d.docusign.com')
    DOCUSIGN_BASE_URL = os.environ.get('DOCUSIGN_BASE_URL', 'https://demo.docusign.net/restapi')
    DOCUSIGN_REDIRECT_URI = os.environ.get('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/api/docusign/callback')
    DOCUSIGN_SCOPES = os.environ.get('DOCUSIGN_SCOPES', 'signature impersonation openid')
    
    # Solo configurar si es cliente confidencial
    DOCUSIGN_CLIENT_SECRET = os.environ.get('DOCUSIGN_CLIENT_SECRET')
    
    # Lista de eventos de webhook aceptados
    DOCUSIGN_WEBHOOK_EVENTS = [
        'envelope-sent', 'envelope-delivered', 'envelope-completed', 
        'envelope-declined', 'envelope-voided'
    ]

    # ...existing code...