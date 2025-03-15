import pytest
from unittest.mock import patch, MagicMock
import json
import time
import os
import base64
import hashlib
from pathlib import Path
from flask import session

@pytest.fixture
def docusign_test_env(app):
    """Configura el entorno de prueba para DocuSign."""
    app.config.update({
        'TESTING': True,
        'DOCUSIGN_INTEGRATION_KEY': 'test_key',
        'DOCUSIGN_AUTH_SERVER': 'account-d.docusign.com',
        'DOCUSIGN_REDIRECT_URI': 'http://localhost:5000/api/docusign/callback',
        'DOCUSIGN_BASE_URL': 'https://demo.docusign.net/restapi',
        'DOCUSIGN_SCOPES': 'signature impersonation openid'
    })
    return app

def test_complete_oauth_flow(client, docusign_test_env):
    """
    Prueba el flujo completo de OAuth 2.0 con PKCE, incluyendo:
    1. Inicio del flujo en /api/docusign/auth
    2. Redirección y recepción del callback
    3. Intercambio del código por tokens
    """
    # Paso 1: Iniciar flujo de autorización
    with patch('routes.api.DocuSignPKCE.generate_pkce_pair') as mock_generate:
        # Mock para simular la generación del par PKCE
        test_verifier = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-._~"
        test_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(test_verifier.encode()).digest()
        ).decode().rstrip('=')
        test_state = "test_state_value"
        
        mock_generate.return_value = (test_verifier, test_challenge)
        
        # Capturar la redirección
        with patch('routes.api.redirect') as mock_redirect:
            mock_redirect.return_value = "Redirected"
            
            # Solicitar autorización
            response = client.get('/api/docusign/auth')
            assert response.status_code == 200, "Debería retornar 200 con mock"
            
            # Verificar la llamada a generate_pkce_pair
            mock_generate.assert_called_once()
            
            # Verificar la llamada a redirect con el URL correcto
            mock_redirect.assert_called_once()
            redirect_args = mock_redirect.call_args[0][0]
            
            # Verificar componentes de la URL
            assert "https://account-d.docusign.com/oauth/auth" in redirect_args
            assert "response_type=code" in redirect_args
            assert "client_id=test_key" in redirect_args
            assert f"code_challenge={test_challenge}" in redirect_args
            assert "code_challenge_method=S256" in redirect_args
    
    # Paso 2: Simular callback de DocuSign
    with patch('routes.api.DocuSignPKCE.validate_verifier') as mock_validate_verifier, \
         patch('routes.api.DocuSignPKCE.validate_state') as mock_validate_state, \
         patch('routes.api.exchange_code_for_token') as mock_exchange:
        
        # Configurar mocks
        mock_validate_verifier.return_value = (True, None)
        mock_validate_state.return_value = (True, None)
        mock_exchange.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        # Configurar session para el test
        with client.session_transaction() as session:
            session['code_verifier'] = test_verifier
            session['code_verifier_timestamp'] = int(time.time())
            session['docusign_oauth_state'] = test_state
        
        # Simular callback
        response = client.get(f'/api/docusign/callback?code=test_auth_code&state={test_state}')
        
        # Verificar respuesta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'token_type' in data['data']
        
        # Verificar llamadas a los métodos
        mock_validate_verifier.assert_called_once()
        mock_validate_state.assert_called_once_with(test_state)
        mock_exchange.assert_called_once_with(
            auth_code='test_auth_code',
            code_verifier=test_verifier,
            redirect_uri='http://localhost:5000/api/docusign/callback'
        )
        
        # Verificar que se haya limpiado la sesión
        with client.session_transaction() as session:
            assert 'code_verifier' not in session
            assert 'code_verifier_timestamp' not in session
            assert 'docusign_oauth_state' not in session

def test_exchange_code_for_token(docusign_test_env):
    """Prueba la función que intercambia el código por un token."""
    from routes.api import exchange_code_for_token
    
    with patch('requests.post') as mock_post:
        # Mock de la respuesta de DocuSign
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        # Ejecutar función
        with docusign_test_env.app_context():
            result = exchange_code_for_token(
                auth_code='test_code',
                code_verifier='test_verifier',
                redirect_uri='http://test.com/callback'
            )
            
            # Verificar resultado
            assert result['access_token'] == 'test_access_token'
            assert result['refresh_token'] == 'test_refresh_token'
            
            # Verificar llamada a requests.post
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            
            # Verificar URL de token
            assert args[0] == 'https://account-d.docusign.com/oauth/token'
            
            # Verificar parámetros enviados
            assert kwargs['data']['grant_type'] == 'authorization_code'
            assert kwargs['data']['code'] == 'test_code'
            assert kwargs['data']['client_id'] == 'test_key'
            assert kwargs['data']['redirect_uri'] == 'http://test.com/callback'
            assert kwargs['data']['code_verifier'] == 'test_verifier'

def test_exchange_code_for_token_error(docusign_test_env):
    """Prueba el manejo de errores en el intercambio de código."""
    from routes.api import exchange_code_for_token
    
    with patch('requests.post') as mock_post:
        # Mock de respuesta de error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "invalid_grant", "error_description": "Invalid authorization code"}'
        mock_post.return_value = mock_response
        
        # Ejecutar función y verificar excepción
        with docusign_test_env.app_context():
            with pytest.raises(ValueError) as excinfo:
                exchange_code_for_token(
                    auth_code='invalid_code',
                    code_verifier='test_verifier',
                    redirect_uri='http://test.com/callback'
                )
            
            # Verificar mensaje de error
            assert "Error en token endpoint" in str(excinfo.value)
