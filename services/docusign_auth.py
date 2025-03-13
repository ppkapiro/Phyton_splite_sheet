import os
import jwt
import time
import requests
import logging
from flask import current_app
from datetime import datetime, timedelta
from typing import Optional

class DocuSignAuth:
    """Gestiona la autenticación con DocuSign usando OAuth 2.0 con JWT"""
    
    def __init__(self):
        self._token: Optional[str] = None
        self._token_expiration: float = 0
        self._jwt_token: Optional[str] = None
        self.logger = logging.getLogger(__name__)

    def _generate_jwt(self) -> str:
        """Genera un token JWT firmado con la clave privada RSA"""
        try:
            with open(os.getenv('DOCUSIGN_PRIVATE_KEY_PATH'), "r") as key_file:
                private_key = key_file.read()

            jwt_payload = {
                "iss": os.getenv('DOCUSIGN_INTEGRATION_KEY'),
                "sub": os.getenv('DOCUSIGN_USER_ID'),
                "aud": os.getenv('DOCUSIGN_AUTH_SERVER'),
                "iat": int(time.time()),
                "exp": int(time.time()) + int(os.getenv('DOCUSIGN_JWT_LIFETIME', 3600)),
                "scope": os.getenv('DOCUSIGN_JWT_SCOPE', 'signature impersonation')
            }

            self._jwt_token = jwt.encode(
                jwt_payload, 
                private_key, 
                algorithm="RS256"
            )
            return self._jwt_token

        except Exception as e:
            self.logger.error(f"Error generando JWT: {str(e)}")
            raise ValueError("No se pudo generar el token JWT") from e

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Obtiene un token de acceso válido"""
        if current_app.config.get('TESTING'):
            # En modo testing, retornar token de prueba
            return "test_token"
            
        """
        Obtiene un token de acceso válido, generando uno nuevo si es necesario
        
        Args:
            force_refresh: Si es True, fuerza la generación de un nuevo token
            
        Returns:
            str: Token de acceso válido
        """
        current_time = time.time()

        # Verificar si necesitamos un nuevo token
        if (not self._token or 
            current_time >= self._token_expiration or 
            force_refresh):
            
            try:
                jwt_token = self._generate_jwt()
                auth_url = (f"https://{current_app.config['DOCUSIGN_AUTH_SERVER']}"
                          f"/oauth/token")
                
                response = requests.post(
                    auth_url,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": jwt_token
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    self._token = data["access_token"]
                    # Restar 60 segundos para renovar antes de que expire
                    self._token_expiration = (
                        current_time + data["expires_in"] - 60
                    )
                    
                    self.logger.info(
                        "Nuevo token de acceso generado, expira en: %s",
                        datetime.fromtimestamp(self._token_expiration)
                    )
                else:
                    self.logger.error(
                        "Error obteniendo token: %s - %s",
                        response.status_code,
                        response.text
                    )
                    raise ValueError(
                        f"Error en autenticación DocuSign: {response.text}"
                    )

            except Exception as e:
                self.logger.error("Error en get_access_token: %s", str(e))
                raise

        return self._token

    def refresh_token(self) -> str:
        """Fuerza la actualización del token de acceso"""
        return self.get_access_token(force_refresh=True)

    @property
    def token_valid_for(self) -> timedelta:
        """Retorna el tiempo restante de validez del token"""
        if not self._token:
            return timedelta(0)
        return timedelta(seconds=max(0, self._token_expiration - time.time()))
