from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import (
    jwt_required, create_access_token, 
    create_refresh_token, get_jwt_identity,
    get_jwt
)
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, add_user, get_user
from services.docusign_service import DocuSignService
from services.auth_service import AuthService
from datetime import datetime
import logging
import time
from src.register_schema import RegisterSchema
from src.login_schema import LoginSchema
from src.send_signature_schema import SendSignatureSchema
from src.status_check_schema import StatusCheckSchema
from src.update_document_schema import UpdateDocumentSchema
from src.delete_document_schema import DeleteDocumentSchema

bp = Blueprint('api', __name__)

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
    """
    Endpoint para autenticación de usuarios con validación Marshmallow.
    """
    try:
        # 1. Validar datos de entrada usando Marshmallow
        schema = LoginSchema()
        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        username = data['username']
        password = data['password']

        # 2. Buscar usuario y verificar credenciales
        user = get_user(username)
        if not user or not user.check_password(password):
            current_app.logger.warning(f"Intento de login fallido para usuario: {username}")
            return jsonify({
                "error": "Credenciales inválidas"
            }), 401

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

@bp.route('/generate_pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    """
    Endpoint para generación de PDF de Split Sheet.
    NOTA: Esta es una implementación placeholder.
    En la versión final, se integrará con un servicio real de generación de PDF.
    
    Espera recibir:
    {
        "title": "Nombre de la canción",
        "participants": [
            {"name": "Artista 1", "role": "Compositor", "share": 50},
            {"name": "Artista 2", "role": "Productor", "share": 50}
        ],
        "metadata": {
            "date": "2024-03-07",
            "project": "Álbum X"
        }
    }
    
    Returns:
        200: PDF generado exitosamente + URL y metadata
        400: Datos inválidos o incompletos
        401: No autenticado
        500: Error en generación
    """
    try:
        # 1. Obtener identidad del usuario
        current_user = get_jwt_identity()
        current_app.logger.info(f"Solicitud de generación de PDF de {current_user}")

        # 2. Validar datos de entrada
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "Datos faltantes",
                "details": "Se requiere el cuerpo de la solicitud"
            }), 400

        # 3. Validar campos requeridos
        required_fields = ['title', 'participants']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": "Datos incompletos",
                "details": f"Campos faltantes: {', '.join(missing_fields)}"
            }), 400

        # 4. Validar estructura de participantes
        if not isinstance(data['participants'], list) or not data['participants']:
            return jsonify({
                "error": "Datos inválidos",
                "details": "Se requiere al menos un participante"
            }), 400

        # 5. Simular generación de PDF (placeholder)
        timestamp = int(time.time())
        pdf_data = {
            "document_id": f"split_{timestamp}",
            "url": f"https://storage.example.com/splits/{timestamp}.pdf",
            "filename": f"split_sheet_{data['title']}_{timestamp}.pdf",
            "metadata": {
                "title": data['title'],
                "creator": current_user,
                "created_at": datetime.utcnow().isoformat(),
                "participants_count": len(data['participants']),
                "total_shares": sum(p.get('share', 0) for p in data['participants'])
            },
            "status": "generated"
        }

        # 6. Registrar generación exitosa
        current_app.logger.info(
            f"PDF generado exitosamente: {pdf_data['document_id']} "
            f"para '{data['title']}' por {current_user}"
        )

        # 7. Retornar respuesta exitosa
        return jsonify({
            "status": "success",
            "message": "PDF generado exitosamente",
            "data": pdf_data
        }), 200

    except KeyError as e:
        current_app.logger.error(f"Datos inválidos: {str(e)}")
        return jsonify({
            "error": "Datos inválidos",
            "details": f"Campo requerido faltante: {str(e)}"
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {str(e)}")
        return jsonify({
            "error": "Error en generación de PDF",
            "details": "Error interno del servidor"
        }), 500

@bp.route('/send_for_signature', methods=['POST'])
def send_for_signature():
    """
    Endpoint para envío de documentos a firma.
    Implementa validación mediante Marshmallow.
    """
    try:
        # 1. Validar datos de entrada usando Marshmallow
        schema = SendSignatureSchema()
        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return jsonify(err.messages), 400

        # 2. Simular envío a DocuSign (placeholder)
        envelope_id = f"test_123_{data['document_id']}"

        # 3. Retornar respuesta exitosa
        return jsonify({
            "status": "success",
            "message": "Firma enviada",
            "data": {
                "envelope_id": envelope_id,
                "document_id": data['document_id'],
                "recipient": {
                    "email": data['recipient_email'],
                    "name": data['recipient_name']
                }
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error en envío para firma: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": "Por favor intente más tarde"
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

# Error handlers
@bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Recurso no encontrado"}), 404

@bp.errorhandler(500)
def internal_error(error):
    current_app.logger.error(f"Error interno: {str(error)}")
    return jsonify({"error": "Error interno del servidor"}), 500
