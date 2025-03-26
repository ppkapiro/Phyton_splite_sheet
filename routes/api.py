from flask import Blueprint, jsonify, request, current_app, send_file, session, redirect
from flask_jwt_extended import (
    jwt_required, create_access_token, 
    create_refresh_token, get_jwt_identity,
    get_jwt
)
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, add_user, get_user, get_document, get_document_by_envelope
from models import Document
from services.docusign_hmac import DocuSignHMACValidator
from services.docusign_service import DocuSignService
from services.auth_service import AuthService
from datetime import datetime, timedelta
import logging
import time
from src.register_schema import RegisterSchema
from src.login_schema import LoginSchema
from src.send_signature_schema import SendSignatureSchema
from src.status_check_schema import StatusCheckSchema
from src.update_document_schema import UpdateDocumentSchema
from src.delete_document_schema import DeleteDocumentSchema
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import requests
from dotenv import load_dotenv
from services.docusign_pkce import DocuSignPKCE
from .protected import protected_bp
import re
from models.user import User
from config.rate_limiting import limiter  # Agregado para definir "limiter"
from config.security import xss_protection, sanitize_input, log_security_event

# Cargar variables de entorno
load_dotenv()

bp = Blueprint('api', __name__)
pdf_bp = protected_bp

@bp.route('/register', methods=['POST'])
@xss_protection
def register():
    """
    Endpoint para registrar un nuevo usuario.
    
    Espera un JSON con: username, password, email
    """
    try:
        # Obtener datos de la solicitud
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
            
        # Validar datos requeridos
        required_fields = ['username', 'password', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Falta el campo obligatorio '{field}'"}), 400
        
        # Validaciones básicas
        if len(data['username']) < 3:
            return jsonify({"error": "El nombre de usuario debe tener al menos 3 caracteres"}), 400
            
        if len(data['password']) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
            
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({"error": "El formato del email es inválido"}), 400
        
        # Verificar si el usuario ya existe
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({"error": "Nombre de usuario ya existe"}), 400
        
        # Verificar si el email ya existe
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({"error": "Email ya está registrado"}), 400
        
        # Crear nuevo usuario
        new_user = User(
            username=data['username'],
            email=data['email']
        )
        new_user.set_password(data['password'])
        
        # Guardar en base de datos
        db.session.add(new_user)
        db.session.commit()
        
        # Logging de evento de seguridad exitoso
        log_security_event('user_registration', 
                           {'username': data['username']}, 
                           user_id=None)
        
        # Retornar respuesta exitosa
        return jsonify({
            "message": "Usuario registrado exitosamente",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error en registro: {str(e)}")
        db.session.rollback()  # Asegurar rollback en caso de error
        return jsonify({"error": "Error al procesar el registro", "details": str(e)}), 400

@bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Limitar a 5 login por minuto
@xss_protection
def login():
    """
    Endpoint para iniciar sesión de usuario.
    
    Espera un JSON con: username, password
    Retorna tokens JWT para autenticación
    """
    try:
        # Obtener datos de la solicitud
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "Datos inválidos", 
                "details": "No se recibieron datos JSON"
            }), 400
            
        # Validar campos requeridos
        required_fields = ['username', 'password']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "error": "Datos incompletos", 
                "details": f"Faltan campos requeridos: {', '.join(missing_fields)}"
            }), 400
        
        # Buscar el usuario en la base de datos
        user = User.query.filter_by(username=data['username']).first()
        
        # Verificar si el usuario existe y la contraseña es correcta
        if not user or not user.check_password(data['password']):
            log_security_event('failed_login_attempt', 
                              {'username': data['username']}, 
                              user_id=None)
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        # Generar tokens JWT
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Registrar el token para seguimiento (opcional)
        try:
            AuthService.register_token(access_token)
        except Exception as e:
            current_app.logger.warning(f"No se pudo registrar el token: {str(e)}")
        
        # Login exitoso, registrar evento
        log_security_event('successful_login', 
                          {'username': user.username}, 
                          user_id=user.id)
        
        # Retornar respuesta exitosa con tokens
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en login: {str(e)}")
        return jsonify({
            "error": "Error de autenticación", 
            "details": str(e)
        }), 400

