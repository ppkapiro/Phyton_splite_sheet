import os
import requests
import logging
import time  # Añadir esta importación
from flask import Blueprint, request, jsonify, current_app, session, redirect, url_for, abort
from werkzeug.exceptions import BadRequest
from services.docusign_service import DocuSignService

# Crear el blueprint para DocuSign
docusign_bp = Blueprint('docusign', __name__)

# Configuración de logging
logger = logging.getLogger(__name__)

@docusign_bp.route('/auth', methods=['GET'])
def docusign_auth():
    """
    Inicia el flujo de autorización de DocuSign.
    
    Este endpoint redirige al usuario a DocuSign para autorizar nuestra aplicación.
    Genera y almacena un valor 'state' para prevenir ataques CSRF.
    """
    try:
        # Verificación de configuración
        logger.info("Iniciando flujo DocuSign auth...")
        
        # MODIFICACIÓN CLAVE: Imprimir claramente los valores de la sesión para diagnóstico
        if 'docusign_state' in session:
            existing_state = session['docusign_state']
            logger.debug(f"Encontrado state existente en la sesión: {existing_state[:10]}...")
        else:
            logger.debug("No hay state en la sesión, se generará uno nuevo")
            
        # Verificar configuración crítica
        integration_key = current_app.config.get('DOCUSIGN_INTEGRATION_KEY')
        auth_server = current_app.config.get('DOCUSIGN_AUTH_SERVER')
        redirect_uri = current_app.config.get('DOCUSIGN_REDIRECT_URI')
        
        if not integration_key or integration_key == "DOCUSIGN_INTEGRATION_KEY":
            logger.error("DOCUSIGN_INTEGRATION_KEY no configurada correctamente")
            return jsonify({
                "error": "Error de configuración",
                "details": "DocuSign Integration Key no está configurada correctamente"
            }), 500
            
        if not auth_server:
            logger.error("DOCUSIGN_AUTH_SERVER no configurado")
            return jsonify({
                "error": "Error de configuración",
                "details": "DOCUSIGN_AUTH_SERVER no configurado"
            }), 500
            
        if not redirect_uri:
            logger.error("DOCUSIGN_REDIRECT_URI no configurado")
            return jsonify({
                "error": "Error de configuración", 
                "details": "DOCUSIGN_REDIRECT_URI no configurado"
            }), 500
            
        # Verificar que la clave secreta esté configurada
        if not current_app.config.get('SECRET_KEY'):
            logger.error("SECRET_KEY no configurada. Las sesiones no funcionarán correctamente.")
            return jsonify({"error": "Error de configuración del servidor"}), 500

        # Inicializar el servicio DocuSign con más información de diagnóstico
        try:
            logger.debug(f"Configuración: INTEGRATION_KEY={integration_key[:8]}..., AUTH_SERVER={auth_server}, REDIRECT_URI={redirect_uri}")
            docusign = DocuSignService()
        except Exception as e:
            logger.error(f"Error creando DocuSignService: {str(e)}")
            return jsonify({
                "error": "Error de inicialización",
                "details": f"No se pudo inicializar el servicio DocuSign: {str(e)}"
            }), 500
        
        # Generar URL de autorización
        try:
            # MODIFICACIÓN CLAVE: Asegurarnos de que no se modifique la sesión si ya tiene valores
            # Guardar los valores actuales para restaurarlos si es necesario
            session_backup = {}
            if 'docusign_state' in session:
                session_backup['docusign_state'] = session['docusign_state']
            if 'docusign_code_verifier' in session:
                session_backup['docusign_code_verifier'] = session['docusign_code_verifier']
            if 'code_verifier_timestamp' in session:
                session_backup['code_verifier_timestamp'] = session['code_verifier_timestamp']
            
            # Generar URL normalmente
            auth_url = docusign.generate_auth_url(
                scope='signature',
                response_type='code'
            )
            
            # Restaurar los valores originales si cambiaron y había valores previos
            for key, value in session_backup.items():
                if key in session and session[key] != value:
                    logger.warning(f"Restaurando valor original de {key} que cambió")
                    session[key] = value
            
            logger.debug(f"URL generada: {auth_url[:100]}...")
        except Exception as e:
            logger.error(f"Error generando URL de autorización: {str(e)}")
            return jsonify({
                "error": "Error generando URL",
                "details": str(e)
            }), 500
        
        # Verificar que el state se haya almacenado correctamente en la sesión
        if not session.get('docusign_state'):
            logger.error("No se pudo almacenar el state en la sesión. Verificar SECRET_KEY.")
            return jsonify({"error": "Error de sesión"}), 500
            
        logger.info(f"Iniciando flujo OAuth con DocuSign. State almacenado: {session.get('docusign_state')[:5]}...")
        
        # Redirigir al usuario a la URL de autorización de DocuSign
        return redirect(auth_url)
        
    except Exception as e:
        logger.exception(f"Error no controlado en docusign_auth: {str(e)}")
        return jsonify({
            "error": "Error al iniciar flujo de autorización", 
            "details": str(e),
            "traceback": f"{type(e).__name__}: {str(e)}"
        }), 500

