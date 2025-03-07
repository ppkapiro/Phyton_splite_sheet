from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models.database import init_db
import os
import importlib
import pkgutil

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
jwt = JWTManager(app)

# Inicializar la base de datos
init_db(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    from services.auth_service import AuthService
    return AuthService.is_token_blacklisted(jwt_payload["jti"])

# Registrar automáticamente todos los blueprints en la carpeta routes
def register_blueprints():
    import routes
    for _, name, _ in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f'routes.{name}')
        if hasattr(module, 'bp'):
            app.register_blueprint(module.bp)

register_blueprints()

# Manejador de error 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '404 - Not Found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
