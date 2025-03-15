import pytest
import re
import base64
import hashlib
import time
from unittest.mock import patch, MagicMock
from flask import session, url_for
from services.docusign_pkce import DocuSignPKCE

def test_generate_pkce_pair(app):
    """Prueba la generación correcta del par PKCE."""
    with app.test_request_context():
        # Generar el par PKCE
        verifier, challenge = DocuSignPKCE.generate_pkce_pair()
        
        # Verificar que el verifier cumple con las especificaciones
        assert len(verifier) >= 43, f"code_verifier debe tener al menos 43 caracteres, tiene {len(verifier)}"
        assert len(verifier) <= 128, f"code_verifier no debe exceder 128 caracteres, tiene {len(verifier)}"
        
        # Verificar que el verifier solo contiene caracteres permitidos
        allowed_chars_pattern = r'^[A-Za-z0-9\-._~]+$'
        assert re.match(allowed_chars_pattern, verifier), "code_verifier contiene caracteres no permitidos"
        
        # Verificar que el challenge se generó correctamente
        # Recalcular el challenge para confirmar
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip('=')
        
        assert challenge == expected_challenge, "code_challenge no coincide con el esperado"
        
        # Verificar almacenamiento en sesión
        assert 'code_verifier' in session, "code_verifier no se guardó en sesión"
        assert 'code_verifier_timestamp' in session, "timestamp no se guardó en sesión"
        assert 'docusign_oauth_state' in session, "state no se guardó en sesión"
        assert session['code_verifier'] == verifier, "code_verifier en sesión no coincide"

def test_validate_verifier(app):
    """Prueba la validación de code_verifier."""
    with app.test_request_context():
        # Caso 1: Sin code_verifier en sesión
        is_valid, error = DocuSignPKCE.validate_verifier()
        assert not is_valid, "Debería fallar sin code_verifier"
        assert "No hay code_verifier en sesión" in error
        
        # Caso 2: Con code_verifier válido
        _, _ = DocuSignPKCE.generate_pkce_pair()
        is_valid, error = DocuSignPKCE.validate_verifier()
        assert is_valid, "Debería validar con code_verifier válido"
        assert error is None
        
        # Caso 3: Con code_verifier expirado
        session['code_verifier_timestamp'] = int(time.time()) - (DocuSignPKCE.VERIFIER_EXPIRATION + 10)
        is_valid, error = DocuSignPKCE.validate_verifier()
        assert not is_valid, "Debería fallar con code_verifier expirado"
        assert "Code verifier expirado" in error

def test_clear_session_verifier(app):
    """Prueba la limpieza de session verifier."""
    with app.test_request_context():
        # Configurar valores en sesión
        _, _ = DocuSignPKCE.generate_pkce_pair()
        assert 'code_verifier' in session
        assert 'code_verifier_timestamp' in session
        assert 'docusign_oauth_state' in session
        
        # Limpiar sesión
        DocuSignPKCE.clear_session_verifier()
        
        # Verificar que se limpiaron los valores
        assert 'code_verifier' not in session
        assert 'code_verifier_timestamp' not in session
        assert 'docusign_oauth_state' not in session

def test_validate_state(app):
    """Prueba la validación de state para CSRF."""
    with app.test_request_context():
        # Caso 1: Sin state en sesión
        is_valid, error = DocuSignPKCE.validate_state("test_state")
        assert not is_valid
        assert "No hay state en sesión" in error
        
        # Caso 2: State válido
        _, _ = DocuSignPKCE.generate_pkce_pair()
        stored_state = session['docusign_oauth_state']
        is_valid, error = DocuSignPKCE.validate_state(stored_state)
        assert is_valid
        assert error is None
        
        # Caso 3: State inválido
        is_valid, error = DocuSignPKCE.validate_state("invalid_state")
        assert not is_valid
        assert "El state no coincide" in error

def test_get_authorization_url(app):
    """Prueba la generación de URL de autorización."""
    with app.test_request_context():
        # Configurar app para test
        app.config.update({
            'DOCUSIGN_AUTH_SERVER': 'test-server.docusign.com',
            'DOCUSIGN_SCOPES': 'test_scope'
        })
        
        # Generar el par PKCE
        _, challenge = DocuSignPKCE.generate_pkce_pair()
        
        # Generar URL
        url = DocuSignPKCE.get_authorization_url(
            client_id="test_client_id",
            redirect_uri="https://test.com/callback",
            code_challenge=challenge
        )
        
        # Verificar componentes de la URL
        assert "https://test-server.docusign.com/oauth/auth" in url
        assert "response_type=code" in url
        assert "scope=test_scope" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https://test.com/callback" in url
        assert f"code_challenge={challenge}" in url
        assert "code_challenge_method=S256" in url
        assert f"state={session['docusign_oauth_state']}" in url
