import pytest
from flask import json, jsonify
from unittest.mock import patch, MagicMock
from services.docusign_service import DocuSignService

@patch('services.docusign_service.DocuSignService.create_instance')
def test_send_for_signature(mock_create_instance, client, app):
    """Prueba el envío de documento para firma"""
    with app.test_request_context():
        # Configurar mock del servicio
        mock_service = MagicMock()
        mock_service.send_document_for_signature.return_value = {
            "envelope_id": "test_env_123",
            "status": "sent",
            "status_datetime": "2024-03-14T12:00:00Z"
        }
        mock_create_instance.return_value = mock_service

        # Datos de prueba válidos
        test_data = {
            "document_id": "test_doc_123",
            "recipient_email": "test@example.com",
            "recipient_name": "John Doe"
        }

        # Asegurarse de que la ruta use DocuSignService.create_instance()
        response = client.post(
            '/api/docusign/send_for_signature',  # Actualizar la ruta
            json=test_data,
            content_type='application/json'
        )

        # Verificaciones
        mock_create_instance.assert_called_once()
        mock_service.send_document_for_signature.assert_called_once()
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["data"]["envelope_id"] == "test_env_123"

def test_send_for_signature_invalid_data(client):
    """Prueba el envío con datos inválidos"""
    # Test con datos vacíos
    response = client.post(
        '/api/docusign/send_for_signature',  # Ruta corregida
        json={},
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "details" in data

    # Test con datos parciales
    response = client.post(
        '/api/docusign/send_for_signature',  # Ruta corregida
        json={"document_id": "test_123"},
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "details" in data

@patch('services.docusign_service.DocuSignService.create_instance')
def test_send_for_signature_service_error(mock_create_instance, client, app):
    """Prueba manejo de error del servicio DocuSign"""
    with app.test_request_context():
        # Configurar mock para lanzar error
        mock_service = MagicMock()
        mock_service.send_document_for_signature.side_effect = Exception("DocuSign API Error")
        mock_create_instance.return_value = mock_service

        test_data = {
            "document_id": "test_doc_123",
            "recipient_email": "test@example.com",
            "recipient_name": "John Doe"
        }

        response = client.post(
            '/api/docusign/send_for_signature',  # Ruta corregida
            json=test_data,
            content_type='application/json'
        )

        # Verificaciones
        mock_create_instance.assert_called_once()
        mock_service.send_document_for_signature.assert_called_once()
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "details" in data
        assert "DocuSign API Error" in str(data["details"])
