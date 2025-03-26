"""
Configuración de seguridad para la aplicación Flask.
Incluye middlewares y funciones auxiliares para mejorar la seguridad.
"""
from flask import Flask, request, g, current_app
import bleach
from functools import wraps

def configure_security_headers(app):
    """Configura encabezados de seguridad HTTP para la aplicación Flask."""
    @app.after_request
    def set_security_headers(response):
        """Añade encabezados de seguridad a todas las respuestas."""
        # Previene que los navegadores interpreten archivos de manera incorrecta
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Protección contra clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Habilita la protección XSS en navegadores antiguos
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy - Restricciones para prevenir XSS
        if not app.config.get('TESTING'):
            csp = "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
            response.headers['Content-Security-Policy'] = csp
            
        # Strict Transport Security - Forzar HTTPS (solo en producción)
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Establecer política de referrer
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    return app

def sanitize_input(data):
    """
    Sanitiza datos de entrada para prevenir XSS y otras vulnerabilidades.
    
    Args:
        data: Datos a sanitizar (string, dict, list)
        
    Returns:
        Datos sanitizados del mismo tipo
    """
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        # Usar biblioteca bleach para limpiar HTML y scripts
        return bleach.clean(
            data, 
            tags=[], 
            attributes={}, 
            styles=[], 
            strip=True,
            strip_comments=True
        )
    else:
        # Tipos que no necesitan sanitización (int, float, bool, None)
        return data

def xss_protection(f):
    """
    Decorador que sanitiza automáticamente datos JSON de entrada.
    
    Usage:
        @app.route('/endpoint', methods=['POST'])
        @xss_protection
        def endpoint():
            # request.json ya está sanitizado
            data = request.json
            # ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.is_json:
            # Sanitizar datos JSON de entrada
            request._cached_json = sanitize_input(request.get_json(silent=True))
        return f(*args, **kwargs)
    return decorated_function

def is_secure_origin():
    """
    Verifica si la solicitud proviene de un origen seguro (HTTPS).
    Útil para operaciones sensibles que requieren conexión segura.
    """
    if current_app.config.get('ENV') == 'development':
        return True
    
    forwarded_proto = request.headers.get('X-Forwarded-Proto')
    if forwarded_proto:
        return forwarded_proto == 'https'
    
    return request.is_secure

def log_security_event(event_type, details=None, user_id=None):
    """
    Registra eventos de seguridad para auditoría.
    
    Args:
        event_type: Tipo de evento (login_attempt, access_denied, etc)
        details: Detalles adicionales
        user_id: ID del usuario involucrado (si aplica)
    """
    event_data = {
        'event_type': event_type,
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string,
        'path': request.path,
        'user_id': user_id,
        'details': details
    }
    
    current_app.logger.warning(f"SECURITY EVENT: {event_data}")
    
    # Aquí se podría implementar almacenamiento adicional
    # como una tabla de eventos de seguridad
