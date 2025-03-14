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

@bp.route('/status')
def status():
    """Endpoint de estado de la API"""
    return jsonify({
        "status": "ok",
        "message": "API funcionando"
    }), 200

@bp.route('/register', methods=['POST'])
def register():
    """Endpoint para registro de usuarios con validación Marshmallow"""
    try:
        # Instanciar y validar esquema
        schema = RegisterSchema()
        try:
            # Validar datos de entrada
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        # Continuar con el registro si los datos son válidos
        try:
            user = add_user(data['username'], data['password'])
            current_app.logger.info(f"Usuario creado exitosamente: {data['username']}")
            
            return jsonify({
                "message": "Usuario registrado exitosamente",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": data['email']
                }
            }), 201

        except ValueError as e:
            current_app.logger.error(f"Error al crear usuario: {str(e)}")
            return jsonify({
                "error": "Error al crear usuario",
                "details": str(e)
            }), 400

    except Exception as e:
        current_app.logger.error(f"Error en registro: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
        }), 500

@bp.route('/login', methods=['POST'])
def login():
    """Endpoint para autenticación de usuarios con validación Marshmallow"""
    try:
        # Validar formato de datos usando Marshmallow
        schema = LoginSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                "error": "Datos inválidos",
                "details": err.messages
            }), 400

        username = data['username']
        password = data['password']

        # Verificar credenciales
        user = get_user(username)
        if not user or not user.check_password(password):
            current_app.logger.warning(f"Intento de login fallido para usuario: {username}")
            return jsonify({
                "error": "Credenciales inválidas"
            }), 401  # Cambiar a 401 para credenciales incorrectas

        # 3. Generar tokens JWT
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)

        # 4. Registrar login exitoso
        current_app.logger.info(f"Login exitoso para usuario: {username}")

        return jsonify({
            "message": "Login exitoso",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error en login: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
        }), 500

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Endpoint para cierre de sesión.
    
    Nota: Con JWT, la invalidación real del token se maneja en el cliente 
    eliminando el token almacenado. Este endpoint proporciona:
    1. Confirmación de la acción de logout
    2. Registro del evento en logs
    3. Opcionalmente, agregar el token a una lista negra
    
    Returns:
        200: Sesión cerrada exitosamente
        401: No autenticado (manejado por jwt_required)
        500: Error interno del servidor
    """
    try:
        # 1. Obtener identidad del usuario actual
        current_user = get_jwt_identity()
        current_app.logger.info(f"Solicitud de logout para usuario: {current_user}")

        # 2. Obtener token actual
        token = get_jwt()
        
        # 3. Agregar token a lista negra (opcional)
        try:
            AuthService.logout_user(token["jti"])
            current_app.logger.info(
                f"Token agregado a lista negra para usuario: {current_user}"
            )
        except Exception as e:
            current_app.logger.warning(
                f"Error al agregar token a lista negra: {str(e)}"
            )

        # 4. Retornar confirmación
        return jsonify({
            "status": "success",
            "message": "Sesión cerrada exitosamente",
            "details": {
                "user": current_user,
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error en logout: {str(e)}")
        return jsonify({
            "error": "Error al cerrar sesión",
            "details": "Por favor intente más tarde"
        }), 500

@pdf_bp.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Endpoint para generación de PDF."""
    try:
        current_user = get_jwt_identity()
        current_app.logger.info(f"Generando PDF para usuario: {current_user}")

        # Obtener y validar datos
        data = request.get_json()
        current_app.logger.info(f"Generando PDF para usuario: {current_user}")

        # 1. Obtener identidad del usuario y datos
        data = request.get_json()
        
        # 2. Validar datos de entrada con mensajes específicos
        if not data:
            current_app.logger.error("No se recibieron datos en el request")
            return jsonify({
                "error": "Datos faltantes",
                "details": "El body del request está vacío"
            }), 400

        # Validar campos requeridos con mensajes específicos
        required_fields = ['title', 'participants', 'metadata']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            current_app.logger.error(f"Campos faltantes: {missing_fields}")
            return jsonify({
                "error": "Datos incompletos",
                "details": f"Campos requeridos faltantes: {', '.join(missing_fields)}"
            }), 400

        # 3. Validar estructura de participantes
        if not isinstance(data['participants'], list) or not data['participants']:
            current_app.logger.error("Lista de participantes inválida")
            return jsonify({
                "error": "Datos inválidos",
                "details": "Se requiere al menos un participante en formato lista"
            }), 400

        # Validar estructura de cada participante
        for i, participant in enumerate(data['participants']):
            required_participant_fields = ['name', 'role', 'share']
            missing_participant_fields = [
                field for field in required_participant_fields 
                if field not in participant
            ]
            if missing_participant_fields:
                current_app.logger.error(
                    f"Campos faltantes en participante {i}: {missing_participant_fields}"
                )
                return jsonify({
                    "error": "Datos inválidos",
                    "details": f"Campos requeridos faltantes en participante {i+1}: {', '.join(missing_participant_fields)}"
                }), 400

        # 4. Generar PDF en memoria
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
        pdf.setTitle(f"Split Sheet - {data['title']}")

        # 5. Escribir contenido en el PDF
        # Título
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, 750, "SPLIT SHEET AGREEMENT")
        
        # Información general
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, 720, f"Título: {data['title']}")
        pdf.drawString(100, 700, f"Fecha: {data['metadata'].get('date', 'No especificada')}")
        pdf.drawString(100, 680, f"Proyecto: {data['metadata'].get('project', 'No especificado')}")
        
        # Participantes
        y_position = 620
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, y_position, "Participantes:")
        y_position -= 20
        
        # Lista de participantes
        pdf.setFont("Helvetica", 12)
        for participant in data['participants']:
            pdf.drawString(100, y_position, f"Nombre: {participant['name']}")
            pdf.drawString(300, y_position, f"Rol: {participant['role']}")
            pdf.drawString(450, y_position, f"Share: {participant['share']}%")
            y_position -= 20

        # Espacios para firmas
        y_position = max(y_position - 40, 200)
        for participant in data['participants']:
            pdf.drawString(100, y_position, "_" * 30)
            pdf.drawString(100, y_position - 20, f"Firma de {participant['name']}")
            y_position -= 60

        # 6. Finalizar y guardar PDF
        pdf.showPage()
        pdf.save()
        pdf_buffer.seek(0)

        # 7. Registrar generación exitosa
        current_app.logger.info(
            f"PDF generado exitosamente para '{data['title']}' "
            f"por usuario {current_user}"
        )

        # 8. Retornar PDF como respuesta descargable
        timestamp = int(time.time())
        filename = f"split_sheet_{data['title']}_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {str(e)}")
        return jsonify({
            "error": "Error en generación de PDF",
            "details": str(e)
        }), 500

