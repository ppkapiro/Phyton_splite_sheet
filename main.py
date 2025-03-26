from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from models.database import db, init_app, create_tables
import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta
from config.rate_limiting import limiter  # Se importa el limiter
from config.monitoring import start_monitoring_server
from config.security import configure_security_headers, sanitize_input

# Importar los blueprints necesarios
from routes.api import bp as api_bp
from routes.api import pdf_bp
from routes.protected import protected_bp
from routes.docusign import docusign_bp

def create_app(test_config=None):
    """Crea y configura la aplicación Flask"""
    # Cargar variables de entorno
    load_dotenv()
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG if os.getenv('FLASK_DEBUG') else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Verificar SECRET_KEY
    if not os.getenv('SECRET_KEY'):
        logger.warning("⚠️ SECRET_KEY no configurada en variables de entorno. Usando valor por defecto, lo cual es inseguro para producción.")
    
    # Crear aplicación Flask
    app = Flask(__name__)
    CORS(app)

    # Asegurar que los directorios necesarios existen
    app_dir = Path(app.root_path)
    migrations_dir = app_dir / 'migrations'
    migrations_dir.mkdir(exist_ok=True)
    (app_dir / 'instance').mkdir(exist_ok=True)
    (app_dir / 'tests' / 'output').mkdir(parents=True, exist_ok=True)

    # Configuración desde variables de entorno
    app.config.update(
        DEBUG=os.getenv('FLASK_DEBUG', True),
        SECRET_KEY=os.getenv('SECRET_KEY', 'clave_secreta_por_defecto'),  # ¡IMPORTANTE! Para sesiones seguras
        SQLALCHEMY_DATABASE_URI=os.getenv(
            'SQLALCHEMY_DATABASE_URI',
            'sqlite:///' + os.path.join(app.instance_path, 'app.db')
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_ACCESS_TOKEN_EXPIRES=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
        JWT_REFRESH_TOKEN_EXPIRES=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800)),
        FLASK_APP='main.py',  # Importante para las migraciones
        MIGRATIONS_DIRECTORY=os.path.join(os.path.dirname(__file__), 'migrations'),  # Ruta absoluta
        # Configuración unificada de sesión
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=os.path.join(app.instance_path, 'flask_session'),
        SESSION_FILE_THRESHOLD=500,
        SESSION_KEY_PREFIX='docusign_',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=5),
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    
    # Crear directorio de sesiones si no existe
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # Log de seguridad para configuración de SECRET_KEY
    if app.config['SECRET_KEY'] == 'clave_secreta_por_defecto':
        logger.warning("⚠️ Usando clave secreta por defecto. Esto no es seguro para producción.")

    # Inicializar extensiones
    init_app(app)  # Usa la función corregida
    
    # Cargar configuración de DocuSign
    from config.docusign_config import init_app as init_docusign
    init_docusign(app)
    
    jwt = JWTManager(app)

    # Inicializar Limiter
    limiter.init_app(app)

    # Configurar headers de seguridad
    configure_security_headers(app)

    # Registrar blueprints
    with app.app_context():
        from routes.base import bp as base_bp
        from routes.protected import protected_bp
        from routes.api import bp as api_bp
        from routes.docusign import docusign_bp
        
        app.register_blueprint(base_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        # Mover endpoint de PDF al blueprint protegido
        app.register_blueprint(protected_bp, url_prefix='/api/pdf')
        # Registrar el blueprint de DocuSign con prefijo /api/docusign
        app.register_blueprint(docusign_bp, url_prefix='/api/docusign')
        
        # Solo crear tablas si estamos en modo testing
        if app.config.get('TESTING', False) or app.config.get('ENV') == 'testing':
            create_tables(app)

    # Configuración de JWT
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from services.auth_service import AuthService
        return AuthService.is_token_blacklisted(jwt_payload["jti"])

    # Configuración adicional
    app.config.update({
        'API_VERSION': '1.0',
        'ENV': os.getenv('FLASK_ENV', 'development')
    })

    if app.config.get("ENV") == "production":
        start_monitoring_server(port=8000)  # Se exponen las métricas en el puerto 8000

    @app.before_request
    def validate_request_data():
        """Validación y sanitización global de datos de entrada."""
        if request.is_json:
            try:
                # Ya se ejecutará la sanitización en xss_protection
                # Aquí solo validamos que el JSON sea válido
                request.get_json()
            except Exception as e:
                app.logger.warning(f"JSON inválido recibido: {str(e)}")
                return jsonify({"error": "Datos JSON inválidos"}), 400

    return app

# Crear la aplicación
app = create_app()

# Manejador de error 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '404 - Not Found'}), 404

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)  # Evita la doble inicialización
