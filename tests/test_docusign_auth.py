import pytest
import os
from unittest.mock import patch, MagicMock
from flask import Flask, session
from services.docusign_auth import DocuSignAuth
from services.docusign_pkce import DocuSignPKCE
from datetime import datetime, timedelta

@pytest.fixture
def app():
    """Crear aplicación Flask para pruebas"""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_key',
        'DOCUSIGN_HMAC_KEY': 'test_hmac_key',
        'DOCUSIGN_INTEGRATION_KEY': 'test_integration_key',
        'DOCUSIGN_REDIRECT_URI': 'http://localhost:5000/api/callback'
    })
    return app

@pytest.fixture
def client(app):
    """Crear cliente de pruebas"""
    return app.test_client()

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Configurar variables de entorno para pruebas"""
    env_vars = {
        'DOCUSIGN_INTEGRATION_KEY': 'test_key',
        'DOCUSIGN_USER_ID': 'test_user',
        'DOCUSIGN_AUTH_SERVER': 'test.docusign.com',
        'DOCUSIGN_PRIVATE_KEY_PATH': 'test_key.pem',
        'DOCUSIGN_JWT_LIFETIME': '3600',
        'DOCUSIGN_JWT_SCOPE': 'signature'
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
def auth_service(mock_env_vars):
    return DocuSignAuth()

def test_generate_jwt(auth_service):
    """Prueba la generación del token JWT"""
    with patch('builtins.open', MagicMock()), \
         patch('jwt.encode', return_value='test_jwt'):
        token = auth_service._generate_jwt()
        assert token == 'test_jwt'

def test_get_access_token_success(auth_service):
    """Prueba la obtención exitosa del token de acceso"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "expires_in": 3600
    }

    with patch('requests.post', return_value=mock_response), \
         patch.object(auth_service, '_generate_jwt', return_value='test_jwt'):
        token = auth_service.get_access_token()
        assert token == "test_access_token"

def test_token_expiration(auth_service):
    """Prueba la expiración y renovación del token"""
    with patch.object(auth_service, '_generate_jwt'), \
         patch('requests.post') as mock_post:
        
        # Configurar primera respuesta
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "token1",
            "expires_in": 1
        }
        
        # Obtener primer token
        token1 = auth_service.get_access_token()
        assert token1 == "token1"
        
        # Esperar a que expire
        import time
        time.sleep(2)
        
        # Configurar segunda respuesta
        mock_post.return_value.json.return_value = {
            "access_token": "token2",
            "expires_in": 3600
        }
        
        # El token debería renovarse
        token2 = auth_service.get_access_token()
        assert token2 == "token2"

def test_pkce_generation(app):
    """Prueba la generación de pares PKCE"""
    with app.test_request_context():
        verifier, challenge = DocuSignPKCE.generate_pkce_pair()
        
        assert len(verifier) >= 43  # Min length según spec
        assert len(verifier) <= 128  # Max length según spec
        assert len(challenge) == 43  # Fixed length para SHA256
        assert session.get('code_verifier') == verifier

def test_docusign_auth_flow(app, client):
    """Prueba el flujo completo de autenticación con PKCE"""
    with app.test_request_context():
        # 1. Iniciar flujo de auth
        response = client.get('/api/auth/docusign')
        assert response.status_code == 302
        assert 'code_challenge=' in response.location
        assert 'code_challenge_method=S256' in response.location
        
        # 2. Simular callback
        code_verifier = session.get('code_verifier')
        assert code_verifier is not None
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "expires_in": 3600
            }
            
            response = client.get('/api/callback?code=test_code')
            assert response.status_code == 200
            assert 'code_verifier' not in session