@bp.route('/send_for_signature', methods=['POST'])
def send_for_signature():
    """Endpoint para envío de documentos a firma"""
    try:
        # Validar datos de entrada usando el schema
        schema = SendSignatureSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                "error": "Error de validación",
                "details": err.messages
            }), 400

        # Usar factory method para crear instancia
        docusign_service = DocuSignService.create_instance()
        result = docusign_service.send_document_for_signature(
            document_id=data['document_id'],
            recipients=[{
                'email': data['recipient_email'],
                'name': data['recipient_name']
            }]
        )

        return jsonify({
            "status": "success",
            "message": "Documento enviado para firma",
            "data": result
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error en envío para firma: {str(e)}")
        return jsonify({
            "error": "Error en el servicio",
            "details": str(e)
        }), 500

@bp.route('/signature_status/<envelope_id>', methods=['GET'])
@jwt_required()
def get_signature_status(envelope_id):
    """
    Endpoint para consulta de estado de firma de documentos.
    NOTA: Esta es una implementación placeholder que simula la consulta.
    En la versión final, se integrará con la API real de DocuSign.

    Args:
        envelope_id: Identificador del envelope a consultar

    Returns:
        200: Estado del envelope + detalles
        401: No autenticado (manejado por jwt_required)
        404: Envelope no encontrado
        500: Error interno del servidor
    """
    try:
        # 1. Obtener identidad del usuario actual
        current_user = get_jwt_identity()
        current_app.logger.info(
            f"Consulta de estado para envelope {envelope_id} "
            f"por usuario {current_user}"
        )

        # 2. Simular consulta a DocuSign (placeholder)
        try:
            # En la versión final, esto consultará la API de DocuSign
            status_data = {
                "envelope_id": envelope_id,
                "status": "completed",  # Valores posibles: created, sent, delivered, signed, completed
                "created_at": "2024-03-07T10:00:00Z",
                "last_updated": "2024-03-07T11:30:00Z",
                "signers": [
                    {
                        "email": "signer1@example.com",
                        "status": "signed",
                        "signed_at": "2024-03-07T11:15:00Z"
                    }
                ],
                "document": {
                    "name": "Split_Sheet_Agreement.pdf",
                    "pages": 3
                }
            }

            # 3. Registrar consulta exitosa
            current_app.logger.info(
                f"Estado recuperado para envelope {envelope_id}: "
                f"{status_data['status']}"
            )

            # 4. Retornar respuesta exitosa
            return jsonify({
                "status": "success",
                "message": "Estado recuperado exitosamente",
                "data": status_data
            }), 200

        except Exception as e:
            current_app.logger.error(
                f"Error consultando estado del envelope {envelope_id}: {str(e)}"
            )
            return jsonify({
                "error": "Envelope no encontrado",
                "details": "No se pudo recuperar el estado del documento"
            }), 404

    except Exception as e:
        current_app.logger.error(f"Error interno: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Error al procesar la solicitud"
        }), 500

@bp.route('/status_check', methods=['POST'])
@jwt_required()
def status_check():
    """
    Endpoint para consultar estado de documentos.
    Requiere autenticación JWT.
    """
    try:
        # 1. Validar datos de entrada usando Marshmallow
        schema = StatusCheckSchema()
        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        # 2. Obtener identidad del usuario actual
        current_user = get_jwt_identity()
        current_app.logger.info(
            f"Consulta de estado para documento {data['document_id']} "
            f"por usuario {current_user}"
        )

        try:
            # 3. Consultar estado en DocuSign (placeholder)
            docusign = DocuSignService()
            status = docusign.get_document_status(
                document_id=data['document_id'],
                recipient_email=data.get('recipient_email')
            )

            # 4. Retornar respuesta exitosa
            return jsonify({
                "status": "success",
                "message": "Estado consultado exitosamente",
                "data": status
            }), 200

        except Exception as e:
            current_app.logger.error(f"Error consultando estado: {str(e)}")
            return jsonify({
                "error": "Error en consulta",
                "details": "No se pudo obtener el estado del documento"
            }), 503

    except Exception as e:
        current_app.logger.error(f"Error interno: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
        }), 500

