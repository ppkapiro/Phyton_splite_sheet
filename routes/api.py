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

# Cargar variables de entorno
load_dotenv()

bp = Blueprint('api', __name__)
pdf_bp = protected_bp

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
                "details": "DocuSign Integration Key no está configurada correctamente. Verifique su archivo .env"
            }), 500
        
        # Asegurar sesión limpia
        DocuSignPKCE.clear_session_verifier()
        
        # Generar nuevo par PKCE
        _, code_challenge = DocuSignPKCE.generate_pkce_pair()
        
        # Verificar almacenamiento exitoso
        if 'code_verifier' not in session:
            current_app.logger.error("Error: code_verifier no guardado en sesión")
            raise ValueError("Error al almacenar code_verifier en sesión")
        
        # Obtener y validar timestamp
        timestamp = session.get('code_verifier_timestamp')
        if not timestamp:
            current_app.logger.error("Error: timestamp no guardado en sesión")
            raise ValueError("Error al almacenar timestamp en sesión")
        
        # Construir URL de autorización
        auth_url = DocuSignPKCE.get_authorization_url(
            client_id=integration_key,  # Usar la key validada
            redirect_uri=current_app.config['DOCUSIGN_REDIRECT_URI'],
            code_challenge=code_challenge
        )
        
        current_app.logger.info(
            f"Iniciando autenticación DocuSign - Verifier expira en "
            f"{DocuSignPKCE.VERIFIER_EXPIRATION} segundos"
        )
        return redirect(auth_url)
        
    except Exception as e:
        current_app.logger.error(f"Error iniciando autenticación: {str(e)}")
        DocuSignPKCE.clear_session_verifier()
        return jsonify({
            "error": "Error iniciando autenticación",
            "details": str(e)
        }), 500

# El resto del archivo se mantiene igual
