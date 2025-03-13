from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models.database import db, init_app, create_tables
import os
from dotenv import load_dotenv

def create_app():
    """Crea y configura la aplicación Flask"""
    # Cargar variables de entorno
    load_dotenv()

    # Crear aplicación Flask
    app = Flask(__name__)
    CORS(app)

    # Configuración desde variables de entorno
    app.config.update(
        DEBUG=os.getenv('FLASK_DEBUG', True),
        SECRET_KEY=os.getenv('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY'),
        JWT_ACCESS_TOKEN_EXPIRES=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
        JWT_REFRESH_TOKEN_EXPIRES=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))
    )

    # Asegurar que SQLAlchemy se inicializa una sola vez
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        init_app(app)
    
    jwt = JWTManager(app)

    # Registrar blueprints y crear tablas
    with app.app_context():
        from routes.base import bp as base_bp
        from routes.api import bp as api_bp
        
        app.register_blueprint(base_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
