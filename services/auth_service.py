import logging
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
import time

# Simulación de base de datos en memoria
users_db = {}
failed_attempts = {}
blacklisted_tokens = set()

class AuthService:
    """Servicio para gestionar la autenticación y tokens JWT"""
    
    # Almacén simple de tokens revocados (en producción, usar Redis o base de datos)
    _blacklisted_tokens = set()
    
    @classmethod
    def register_token(cls, token):
        """
        Registra un token para su seguimiento.
        En una implementación real, esto podría almacenar el token en una base de datos.
        """
        current_app.logger.debug(f"Token registrado: {token[:10]}...")
        # En esta implementación simple, no hacemos nada con el token
        # Este método existe para evitar el error de que no existe el atributo
        return True
    
    @classmethod
    def blacklist_token(cls, jti, expires_delta=None):
        """
        Añade un token a la lista negra para revocarlo.
        
        Args:
            jti: Identificador único del token JWT
            expires_delta: Tiempo hasta que expire (para limpiezas futuras)
        """
        cls._blacklisted_tokens.add(jti)
        current_app.logger.info(f"Token revocado: {jti}")
        return True
    
    @classmethod
    def is_token_blacklisted(cls, jti):
        """
        Verifica si un token está en la lista negra.
        
        Args:
            jti: Identificador único del token JWT
            
        Returns:
            bool: True si el token está revocado
        """
        return jti in cls._blacklisted_tokens
    
    @classmethod
    def clean_blacklist(cls):
        """
        Limpia tokens revocados que ya han expirado.
        En una implementación real, esto se haría periódicamente.
        """
        # En esta implementación simple, simplemente vaciamos la lista
        # En una implementación real, deberíamos verificar las fechas de expiración
        cls._blacklisted_tokens.clear()
        current_app.logger.debug("Lista de tokens revocados limpiada")

    @staticmethod
    def register_user(username: str, password: str) -> dict:
        if username in users_db:
            raise ValueError("Usuario ya existe")
            
        hashed_password = generate_password_hash(password)
        users_db[username] = {
            'password': hashed_password,
            'created_at': time.time()
        }
        
        return {"message": "Usuario registrado exitosamente"}

    @staticmethod
    def login_user(username: str, password: str) -> dict:
        if username in failed_attempts:
            attempts, timestamp = failed_attempts[username]
            if attempts >= current_app.config['MAX_LOGIN_ATTEMPTS']:
                if time.time() - timestamp < current_app.config['LOGIN_TIMEOUT']:
                    raise ValueError("Cuenta bloqueada temporalmente")
                failed_attempts.pop(username)

        if username not in users_db:
            AuthService._record_failed_attempt(username)
            raise ValueError("Usuario o contraseña incorrectos")

        if not check_password_hash(users_db[username]['password'], password):
            AuthService._record_failed_attempt(username)
            raise ValueError("Usuario o contraseña incorrectos")

        # Éxito - generar tokens
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)

        if username in failed_attempts:
            failed_attempts.pop(username)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    @staticmethod
    def logout_user(token: str) -> dict:
        blacklisted_tokens.add(token)
        return {"message": "Sesión cerrada exitosamente"}

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        return token in blacklisted_tokens

    @staticmethod
    def _record_failed_attempt(username: str):
        attempts, _ = failed_attempts.get(username, (0, 0))
        failed_attempts[username] = (attempts + 1, time.time())
