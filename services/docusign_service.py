import os
import base64
import hashlib
import secrets
import requests
import logging
from flask import current_app, session
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs
from docusign_esign.client.api_exception import ApiException
from .docusign_auth import DocuSignAuth

class DocuSignService:
    """Servicio para manejar la integración con DocuSign."""
    
    def __init__(self):
        """Inicializa el servicio con la configuración de DocuSign."""
        self.logger = logging.getLogger(__name__)
        self.auth_server = current_app.config.get('DOCUSIGN_AUTH_SERVER', os.getenv("DOCUSIGN_AUTH_SERVER"))
        self.integration_key = current_app.config.get('DOCUSIGN_INTEGRATION_KEY', os.getenv("DOCUSIGN_INTEGRATION_KEY"))
        self.redirect_uri = current_app.config.get('DOCUSIGN_REDIRECT_URI', os.getenv("DOCUSIGN_REDIRECT_URI"))
        self.base_url = current_app.config.get('DOCUSIGN_BASE_URL', os.getenv("DOCUSIGN_BASE_URL"))
        self.token_url = f"https://{self.auth_server}/oauth/token"
        self.api_client = ApiClient()
        self.account_id = os.getenv('DOCUSIGN_ACCOUNT_ID')
        self.auth_service = DocuSignAuth()
        self._configure_auth()

    def _configure_auth(self):
        """Configura la autenticación usando el servicio de auth"""
        try:
            access_token = self.auth_service.get_access_token()
            self.api_client.host = os.getenv('DOCUSIGN_BASE_URL')
            self.api_client.set_default_header(
                "Authorization",
                f"Bearer {access_token}"
            )
        except Exception as e:
            current_app.logger.error(
                f"Error configurando autenticación DocuSign: {str(e)}"
            )
            raise

    @staticmethod
    def create_instance():
        """Factory method para crear instancias del servicio"""
        return DocuSignService()

    def send_document_for_signature(self, pdf_bytes: bytes, recipients: list, **kwargs) -> dict:
        """Envía un documento para firma"""
        try:
            # Validar parámetros requeridos
            if not recipients:
                raise ValueError("Se requiere al menos un destinatario")
                
            for recipient in recipients:
                if not recipient.get('email') or not recipient.get('name'):
                    raise ValueError("Cada destinatario debe tener email y nombre")

            # Validar configuración
            self._validate_config()

            # Crear envelope y enviar
            envelope_definition = self._create_envelope(pdf_bytes, recipients)
            result = self.api_client.envelopes.create(envelope_definition)

            return {
                "envelope_id": result.envelope_id,
                "status": result.status,
                "status_datetime": result.status_date_time
            }

        except ApiException as e:
            current_app.logger.error(f"Error de API DocuSign: {str(e)}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error enviando documento: {str(e)}")
            raise

    def get_signature_status(self, envelope_id: str) -> dict:
        try:
            envelopes_api = EnvelopesApi(self.api_client)
            result = envelopes_api.get_envelope(self.account_id, envelope_id)
            
            return {
                "status": result.status,
                "completed_date": result.completed_date,
                "created_date": result.created_date
            }
        except ApiException as e:
            raise Exception(f"Error al obtener estado: {str(e)}")

    def get_document_status(self, document_id: str, recipient_email: str = None) -> dict:
        """
        Obtiene el estado de un documento.
        
        Args:
            document_id: ID del documento
            recipient_email: Email del destinatario (opcional)
            
        Returns:
            dict: Estado del documento y detalles
        """
        try:
            document = Document.query.filter_by(id=document_id).first()
            if not document:
                raise ValueError("Documento no encontrado")
                
            result = self.get_signature_status(document.envelope_id)
            return {
                "document_id": document_id,
                "envelope_id": document.envelope_id,
                "status": result["status"],
                "completed_date": result["completed_date"],
                "created_date": result["created_date"]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error obteniendo estado del documento: {str(e)}")
            raise

    def _create_envelope(self, pdf_bytes: bytes, recipients: list) -> EnvelopeDefinition:
        # Crear definición del envelope con el documento y los firmantes
        # Esta es una implementación básica que deberías expandir
        pass

    def _validate_config(self):
        """Valida la configuración de DocuSign"""
        required_configs = [
            'DOCUSIGN_INTEGRATION_KEY',
            'DOCUSIGN_ACCOUNT_ID',
            'DOCUSIGN_CLIENT_SECRET'  # Validar con el nombre correcto
        ]
        
        missing = [
            config for config in required_configs 
            if not current_app.config.get(config)
        ]
        
        if missing:
            raise ValueError(f"Faltan configuraciones requeridas: {', '.join(missing)}")

    def generate_pkce_pair(self):
        """
        Genera un par code_verifier/code_challenge para el flujo PKCE.
        
        Returns:
            tuple: (code_verifier, code_challenge) - Valores para el flujo PKCE
        """
        # Generar code_verifier aleatorio
        code_verifier = secrets.token_urlsafe(64)
        
        # Calcular code_challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')  # Eliminar padding '=' según RFC 7636
        
        # Guardar code_verifier en sesión para usarlo en el callback
        session['docusign_code_verifier'] = code_verifier
        
        self.logger.debug(f"PKCE generado: verifier={code_verifier[:5]}..., challenge={code_challenge[:5]}...")
        return code_verifier, code_challenge
    
    def generate_auth_url(self, scope='signature', response_type='code'):
        """
        Genera la URL de autorización de DocuSign.
        
        Genera un valor 'state' único y lo almacena en la sesión para validarlo
        posteriormente en el callback. Este proceso es crítico para prevenir
        ataques CSRF en el flujo OAuth.
        
        Args:
            scope (str): Permisos solicitados
            response_type (str): Tipo de respuesta (code o token)
            
        Returns:
            str: URL de autorización completa
        """
        # Verificar la configuración de sesión
        if not current_app.config.get('SECRET_KEY'):
            self.logger.warning("SECRET_KEY no configurada. Las sesiones podrían no funcionar correctamente.")
        
        # MODIFICACIÓN CLAVE: Usar el state existente sin ninguna condición adicional
        # Si existe en la sesión - simplemente úsalo, no lo sobrescribas nunca
        if 'docusign_state' in session:
            state = session['docusign_state']
            self.logger.debug(f"Usando state existente: {state[:10]}...")
        else:
            # Solo generar nuevo state si realmente no existe
            state = secrets.token_hex(32)
            session['docusign_state'] = state
            self.logger.debug(f"Nuevo state generado: {state[:10]}...")
        
        # Mismo enfoque para code_verifier
        if 'docusign_code_verifier' in session:
            # Si ya hay code_verifier, lo usamos sin regenerar el challenge
            code_verifier = session['docusign_code_verifier']
            
            # Calcular code_challenge desde el code_verifier existente
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            
            self.logger.debug(f"Usando code_verifier existente: {code_verifier[:10]}...")
        else:
            # Generar nuevo par PKCE solo si no existe
            code_verifier, code_challenge = self.generate_pkce_pair()
        
        # Construir URL de autorización
        auth_url = (
            f"https://{self.auth_server}/oauth/auth"
            f"?response_type={response_type}"
            f"&scope={scope}"
            f"&client_id={self.integration_key}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"  # CSRF protection
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )
        
        self.logger.debug(f"URL de autorización generada: {auth_url[:60]}...")
        return auth_url
    
    def exchange_code_for_token(self, auth_code, code_verifier):
        """
        Intercambia el código de autorización por un token de acceso.
        """
        try:
            # Obtener client_secret de la configuración
            client_secret = current_app.config.get('DOCUSIGN_CLIENT_SECRET')
            
            if not client_secret:
                self.logger.error("DOCUSIGN_CLIENT_SECRET no configurado o vacío")
                raise ValueError("DOCUSIGN_CLIENT_SECRET no configurado")
            
            # Construir payload para intercambio de tokens
            payload = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.integration_key,
                "client_secret": client_secret,
                "code_verifier": code_verifier
            }
            
            # Logging detallado para diagnóstico
            self.logger.debug(f"Enviando solicitud a {self.token_url}")
            self.logger.debug(f"Client ID: {self.integration_key[:8]}...")
            self.logger.debug(f"Redirect URI: {self.redirect_uri}")
            self.logger.debug(f"Code length: {len(auth_code)} chars")
            self.logger.debug(f"Verifier length: {len(code_verifier)} chars")
            
            # Realizar solicitud POST con timeout y manejo mejorado
            response = requests.post(self.token_url, data=payload, timeout=10)
            
            # Registro detallado de la respuesta
            self.logger.debug(f"Respuesta de DocuSign: Status={response.status_code}")
            
            if response.status_code != 200:
                self.logger.error(f"Error en respuesta DocuSign: {response.text}")
            
            # Verificar respuesta HTTP
            response.raise_for_status()
            
            # Procesar respuesta JSON
            token_data = response.json()
            self.logger.info("Token de acceso obtenido exitosamente")
            
            return token_data
            
        except requests.exceptions.Timeout:
            self.logger.error("Timeout en solicitud a DocuSign API")
            raise ValueError("La solicitud a DocuSign ha excedido el tiempo límite")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Error HTTP en exchange_code_for_token: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Detalles de error: {e.response.text}")
            raise ValueError(f"Error en la comunicación con DocuSign: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error de conexión en exchange_code_for_token: {str(e)}")
            raise ValueError(f"Error de conexión con DocuSign: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error inesperado en exchange_code_for_token: {str(e)}")
            raise

    def refresh_access_token(self, refresh_token):
        """
        Actualiza un token de acceso usando el refresh token.
        
        Args:
            refresh_token (str): Token de actualización
            
        Returns:
            dict: Nuevo token de acceso y metadata
        """
        # Obtener client_secret de la configuración
        client_secret = current_app.config.get('DOCUSIGN_CLIENT_SECRET')
        
        if not client_secret:
            self.logger.error("No se encontró DOCUSIGN_CLIENT_SECRET en la configuración")
            raise ValueError("Falta la clave secreta de DocuSign (CLIENT_SECRET) en la configuración")
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.integration_key,
            "client_secret": client_secret  # Incluir client_secret en el payload
        }
        
        self.logger.debug("Refrescando token de acceso")
        
        response = requests.post(self.token_url, data=payload)
        response.raise_for_status()
        
        return response.json()
