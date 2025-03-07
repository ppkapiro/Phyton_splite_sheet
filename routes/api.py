from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from services.docusign_service import DocuSignService
from services.auth_service import AuthService

bp = Blueprint('api', __name__)

@bp.route('/status')
def status():
    """
    Stub mínimo para verificación de API.
    GET /api/status -> 200 OK
    """
    return jsonify({
        "status": "ok",
        "message": "API funcionando"
    }), 200

@bp.route('/register', methods=['POST'])
def register():
    """
    Stub mínimo para registro de usuario.
    POST /api/register -> 201 Created
    """
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Datos incompletos"}), 400
        
        # Stub: Retornar éxito sin procesar
        return jsonify({
            "message": "Usuario registrado exitosamente"
        }), 201
    except Exception:
        return jsonify({"error": "Error interno"}), 500

@bp.route('/login', methods=['POST'])
def login():
    """
    Stub mínimo para login.
    POST /api/login -> 200 OK
    """
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Credenciales incompletas"}), 400
            
        # Stub: Retornar tokens simulados
        return jsonify({
            "access_token": "stub_token",
            "refresh_token": "stub_refresh"
        }), 200
    except Exception:
        return jsonify({"error": "Credenciales inválidas"}), 401

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    token = get_jwt()
    result = AuthService.logout_user(token["jti"])
    return jsonify(result), 200

@bp.route('/generate_pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    """Stub para generación de PDF (ruta protegida)"""
    # Retornar 401 si no hay token (manejado por jwt_required)
    return jsonify({
        "status": "success",
        "message": "PDF generado (stub)"
    }), 200

@bp.route('/send_for_signature', methods=['POST'])
# @jwt_required()  # Comentado para el stub de pruebas
def send_for_signature():
    """
    Stub para el endpoint de firma.
    NOTA: Autenticación deshabilitada temporalmente para pruebas.
    POST /api/send_for_signature -> 200 OK
    """
    try:
        # Stub: Simular éxito sin verificaciones
        return jsonify({
            "status": "success",
            "message": "Firma enviada",
            "envelope_id": "test_123"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/signature_status/<envelope_id>', methods=['GET'])
@jwt_required()
def get_signature_status(envelope_id):
    try:
        docusign = DocuSignService()
        status = docusign.get_signature_status(envelope_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