@bp.route('/test_protected', methods=['GET'])
@jwt_required()
def test_protected():
    """
    Endpoint protegido para pruebas de autenticación.
    Requiere un token JWT válido.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    return jsonify({
        "status": "success",
        "message": "Acceso autorizado",
        "user_id": current_user_id,
        "username": user.username
    }), 200

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Endpoint para el dashboard que podría utilizarse en redirecciones."""
    return jsonify({
        "status": "success", 
        "message": "Bienvenido al dashboard",
        "auth_success": request.args.get('auth_success', False)
    })

# MANTENER SOLO ESTA DEFINICIÓN:
@bp.route('/docusign/auth')
def docusign_auth():
    """Inicia el flujo de autenticación OAuth 2.0 con PKCE para DocuSign"""
    try:
        # Validar la configuración de DocuSign
        integration_key = current_app.config.get("DOCUSIGN_INTEGRATION_KEY")
        if not integration_key or integration_key == "DOCUSIGN_INTEGRATION_KEY":
            current_app.logger.error("DOCUSIGN_INTEGRATION_KEY no configurada correctamente")
            return jsonify({
                "error": "Error de configuración",
                "details": "DocuSign Integration Key no está configurada correctamente"
            }), 500

        # Usar la clase DocuSignService para manejar la autenticación
        docusign_service = DocuSignService()
        
        # Generar y almacenar el code_verifier
        code_verifier, code_challenge = DocuSignPKCE.generate_pkce_pair()
        
        # Verificar estado de la sesión
        if not DocuSignPKCE.validate_verifier()[0]:
            raise ValueError("Error crítico: La sesión no está funcionando correctamente")

        # Construir URL de autorización usando DocuSignService
        auth_url = docusign_service.generate_auth_url(
            scope='signature',
            response_type='code'
        )

        current_app.logger.info(f"Iniciando OAuth flow - code_verifier: {code_verifier[:10]}...")
        return redirect(auth_url)

    except Exception as e:
        current_app.logger.error(f"Error iniciando autenticación: {str(e)}")
        return jsonify({
            "error": "Error iniciando autenticación",
            "details": str(e)
        }), 500

@bp.route('/status', methods=['GET'])
def api_status():
    """Endpoint para verificar el estado de la API"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": current_app.config.get('API_VERSION', '1.0'),
        "environment": current_app.config.get('ENV', 'development')
    }), 200

# Nuevo endpoint para generar PDF
@bp.route('/pdf/generate_pdf', methods=['POST'])
@jwt_required()   # Se agrega protección JWT
@xss_protection
def generate_pdf():
    """Genera un PDF a partir de datos JSON proporcionados."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True)
    if data is None:
         # Si falta encabezado de autorización, retornar 401; de lo contrario, 400 por datos faltantes.
         if 'Authorization' not in request.headers:
             return jsonify({"error": "Unauthorized", "details": "Missing Authorization Header"}), 401
         return jsonify({"error": "Datos inválidos", "details": "No se recibieron datos JSON"}), 400
    required_fields = ['title', 'participants', 'metadata']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
         return jsonify({
             "error": "Datos inválidos", 
             "details": f"Faltan campos requeridos: {', '.join(missing_fields)}"
         }), 400

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, data.get('title', 'Documento PDF'))
    y = 700
    for participant in data.get('participants', []):
        line = f"{participant.get('name', '')} - {participant.get('role', '')} - {participant.get('share', '')}"
        c.drawString(100, y, line)
        y -= 20
    c.drawString(100, y, f"Metadata: {data.get('metadata', {})}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, attachment_filename="output.pdf")
