import hmac
import hashlib
import base64
import json
from flask import current_app, Request, abort
from typing import Tuple

class DocuSignHMACValidator:
    """
    Validador de firmas HMAC para webhooks de DocuSign.
    Implementa la verificación de seguridad según la especificación de DocuSign.
    """

    def __init__(self):
        """Inicializa el validador obteniendo la clave HMAC de la configuración"""
        self.hmac_key = current_app.config['DOCUSIGN_HMAC_KEY'].encode('utf-8')
        if not self.hmac_key:
            raise ValueError("DOCUSIGN_HMAC_KEY no está configurada")

    def validate_or_abort(self, request: Request) -> None:
        """
        Valida la firma HMAC de una solicitud y aborta con 403 si es inválida.
        
        Args:
            request: Objeto Request de Flask
            
        Raises:
            Abort(403): Si la validación falla
        """
        is_valid, error = self._validate_request(request)
        if not is_valid:
            current_app.logger.error(f"Validación HMAC fallida: {error}")
            abort(403, description=f"Firma inválida: {error}")

    def _validate_request(self, request: Request) -> Tuple[bool, str]:
        """
        Implementación interna de la validación HMAC.
        
        Args:
            request: Objeto Request de Flask
            
        Returns:
            Tuple[bool, str]: (es_válido, mensaje_error)
        """
        try:
            # Obtener y validar cabeceras requeridas
            signature = request.headers.get('X-DocuSign-Signature-1')
            timestamp = request.headers.get('X-DocuSign-Signature-Timestamp')
            
            if not signature or not timestamp:
                return False, "Faltan cabeceras de firma requeridas"

            # Obtener payload y construir mensaje
            payload = request.get_data()
            message = timestamp.encode('utf-8') + b'\n' + payload + b'\n'

            # Calcular HMAC usando SHA256
            calculated_hmac = hmac.new(
                self.hmac_key,
                message,
                hashlib.sha256
            )
            calculated_signature = base64.b64encode(calculated_hmac.digest()).decode()

            # Comparación segura contra timing attacks
            if not hmac.compare_digest(calculated_signature, signature):
                return False, "Firma HMAC inválida"

            return True, ""

        except Exception as e:
            current_app.logger.error(f"Error en validación HMAC: {str(e)}")
            return False, f"Error validando firma HMAC: {str(e)}"
