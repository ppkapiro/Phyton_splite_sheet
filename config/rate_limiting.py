from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Configuración de limiter con valores por defecto seguros
limiter = Limiter(
    key_func=get_remote_address,  # Identifica clientes por IP
    default_limits=["200 per day", "50 per hour"],  # Límites globales por defecto
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URL", "memory://"),  # Almacenamiento en memoria por defecto
    headers_enabled=True,  # Activar headers X-RateLimit
    strategy="fixed-window"  # Estrategia de ventana fija
)

# Límites específicos para diferentes tipos de endpoints
AUTHENTICATION_LIMIT = ["5 per minute", "20 per hour"]  # Más restrictivo para autenticación
API_GENERAL_LIMIT = ["30 per minute", "300 per hour"]  # Límite general para API
PDF_GENERATION_LIMIT = ["10 per minute", "100 per hour"]  # Limitado para generación de PDF
DOCUSIGN_LIMIT = ["20 per minute"]  # Límite para interacciones con DocuSign

# Función para obtener límites por ruta
def get_limit_for_route(route):
    """
    Determina los límites de tasa apropiados según la ruta del endpoint.
    
    Args:
        route (str): Ruta del endpoint
        
    Returns:
        list: Lista de límites aplicables a esta ruta
    """
    if '/api/login' in route or '/api/register' in route:
        return AUTHENTICATION_LIMIT
    elif '/api/pdf' in route:
        return PDF_GENERATION_LIMIT
    elif '/api/docusign' in route:
        return DOCUSIGN_LIMIT
    else:
        return API_GENERAL_LIMIT

# Función para excluir IPs internas o de administradores
def is_exempt_from_limits():
    """Determina si la solicitud actual debe estar exenta de límites de tasa."""
    # Implementación básica: eximir solicitudes de localhost/desarrollo
    request_ip = get_remote_address()
    exempt_ips = {'127.0.0.1', 'localhost', '::1'}
    
    # También verificar variable de entorno para IPs adicionales exentas
    if os.environ.get('RATELIMIT_EXEMPT_IPS'):
        exempt_ips.update(os.environ.get('RATELIMIT_EXEMPT_IPS').split(','))
    
    return request_ip in exempt_ips

# Obtener el nombre de usuario para límites por usuario
def get_current_username():
    """
    Obtiene el nombre de usuario para rate limiting basado en usuario.
    Si no está autenticado, retorna la IP.
    """
    from flask import request
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    
    try:
        # Verificar si hay token JWT
        verify_jwt_in_request(optional=True)
        # Obtener identidad si está autenticado
        identity = get_jwt_identity()
        if identity:
            return str(identity)
    except:
        pass
    
    # Si no está autenticado o hay error, usar IP
    return get_remote_address()
