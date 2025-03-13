import os
import base64
import hashlib
import requests  # Agregar esta importación
from typing import Tuple
from datetime import datetime, timedelta
from flask import session, current_app

class DocuSignPKCE:
    """Maneja la autenticación PKCE para DocuSign OAuth 2.0"""
    
    # Aumentar tiempo de expiración a 10 minutos
    VERIFIER_EXPIRATION = 600  # 10 minutos en segundos

    @staticmethod
    def generate_pkce_pair() -> Tuple[str, str]:
        """Genera y guarda de forma segura el code_verifier"""
        try:
            # Limpiar verifier anterior
            DocuSignPKCE.clear_session_verifier()
            
            # Generar nuevo code_verifier
            code_verifier = base64.urlsafe_b64encode(os.urandom(64)).rstrip(b'=').decode('utf-8')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('utf-8')).digest()
            ).rstrip(b'=').decode('utf-8')
            
            # Guardar en sesión con timestamp actual
            session['code_verifier'] = code_verifier
            session['code_verifier_timestamp'] = datetime.utcnow().timestamp()
            
            current_app.logger.info("Nuevo code_verifier generado y almacenado en sesión")
            return code_verifier, code_challenge

        except Exception as e:
            current_app.logger.error(f"Error generando PKCE: {str(e)}")
            raise

    @staticmethod
    def validate_verifier() -> Tuple[bool, str]:
        """Valida el code_verifier almacenado"""
        try:
            verifier = session.get('code_verifier')
            timestamp = session.get('code_verifier_timestamp')
            
            if not verifier or not timestamp:
                return False, "No se encontró code_verifier en sesión"
            
            # Verificar expiración
            current_time = datetime.utcnow().timestamp()
            elapsed = current_time - float(timestamp)
            
            if elapsed > DocuSignPKCE.VERIFIER_EXPIRATION:
                DocuSignPKCE.clear_session_verifier()
                return False, "code_verifier expirado"
            
            # Registrar tiempo restante
            remaining = DocuSignPKCE.VERIFIER_EXPIRATION - elapsed
            current_app.logger.info(f"code_verifier válido por {int(remaining)} segundos más")
            
            return True, ""

        except Exception as e:
            current_app.logger.error(f"Error validando verifier: {str(e)}")
            return False, f"Error interno: {str(e)}"

    @staticmethod
    def clear_session_verifier():
        """Limpia el code_verifier de la sesión"""
        session.pop('code_verifier', None)
        session.pop('code_verifier_timestamp', None)

    @staticmethod
    def get_authorization_url(client_id: str, redirect_uri: str, code_challenge: str) -> str:
        """Construye la URL de autorización con PKCE."""
        from flask import current_app
        
        if redirect_uri != current_app.config['DOCUSIGN_REDIRECT_URI']:
            current_app.logger.warning(
                f"redirect_uri mismatch: expected {current_app.config['DOCUSIGN_REDIRECT_URI']}, "
                f"got {redirect_uri}"
            )

        params = {
            'response_type': 'code',
            'scope': 'signature impersonation',
            'client_id': client_id,
            'redirect_uri': current_app.config['DOCUSIGN_REDIRECT_URI'],  # Usar el valor de config
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login'
        }
        
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{current_app.config['DOCUSIGN_CONSENT_URL']}?{query_string}"

    @staticmethod
    def exchange_code_for_token(auth_code: str, code_verifier: str) -> dict:
        """Intercambia el código por tokens."""
        try:
            token_url = current_app.config['DOCUSIGN_TOKEN_URL']
            if not token_url:
                raise ValueError("DOCUSIGN_TOKEN_URL no está configurado")
                
            # Validar parámetros requeridos
            if not current_app.config.get('DOCUSIGN_INTEGRATION_KEY'):
                raise ValueError("DOCUSIGN_INTEGRATION_KEY no está configurado")
                
            if not current_app.config.get('DOCUSIGN_CLIENT_SECRET'):
                raise ValueError("DOCUSIGN_CLIENT_SECRET no está configurado")
                
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": current_app.config['DOCUSIGN_INTEGRATION_KEY'],
                "client_secret": current_app.config['DOCUSIGN_CLIENT_SECRET'],
                "redirect_uri": current_app.config['DOCUSIGN_REDIRECT_URI'],
                "code_verifier": code_verifier
            }
            
            current_app.logger.info(
                "Solicitando token con code_verifier: %s...",
                code_verifier[:10] if code_verifier else None
            )
            
            response = requests.post(token_url, data=data)
            
            if response.status_code != 200:
                error_msg = f"Error en token endpoint: {response.text}"
                current_app.logger.error(error_msg)
                raise ValueError(error_msg)
                
            token_data = response.json()
            current_app.logger.info("Token obtenido exitosamente")
            
            return token_data
            
        except Exception as e:
            current_app.logger.error("Error en exchange_code_for_token: %s", str(e))
            raise

    @staticmethod
    def verify_callback_state(request) -> bool:
        """Verifica el estado del callback"""
        return bool(request.args.get('code'))
