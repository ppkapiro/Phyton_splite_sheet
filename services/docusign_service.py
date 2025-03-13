from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs
from docusign_esign.client.api_exception import ApiException
from flask import current_app
import base64
import jwt
import time
import os
from .docusign_auth import DocuSignAuth

class DocuSignService:
    def __init__(self):
        self.api_client = ApiClient()
        self.account_id = os.getenv('DOCUSIGN_ACCOUNT_ID')
        self.base_url = os.getenv('DOCUSIGN_BASE_URL')
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
            'DOCUSIGN_CLIENT_SECRET'
        ]
        
        missing = [
            config for config in required_configs 
            if not current_app.config.get(config)
        ]
        
        if missing:
            raise ValueError(f"Faltan configuraciones requeridas: {', '.join(missing)}")
