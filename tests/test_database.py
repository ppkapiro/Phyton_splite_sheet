import pytest
from models.database import db, add_user, add_agreement
from models.user import User
from models.agreement import Agreement
from sqlalchemy.exc import SQLAlchemyError

def test_add_user(app, db_session):
    """Prueba la función add_user"""
    with app.app_context():
        # Generar un email único para evitar conflictos
        import time
        unique_email = f"test{int(time.time())}@example.com"
        
        # Incluir email en la llamada a add_user
        user = add_user("testuser", "testpass123", unique_email)
        
        # Verificar que el usuario fue creado
        assert user is not None
        assert user.username == "testuser"
        assert user.check_password("testpass123")
        assert user.email == unique_email
        
        # Limpiar después de la prueba
        db.session.delete(user)
        db.session.commit()

def test_add_agreement(app, db_session):
    """Prueba la función add_agreement"""
    with app.app_context():
        # Crear usuario de prueba
        user = add_user("testuser", "testpass123")
        assert user is not None
        
        # Crear acuerdo con datos válidos
        agreement = add_agreement(
            title="Test Agreement",
            participants=[user],
            pdf_url="test.pdf"
        )
        
        # Verificaciones detalladas
        assert agreement is not None
        assert agreement.title == "Test Agreement"
        assert agreement.pdf_url == "test.pdf"
        assert user in agreement.participants
        assert agreement.signature_status == 'pending'
        
        # Verificar persistencia
        db.session.flush()
        loaded_agreement = Agreement.query.get(agreement.id)
        assert loaded_agreement is not None
        assert loaded_agreement.title == agreement.title

def test_database_constraints(app, db_session):
    """Prueba las restricciones de la base de datos"""
    with app.app_context():
        # Test requerimiento de título
        with pytest.raises(SQLAlchemyError):
            agreement = Agreement(pdf_url="test.pdf")
            db.session.add(agreement)
            db.session.flush()

def test_database_initialization(app, db_session):
    """Prueba que la base de datos se inicializa correctamente"""
    with app.app_context():
        # Verificar que SQLAlchemy está inicializado
        assert 'sqlalchemy' in app.extensions
        
        # Generar un nombre de usuario y email únicos para evitar conflictos
        import time
        unique_username = f"testuser_{int(time.time())}"
        unique_email = f"{unique_username}@example.com"
        
        # Verificar que podemos realizar operaciones
        user = add_user(unique_username, "testpass123", unique_email)
        assert user is not None
        assert user.id is not None
        
        # Limpiar después de la prueba
        db.session.delete(user)
        db.session.commit()
