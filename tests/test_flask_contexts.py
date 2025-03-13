import pytest
from flask import _app_ctx_stack, current_app
from models.database import db

def test_context_count(app):
    """Verifica que no haya fugas de contexto"""
    # Verificar estado inicial
    assert len(_app_ctx_stack._stack) <= 1, (
        f"Demasiados contextos activos: {len(_app_ctx_stack._stack)}"
    )

    with app.test_request_context():
        # Durante el request
        assert len(_app_ctx_stack._stack) == 1, "Debería haber exactamente 1 contexto"
        assert current_app == app, "La aplicación actual no coincide"
        
        # Verificar SQLAlchemy
        assert 'sqlalchemy' in app.extensions, "SQLAlchemy no está inicializado"
        assert db.get_app() == app, "SQLAlchemy no está vinculado a la app correcta"

    # Después del request
    assert len(_app_ctx_stack._stack) <= 1, "El contexto no se liberó correctamente"

def test_nested_contexts(app):
    """Verifica el comportamiento con contextos anidados"""
    initial_stack = len(_app_ctx_stack._stack)
    
    with app.app_context():
        first_level = len(_app_ctx_stack._stack)
        assert first_level == initial_stack + 1, "Primer nivel incorrecto"
        
        with app.test_request_context():
            second_level = len(_app_ctx_stack._stack)
            assert second_level == first_level + 1, "Segundo nivel incorrecto"
            
        assert len(_app_ctx_stack._stack) == first_level, "Contexto interno no liberado"
        
    assert len(_app_ctx_stack._stack) == initial_stack, "Contexto externo no liberado"

def test_db_session_context(app, db_session):
    """Verifica que el fixture db_session mantenga el contexto correctamente"""
    assert current_app == app, "Sin contexto de aplicación"
    assert db.get_app() == app, "SQLAlchemy no está vinculado"
    
    # Verificar que podemos usar la sesión
    assert db.session is not None
    assert not db.session.is_active, "La sesión no debería estar activa aún"
    
    # Realizar una operación
    with db.session.begin():
        assert db.session.is_active, "La sesión debería estar activa"
        
    assert not db.session.is_active, "La sesión no se cerró correctamente"

@pytest.fixture
def check_contexts():
    """Fixture para verificar contextos antes y después de cada test"""
    initial_count = len(_app_ctx_stack._stack)
    yield
    final_count = len(_app_ctx_stack._stack)
    assert final_count == initial_count, (
        f"Fuga de contexto detectada: {final_count - initial_count} "
        "contextos no liberados"
    )
