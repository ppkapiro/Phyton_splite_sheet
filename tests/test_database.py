import pytest
from models.database import add_user, add_agreement, get_user, get_agreement
from models.user import User
from models.agreement import Agreement

def test_add_user(app):
    """Prueba de creación de usuario en la BD"""
    with app.app_context():
        user = add_user('testuser', 'testpass')
        assert user.username == 'testuser'
        assert user.check_password('testpass')

def test_add_agreement(app):
    """Prueba de creación de acuerdo"""
    with app.app_context():
        # Crear usuario primero
        user = add_user('testuser', 'testpass')
        
        # Crear acuerdo
        agreement = add_agreement(
            title="Test Agreement",
            participants=[user],
            pdf_url="http://example.com/test.pdf"
        )
        
        assert agreement.title == "Test Agreement"
        assert len(agreement.participants) == 1
        assert agreement.signature_status == "pending"
