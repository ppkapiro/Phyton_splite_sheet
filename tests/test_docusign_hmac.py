import pytest
import hmac
import hashlib
import base64
from services.docusign_hmac import DocuSignHMACValidator
from unittest.mock import MagicMock
from flask import Flask
from werkzeug.exceptions import Forbidden

def create_mock_request(payload: bytes, signature: str, timestamp: str) -> MagicMock:
    """Crea un mock de Request de Flask para testing"""
    mock_request = MagicMock()
    mock_request.headers = {
        'X-DocuSign-Signature-1': signature,
        'X-DocuSign-Signature-Timestamp': timestamp
    }
    mock_request.get_data.return_value = payload
    return mock_request

def test_hmac_validation_success():
    """Prueba validación HMAC exitosa"""
    # Configurar
    hmac_key = "test_key"
    payload = b'{"test": "data"}'
    timestamp = "2024-03-14T12:00:00Z"
    
    # Calcular firma válida
    message = timestamp.encode('utf-8') + b'\n' + payload + b'\n'
    signature = base64.b64encode(
        hmac.new(
            hmac_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).digest()
    ).decode()
    
    # Crear request mock
    mock_request = create_mock_request(payload, signature, timestamp)
    
    # Validar
    validator = DocuSignHMACValidator(hmac_key)
    is_valid, error = validator.validate_request(mock_request)
    
    assert is_valid
    assert error == ""

def test_hmac_validation_invalid_signature():
    """Prueba validación HMAC con firma inválida"""
    validator = DocuSignHMACValidator("test_key")
    mock_request = create_mock_request(
        b'{"test": "data"}',
        "invalid_signature",
        "2024-03-14T12:00:00Z"
    )
    
    is_valid, error = validator.validate_request(mock_request)
    
    assert not is_valid
    assert "Firma HMAC inválida" in error

def test_hmac_validation_integration(app):
    """Prueba integración completa de validación HMAC"""
    with app.test_request_context():
        app.config['DOCUSIGN_HMAC_KEY'] = 'test_key'
        
        # Crear datos de prueba
        payload = b'{"test": "data"}'
        timestamp = "2024-03-14T12:00:00Z"
        message = timestamp.encode('utf-8') + b'\n' + payload + b'\n'
        
        # Calcular firma válida
        signature = base64.b64encode(
            hmac.new(
                b'test_key',
                message,
                hashlib.sha256
            ).digest()
        ).decode()
        
        # Simular request
        with app.test_client() as client:
            response = client.post(
                '/api/docusign/webhook',
                data=payload,
                headers={
                    'X-DocuSign-Signature-1': signature,
                    'X-DocuSign-Signature-Timestamp': timestamp,
                    'Content-Type': 'application/json'
                }
            )
            
            assert response.status_code == 200

def test_hmac_validation_invalid_signature(app):
    """Prueba rechazo de firma inválida"""
    with app.test_request_context():
        app.config['DOCUSIGN_HMAC_KEY'] = 'test_key'
        
        with app.test_client() as client:
            response = client.post(
                '/api/docusign/webhook',
                json={'test': 'data'},
                headers={
                    'X-DocuSign-Signature-1': 'invalid_signature',
                    'X-DocuSign-Signature-Timestamp': '2024-03-14T12:00:00Z'
                }
            )
            
            assert response.status_code == 403
