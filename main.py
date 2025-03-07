from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models.database import init_db
import os

# Crear e inicializar la aplicación Flask
app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
jwt = JWTManager(app)

# Inicializar la base de datos
init_db(app)

# IMPORTANTE: Registrar blueprints después de crear la app
# Importar blueprints - el orden es importante
from routes.base import bp as base_bp
from routes.api import bp as api_bp

# Registrar blueprint base
app.register_blueprint(base_bp)

# Registrar blueprint api con prefijo /api para todos sus endpoints
app.register_blueprint(api_bp, url_prefix='/api')

if app.debug:
    # Imprimir rutas registradas para verificación
    print("\nEndpoints disponibles:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.methods} {rule.rule} -> {rule.endpoint}")

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    from services.auth_service import AuthService
    return AuthService.is_token_blacklisted(jwt_payload["jti"])

# Manejador de error 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '404 - Not Found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
