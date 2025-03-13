import pytest
from unittest.mock import patch, MagicMock
import json
from flask import session
from datetime import datetime, timedelta
import time

def test_docusign_callback_success(client, app):
    """Prueba el callback exitoso de DocuSign"""
    mock_response = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    
    with app.test_request_context():
        # Configuración completa
        app.config.update({
            'DOCUSIGN_AUTH_SERVER': 'account-d.docusign.com',
            'DOCUSIGN_TOKEN_URL': 'https://account-d.docusign.com/oauth/token',
            'DOCUSIGN_REDIRECT_URI': 'http://localhost:5000/api/callback',
            'DOCUSIGN_INTEGRATION_KEY': 'test_key',
            'DOCUSIGN_CLIENT_SECRET': 'test_secret',
            'DOCUSIGN_HMAC_KEY': 'test_hmac_key'
        })
        
        # Configurar sesión con code_verifier válido
        with client.session_transaction() as sess:
            sess['code_verifier'] = 'test_verifier'
            sess['code_verifier_timestamp'] = datetime.utcnow().timestamp() - 60
        
        # Mock de requests.post
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                text='Success'
            )
            
            response = client.get('/api/callback?code=test_auth_code')
            
            # Verificaciones
            assert mock_post.call_count == 1
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["data"]["access_token"] == mock_response["access_token"]

def test_docusign_callback_no_code(client):
    """Prueba el callback sin código de autorización"""
    response = client.get('/api/callback')
    assert response.status_code == 400
    assert b"No se recibi" in response.data

def test_docusign_callback_expired_verifier(client, app):
    """Prueba el callback con code_verifier expirado"""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['code_verifier'] = 'test_verifier'
            # Establecer timestamp expirado (35 minutos atrás)
            sess['code_verifier_timestamp'] = time.time() - 2100
        
        response = client.get('/api/callback?code=test_auth_code')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "code_verifier expirado" in data["error"]

def test_docusign_callback_invalid_token_response(client, app):
    """Prueba el callback con respuesta inválida del token endpoint"""
    with app.test_request_context():
        app.config['DOCUSIGN_INTEGRATION_KEY'] = 'test_key'
        app.config['DOCUSIGN_CLIENT_SECRET'] = 'test_secret'
        
        with client.session_transaction() as sess:
            sess['code_verifier'] = 'test_verifier'
            sess['code_verifier_timestamp'] = datetime.utcnow().timestamp() - 60
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=400,
                text="Invalid grant"
            )
            
            response = client.get('/api/callback?code=test_auth_code')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "Error obteniendo token" in data["error"]
