import pytest
from unittest.mock import patch, MagicMock
import json
import base64
import hashlib
from flask import session, url_for

@pytest.fixture
def mock_docusign_config(app):
    """Fixture para configurar variables de entorno de DocuSign."""
    app.config.update({
        'DOCUSIGN_INTEGRATION_KEY': 'test_integration_key',
        'DOCUSIGN_AUTH_SERVER': 'test.docusign.com',
        'DOCUSIGN_REDIRECT_URI': 'http://localhost:5000/api/docusign/callback',
        'DOCUSIGN_SCOPES': 'signature impersonation',
        'DOCUSIGN_CLIENT_SECRET': 'test_secret'
    })
    return app.config

def test_docusign_auth_redirect(client, mock_docusign_config):
    """Prueba que el endpoint /api/docusign/auth redirige correctamente."""
    # Configurar mock para DocuSignPKCE
    with patch('services.docusign_pkce.DocuSignPKCE.generate_pkce_pair') as mock_generate:
        mock_generate.return_value = ('test_verifier', 'test_challenge')
        
        # Realizar la solicitud
        response = client.get('/api/docusign/auth', follow_redirects=False)
        
        # Verificar redirección
        assert response.status_code == 302
        location = response.headers.get('Location')
        
        # Verificar componentes de la URL
        assert "https://test.docusign.com/oauth/auth" in location
        assert "response_type=code" in location
        assert "client_id=test_integration_key" in location
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A5000%2Fapi%2Fdocusign%2Fcallback" in location
        assert "code_challenge=test_challenge" in location
        assert "code_challenge_method=S256" in location
        
        # Verificar que se llamó a generate_pkce_pair
        mock_generate.assert_called_once()

def test_docusign_auth_error_handling(client):
    """Prueba el manejo de errores en /api/docusign/auth."""
    # Configurar mock para simular un error en generate_pkce_pair
    with patch('services.docusign_pkce.DocuSignPKCE.generate_pkce_pair') as mock_generate:
        mock_generate.side_effect = Exception("Test error")
        
        # Realizar la solicitud
        response = client.get('/api/docusign/auth')
        
        # Verificar respuesta de error
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "details" in data
        assert "Test error" in data["details"]

@patch('routes.api.exchange_code_for_token')
def test_docusign_callback_success(mock_exchange, client, mock_docusign_config):
    """Prueba el éxito del callback de DocuSign."""
    # Configurar mocks
    mock_exchange.return_value = {
        'access_token': 'test_access_token', 
        'refresh_token': 'test_refresh_token',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': 'signature'
    }
    
    with client.session_transaction() as session:
        session['code_verifier'] = 'test_verifier'
        session['code_verifier_timestamp'] = int(pytest.importorskip("time").time())
        session['docusign_oauth_state'] = 'test_state'
    
    # Realizar la solicitud con código de autorización
    response = client.get('/api/docusign/callback?code=test_auth_code&state=test_state')
    
    # Verificar respuesta
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'token_type' in data['data']
    assert 'expires_in' in data['data']
    
    # Verificar que se llamó a exchange_code_for_token con los parámetros correctos
    mock_exchange.assert_called_once_with(
        auth_code='test_auth_code',
        code_verifier='test_verifier',
        redirect_uri=mock_docusign_config['DOCUSIGN_REDIRECT_URI']
    )

@patch('routes.api.DocuSignPKCE.validate_verifier')
def test_docusign_callback_invalid_verifier(mock_validate, client):
    """Prueba el callback con code_verifier inválido."""
    # Configurar mock para simular verifier inválido
    mock_validate.return_value = (False, "Test error")
    
    # Realizar la solicitud
    response = client.get('/api/docusign/callback?code=test_code')
    
    # Verificar respuesta de error
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Test error" in data["details"]

@patch('routes.api.exchange_code_for_token')
def test_docusign_callback_exchange_error(mock_exchange, client, mock_docusign_config):
    """Prueba el manejo de errores en el intercambio de código."""
    # Configurar mocks
    mock_exchange.side_effect = Exception("Exchange error")
    
    with client.session_transaction() as session:
        session['code_verifier'] = 'test_verifier'
        session['code_verifier_timestamp'] = int(pytest.importorskip("time").time())
        session['docusign_oauth_state'] = 'test_state'
    
    # Realizar la solicitud
    response = client.get('/api/docusign/callback?code=test_code&state=test_state')
    
    # Verificar respuesta de error
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "Exchange error" in data["details"]

@patch('routes.api.DocuSignPKCE.validate_state')
def test_docusign_callback_invalid_state(mock_validate_state, client):
    """Prueba el callback con state inválido (protección CSRF)."""
    # Configurar mock para simular state inválido
    mock_validate_state.return_value = (False, "Invalid state")
    
    # Realizar la solicitud
    response = client.get('/api/docusign/callback?code=test_code&state=invalid_state')
    
    # Verificar respuesta de error
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Error de seguridad" in data["error"]
