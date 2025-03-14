from datetime import timedelta
from flask import jsonify, abort

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

    # ...existing code...