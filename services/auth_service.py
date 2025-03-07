from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
import time

# Simulación de base de datos en memoria
users_db = {}
failed_attempts = {}
blacklisted_tokens = set()

class AuthService:
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
