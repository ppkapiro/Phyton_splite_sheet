import pytest
from services.docusign_service import DocuSignService
from unittest.mock import Mock, patch

@pytest.fixture
def mock_docusign():
    """Mock del servicio DocuSign"""
    with patch('services.docusign_service.DocuSignService') as mock:
        yield mock

def test_send_for_signature(client, mock_docusign):
    """Prueba de envío de documento para firma"""
    data = {
        'file': (b'fake pdf content', 'test.pdf'),
        'recipients': ['user1@test.com', 'user2@test.com']
    }
    
    mock_docusign.return_value.send_document_for_signature.return_value = "test-envelope-id"
    
    response = client.post('/api/send_for_signature',  # Prefix /api agregado
        data=data,
        content_type='multipart/form-data')
    
    assert response.status_code == 200