@docusign_bp.route('/callback', methods=['GET'])
def docusign_callback():
    """
    Endpoint para recibir el callback de DocuSign después de la autorización.
    
    DocuSign redirige aquí con un código de autorización que luego intercambiamos
    por un token de acceso. Se valida el parámetro 'state' para prevenir CSRF.
    
    Query parameters:
    - code: Código de autorización de DocuSign
    - state: Valor de estado para prevenir CSRF
    - format: (opcional) Si es 'json', devuelve JSON en lugar de redirigir
    """
    # Mejorado para capturar y mostrar todos los parámetros recibidos
    logger.info(f"Callback de DocuSign recibido. Parámetros: {dict(request.args)}")
    
    try:
        # Verificar que la clave secreta esté configurada
        if not current_app.config.get('SECRET_KEY'):
            logger.error("SECRET_KEY no configurada. Las sesiones no funcionarán correctamente.")
            return jsonify({"error": "Error de configuración del servidor"}), 500

        # Extraer los parámetros 'code' y 'state'
        auth_code = request.args.get('code')
        state_received = request.args.get('state')
        response_format = request.args.get('format')  # Para pruebas 
        
        # Validar que se recibieron los parámetros necesarios
        if not auth_code:
            logger.error("No se recibió el parámetro 'code' en el callback de DocuSign")
            return jsonify({"error": "Falta el parámetro 'code'", "details": "El parámetro 'code' es obligatorio"}), 400
            
        if not state_received:
            logger.error("No se recibió el parámetro 'state' en el callback de DocuSign")
            return jsonify({"error": "Falta el parámetro 'state'", "details": "El parámetro 'state' es obligatorio"}), 400
        
        # Recuperar el estado esperado desde la sesión
        expected_state = session.get('docusign_state')
        
        # Si no hay estado en la sesión, es un problema de configuración o sesión expirada
        if not expected_state:
            logger.error("No se encontró 'state' en la sesión. Posible problema de sesión o configuración.")
            return jsonify({
                "error": "Estado de sesión inválido", 
                "details": "No se encontró el estado esperado en la sesión. Posiblemente la sesión expiró."
            }), 400
        
        # Validar el estado para prevenir ataques CSRF
        if state_received != expected_state:
            logger.error(f"Estado inválido en callback de DocuSign. Esperado: {expected_state[:5]}..., Recibido: {state_received[:5]}...")
            return jsonify({"error": "Estado inválido o manipulado", "details": "El valor recibido para state no coincide con el esperado"}), 400
        
        logger.info(f"State validado correctamente: {state_received[:5]}...")
        
        # Eliminar el estado de la sesión una vez utilizado
        session.pop('docusign_state', None)
        
        # Obtener el code_verifier de la sesión para completar el flujo PKCE
        code_verifier = session.get('docusign_code_verifier')
        if not code_verifier:
            logger.error("No se encontró code_verifier en la sesión")
            return jsonify({"error": "Falta el code_verifier para completar la autenticación", "details": "El valor 'docusign_code_verifier' es requerido"}), 400

        # Verificar que el code_verifier no haya expirado
        timestamp = session.get('code_verifier_timestamp')
        if not timestamp:
            logger.error("No se encontró timestamp para code_verifier")
            return jsonify({
                "error": "Error de verificación", 
                "details": "Falta timestamp para code_verifier"
            }), 400
            
        # NUEVA VALIDACIÓN: Verificar code_verifier a través de DocuSignPKCE.validate_verifier()
        from services.docusign_pkce import DocuSignPKCE
        valid, error_msg = DocuSignPKCE.validate_verifier()
        if not valid:
            logger.error(f"Code verifier inválido: {error_msg}")
            session.pop('docusign_code_verifier', None)
            session.pop('code_verifier_timestamp', None)
            return jsonify({"error": "Code verifier inválido", "details": error_msg}), 400

        # Comprobar expiración
        now = int(time.time())
        max_age = 300  # 5 minutos en segundos
        if now - timestamp > max_age:
            logger.error(f"Code verifier expirado. Edad: {now - timestamp} segundos, máximo: {max_age}")
            return jsonify({
                "error": "Code verifier expirado", 
                "details": f"El código ha expirado hace {now - timestamp - max_age} segundos"
            }), 400
            
        # Eliminar el code_verifier de la sesión una vez utilizado
        session.pop('docusign_code_verifier', None)
        session.pop('code_verifier_timestamp', None)
        
        # Inicializar el servicio DocuSign
        docusign = DocuSignService()
        
        # Intercambiar código por token con mejor manejo de errores
        try:
            tokens = docusign.exchange_code_for_token(auth_code, code_verifier)
        except ValueError as e:
            # Capturar errores específicos de validación
            logger.error(f"Error de validación en intercambio de tokens: {str(e)}")
            return jsonify({
                "error": "Error de validación", 
                "details": str(e),
                "code": "VALIDATION_ERROR"
            }), 400
        except requests.exceptions.RequestException as e:
            # Errores de comunicación con DocuSign
            logger.error(f"Error de comunicación con DocuSign: {str(e)}")
            # Añadir información extra de diagnóstico
            error_details = str(e)
            if hasattr(e, 'response') and e.response:
                try:
                    error_details = f"{error_details} - {e.response.text}"
                    # Intentar obtener JSON con mensaje de error específico
                    error_json = e.response.json()
                    if 'error' in error_json and 'error_description' in error_json:
                        error_details = f"{error_json['error']}: {error_json['error_description']}"
                except:
                    pass
                    
            return jsonify({
                "error": "Error al comunicarse con DocuSign", 
                "details": error_details,
                "code": "API_ERROR",
                "status_code": e.response.status_code if hasattr(e, 'response') else None
            }), 500
        
        # Guardar los tokens en la sesión (o en la base de datos para persistencia)
        session['docusign_access_token'] = tokens.get('access_token')
        session['docusign_refresh_token'] = tokens.get('refresh_token')
        session['docusign_token_expiry'] = tokens.get('expires_in')
        
        logger.info("Token de DocuSign obtenido exitosamente")
        
        # Para tests, devolver JSON en lugar de redirigir
        if response_format == 'json':
            return jsonify({
                "access_token": tokens.get('access_token'),
                "refresh_token": tokens.get('refresh_token'),
                "expires_in": tokens.get('expires_in'),
                "status": "success"
            })
        
        # Redirigir a una página de éxito o dashboard
        return redirect(url_for('api.dashboard', auth_success=True))
        
    except BadRequest as e:
        logger.error(f"Error de solicitud en callback de DocuSign: {str(e)}")
        return jsonify({"error": "Solicitud inválida", "details": str(e)}), 400
    except Exception as e:
        logger.exception(f"Error no controlado en callback de DocuSign: {str(e)}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

@docusign_bp.route('/status', methods=['GET'])
def docusign_status():
    """Verifica el estado de la autenticación con DocuSign."""
    access_token = session.get('docusign_access_token')
    if access_token:
        return jsonify({
            "authenticated": True,
            "expires_in": session.get('docusign_token_expiry')
        })
    else:
        return jsonify({"authenticated": False})

@docusign_bp.route('/send_for_signature', methods=['POST'])
def send_for_signature():
    """Envía un documento para firma usando DocuSign"""
    try:
        # Validar datos de entrada
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No se recibieron datos",
                "details": "Se requiere un objeto JSON con información de firma"
            }), 400

        # Validar campos requeridos
        required_fields = ["recipient_email", "recipient_name"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                "error": "Datos incompletos",
                "details": f"Faltan campos requeridos: {', '.join(missing_fields)}"
            }), 400

        # Usar el método de clase para crear la instancia
        docusign_service = DocuSignService.create_instance()
        
        # Preparar destinatarios
        recipients = [{
            "email": data.get("recipient_email"),
            "name": data.get("recipient_name")
        }]

        # Obtener documento (aquí deberías implementar la lógica para obtener el PDF)
        # Por ahora usamos un PDF de ejemplo
        pdf_bytes = b"PDF content here"  # Reemplazar con el PDF real

        # Enviar para firma
        result = docusign_service.send_document_for_signature(
            pdf_bytes=pdf_bytes,
            recipients=recipients
        )

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as e:
        logger.exception(f"Error al enviar documento para firma: {str(e)}")
        return jsonify({
            "error": "Error al procesar la solicitud",
            "details": str(e)
        }), 500
