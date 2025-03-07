from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from services.docusign_service import DocuSignService
from services.auth_service import AuthService

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "API en funcionamiento"})

@bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        result = AuthService.register_user(data['username'], data['password'])
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500

@bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        result = AuthService.login_user(data['username'], data['password'])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    token = get_jwt()
    result = AuthService.logout_user(token["jti"])
    return jsonify(result), 200

@bp.route('/generate_pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    # Placeholder para la futura implementación
    return jsonify({
        "status": "success",
        "message": "Endpoint para generación de PDF (placeholder)"
    }), 200

@bp.route('/send_for_signature', methods=['POST'])
@jwt_required()
def send_for_signature():
    try:
        if 'file' not in request.files or 'recipients' not in request.json:
            return jsonify({"error": "Falta archivo PDF o lista de destinatarios"}), 400
        
        pdf_file = request.files['file']
        recipients = request.json['recipients']
        
        docusign = DocuSignService()
        envelope_id = docusign.send_document_for_signature(pdf_file.read(), recipients)
        
        return jsonify({
            "status": "success",
            "envelope_id": envelope_id
        })
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
