from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from models.database import db, init_app, create_tables
import os
from dotenv import load_dotenv
from pathlib import Path

# Importar los blueprints necesarios
from routes.api import bp as api_bp
from routes.api import pdf_bp  # Asegurarnos de importar el blueprint pdf_bp
from routes.protected import protected_bp

def create_app():
    """Crea y configura la aplicación Flask"""
    # Cargar variables de entorno
    load_dotenv()

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
        SECRET_KEY=os.getenv('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            'SQLALCHEMY_DATABASE_URI',
            'sqlite:///' + os.path.join(app.instance_path, 'app.db')
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_ACCESS_TOKEN_EXPIRES=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
        JWT_REFRESH_TOKEN_EXPIRES=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800)),
        FLASK_APP='main.py',  # Importante para las migraciones
        MIGRATIONS_DIRECTORY=str(migrations_dir)  # Ruta explícita para migraciones
    )

    # Inicializar extensiones
    init_app(app)  # Usa la función corregida
    
    # Cargar configuración de DocuSign
    from config.docusign_config import init_app as init_docusign
    init_docusign(app)
    
    jwt = JWTManager(app)

    # Registrar blueprints
    with app.app_context():
        from routes.base import bp as base_bp
        from routes.protected import protected_bp
        from routes.api import bp as api_bp
        
        app.register_blueprint(base_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        # Mover endpoint de PDF al blueprint protegido
        app.register_blueprint(protected_bp, url_prefix='/api/pdf')
        
        # Solo crear tablas si estamos en modo testing
        if app.config.get('TESTING', False) or app.config.get('ENV') == 'testing':
            create_tables(app)

    # Configuración de JWT
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from services.auth_service import AuthService
        return AuthService.is_token_blacklisted(jwt_payload["jti"])

    return app

# Crear la aplicación
app = create_app()

# Manejador de error 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '404 - Not Found'}), 404

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)  # Evita la doble inicialización