@bp.route('/update_document', methods=['PUT'])
@jwt_required()
def update_document():
    """
    Endpoint para actualización de documentos.
    Requiere autenticación JWT.
    """
    try:
        # 1. Validar datos de entrada usando Marshmallow
        schema = UpdateDocumentSchema()
        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        # 2. Obtener identidad del usuario actual
        current_user = get_jwt_identity()
        current_app.logger.info(
            f"Solicitud de actualización para documento {data['document_id']} "
            f"por usuario {current_user}"
        )

        # 3. Actualizar documento (placeholder)
        # TODO: Implementar actualización real en la base de datos
        return jsonify({
            "status": "success",
            "message": "Documento actualizado exitosamente",
            "data": data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error actualizando documento: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
        }), 500

@bp.route('/delete_document', methods=['POST'])
@jwt_required()
def delete_document():
    """
    Endpoint para eliminar documentos.
    Requiere autenticación JWT.
    """
    try:
        # 1. Validar datos de entrada usando Marshmallow
        schema = DeleteDocumentSchema()
        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        # 2. Obtener identidad del usuario actual
        current_user = get_jwt_identity()
        current_app.logger.info(
            f"Solicitud de eliminación para documento {data['document_id']} "
            f"por usuario {current_user}"
        )

        # 3. Verificar existencia del documento y permisos
        # TODO: Implementar lógica de verificación

        # 4. Eliminar documento
        try:
            # TODO: Implementar eliminación real en la base de datos
            return jsonify({
                "status": "success",
                "message": "Documento eliminado exitosamente",
                "data": {
                    "document_id": data['document_id']
                }
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error eliminando documento: {str(e)}")
            return jsonify({
                "error": "Error al eliminar documento",
                "details": "No se pudo completar la operación"
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error en delete_document: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
        }), 500

@bp.route('/auth/docusign')
def docusign_auth():
    """Inicia el flujo de autenticación OAuth 2.0 con PKCE"""
    try:
        # Asegurar sesión limpia
        DocuSignPKCE.clear_session_verifier()
        
        # Generar nuevo par PKCE
        _, code_challenge = DocuSignPKCE.generate_pkce_pair()
        
        # Verificar almacenamiento exitoso
        if 'code_verifier' not in session:
            raise ValueError("Error al almacenar code_verifier en sesión")
        
        # Obtener y validar timestamp
        timestamp = session.get('code_verifier_timestamp')
        if not timestamp:
            raise ValueError("Error al almacenar timestamp en sesión")
        
        # Construir URL de autorización
        auth_url = DocuSignPKCE.get_authorization_url(
            client_id=current_app.config['DOCUSIGN_INTEGRATION_KEY'],
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

@bp.route('/callback')
def docusign_callback():
    """Maneja el callback de DocuSign con PKCE"""
    try:
        # 1. Verificar código de autorización
        auth_code = request.args.get('code')
        if not auth_code:
            current_app.logger.error(
                "Callback sin código - Query params: %s",
                dict(request.args)
            )
            return jsonify({
                "error": "No se recibió el código de autorización",
                "details": "Verifique la configuración de DocuSign"
            }), 400

        # 2. Validar code_verifier
        is_valid, error = DocuSignPKCE.validate_verifier()
        if not is_valid:
            current_app.logger.error(f"Error con code_verifier: {error}")
            return jsonify({
                "error": error,
                "details": "Por favor, inicie el proceso de autenticación nuevamente"
            }), 400

        # 3. Intercambiar código por token
        try:
            code_verifier = session.get('code_verifier')
            token_response = exchange_code_for_token(
                auth_code=auth_code,
                code_verifier=code_verifier,
                redirect_uri=current_app.config['DOCUSIGN_REDIRECT_URI']
            )
            
            # 4. Limpiar code_verifier de la sesión
            DocuSignPKCE.clear_session_verifier()
            
            return jsonify({
                "status": "success",
                "message": "Autenticación DocuSign exitosa",
                "data": token_response
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error en intercambio de token: {str(e)}")
            return jsonify({
                "error": "Error obteniendo token",
                "details": str(e)
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error en callback: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": str(e)
        }), 500

def exchange_code_for_token(auth_code: str, code_verifier: str, redirect_uri: str) -> dict:
    """Intercambia el código de autorización por tokens"""
    token_url = f"https://{current_app.config['DOCUSIGN_AUTH_SERVER']}/oauth/token"
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": current_app.config['DOCUSIGN_INTEGRATION_KEY'],
        "client_secret": current_app.config['DOCUSIGN_CLIENT_SECRET'],
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code != 200:
        raise ValueError(f"Error en token endpoint: {response.text}")
        
    return response.json()

@bp.route('/docusign/webhook', methods=['POST'])
def update_document_status(envelope_id, status):
    """Update document status in database."""
    try:
        document = Document.query.filter_by(envelope_id=envelope_id).first()
        if document:
            document.status = status
            db.session.commit()
            current_app.logger.info(f"Document status updated: {envelope_id} -> {status}")
    except Exception as e:
        current_app.logger.error(f"Error updating document status: {str(e)}")
        raise

def docusign_webhook():
    """
    Endpoint para recibir webhooks de DocuSign.
    Implementa validación HMAC obligatoria para asegurar autenticidad.
    """
    try:
        # Validar firma HMAC (abortará con 403 si es inválida)
        validator = DocuSignHMACValidator()
        validator.validate_or_abort(request)
        
        # Procesar evento
        event_data = request.get_json()
        event_type = event_data.get('event')
        envelope_id = event_data.get('envelopeId')
        
        current_app.logger.info(
            f"Webhook autenticado recibido - Tipo: {event_type}, "
            f"Envelope: {envelope_id}"
        )

        # Procesar según tipo de evento
        if event_type in current_app.config['DOCUSIGN_WEBHOOK_EVENTS']:
            status = event_type.replace('envelope-', '')
            update_document_status(envelope_id, status)
            
            return jsonify({
                "status": "success",
                "message": f"Evento {event_type} procesado correctamente"
            }), 200
        else:
            return jsonify({
                "status": "ignored",
                "message": f"Evento {event_type} no procesado"
            }), 200

    except Exception as e:
        current_app.logger.error(f"Error procesando webhook: {str(e)}")
        return jsonify({
            "error": "Error procesando webhook",
            "details": str(e)
        }), 500

@bp.route('/test_protected', methods=['GET'])
@jwt_required()
def test_protected():
    """Endpoint de prueba protegido por JWT"""
    return jsonify({
        'message': 'Acceso autorizado',
        'user_id': get_jwt_identity()
    }), 200

# Error handlers
@bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Recurso no encontrado"}), 404

@bp.errorhandler(500)
def internal_error(error):
    current_app.logger.error(f"Error interno: {str(error)}")
    return jsonify({"error": "Error interno del servidor"}), 500
