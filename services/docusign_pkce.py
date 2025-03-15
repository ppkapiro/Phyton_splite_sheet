import os
import base64
import hashlib
import time
from datetime import datetime, timedelta
from flask import session, current_app
import logging

class DocuSignPKCE:
    """
    Clase para manejar el flujo OAuth 2.0 con PKCE para DocuSign.
    Implementa la generación del par PKCE y manejo de la sesión.
    """
    # Constantes para configuración
    CODE_VERIFIER_KEY = 'code_verifier'
    CODE_VERIFIER_TIMESTAMP_KEY = 'code_verifier_timestamp'
    STATE_KEY = 'docusign_oauth_state'
    VERIFIER_EXPIRATION = 300  # 5 minutos en segundos

    @classmethod
    def generate_pkce_pair(cls):
        """
        Genera un par PKCE:
          - code_verifier: cadena aleatoria segura (mínimo 43 caracteres)
          - code_challenge: SHA256(code_verifier) codificado en Base64 URL-safe sin '='
        
        Returns:
            tuple: (code_verifier, code_challenge)
        """
        try:
            # Generar code_verifier seguro
            verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
            if len(verifier) < 43:
                # Asegurarse que tenga al menos 43 caracteres
                verifier += 'A' * (43 - len(verifier))
            
            # Calcular code_challenge (SHA256 + Base64 URL-safe)
            sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
            challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
            
            # Almacenar code_verifier en sesión con timestamp
            session[cls.CODE_VERIFIER_KEY] = verifier
            session[cls.CODE_VERIFIER_TIMESTAMP_KEY] = int(time.time())
            
            # Generar state para prevenir CSRF
            state = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
            session[cls.STATE_KEY] = state
            
            current_app.logger.debug(f"Par PKCE generado: verifier={len(verifier)} chars, challenge={len(challenge)} chars")
            return verifier, challenge
            
        except Exception as e:
            current_app.logger.error(f"Error generando par PKCE: {str(e)}")
            raise
    
    @classmethod
    def validate_verifier(cls):
        """
        Valida que el code_verifier exista en la sesión y no haya expirado.
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # Verificar que existe code_verifier
        if cls.CODE_VERIFIER_KEY not in session:
            return False, "No hay code_verifier en sesión"
        
        # Verificar que existe timestamp
        if cls.CODE_VERIFIER_TIMESTAMP_KEY not in session:
            return False, "No hay timestamp para code_verifier"
        
        # Verificar que no haya expirado
        timestamp = session.get(cls.CODE_VERIFIER_TIMESTAMP_KEY)
        now = int(time.time())
        if now - timestamp > cls.VERIFIER_EXPIRATION:
            return False, f"Code verifier expirado ({now - timestamp} segundos)"
        
        return True, None
    
    @classmethod
    def validate_state(cls, received_state):
        """
        Valida que el state recibido coincida con el almacenado en sesión.
        
        Args:
            received_state: El state recibido en el callback
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if cls.STATE_KEY not in session:
            return False, "No hay state en sesión"
        
        stored_state = session.get(cls.STATE_KEY)
        if stored_state != received_state:
            return False, "El state no coincide"
        
        return True, None
    
    @classmethod
    def clear_session_verifier(cls):
        """Elimina el code_verifier y timestamp de la sesión."""
        if cls.CODE_VERIFIER_KEY in session:
            del session[cls.CODE_VERIFIER_KEY]
        if cls.CODE_VERIFIER_TIMESTAMP_KEY in session:
            del session[cls.CODE_VERIFIER_TIMESTAMP_KEY]
        if cls.STATE_KEY in session:
            del session[cls.STATE_KEY]
    
    @classmethod
    def get_authorization_url(cls, client_id, redirect_uri, code_challenge):
        """
        Construye la URL de autorización de DocuSign con PKCE.
        
        Args:
            client_id: Integration Key de DocuSign
            redirect_uri: URI de redirección registrada en DocuSign
            code_challenge: El code_challenge generado
            
        Returns:
            str: URL de autorización completa
        """
        base_url = f"https://{current_app.config.get('DOCUSIGN_AUTH_SERVER', 'account-d.docusign.com')}/oauth/auth"
        
        # Construir parámetros de query
        params = {
            'response_type': 'code',
            'scope': current_app.config.get('DOCUSIGN_SCOPES', 'signature impersonation openid'),
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': session.get(cls.STATE_KEY, '')
        }
        
        # Construir URL completa
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{base_url}?{query_string}"
        
        current_app.logger.debug(f"URL de autorización: {auth_url}")
        return auth_url
