import pytest
from flask import current_app, g, has_app_context, has_request_context, _app_ctx_stack
from models.database import db
import logging

def count_active_contexts():
    """
    Cuenta contextos activos usando métodos oficiales de Flask 2.x+
    
    Returns:
        int: Número total de contextos activos 
             (1 para app_context, +1 si hay request_context)
    """
    count = 0
    
    # Verificar contexto de aplicación
    if has_app_context():
        count += 1
        current_app.logger.debug("Contexto de aplicación activo")
    
    # Verificar contexto de request
    if has_request_context():
        count += 1
        current_app.logger.debug("Contexto de request activo")
    
    return count

@pytest.fixture(autouse=True)
def ensure_clean_context(app):
    """
    Fixture que asegura un contexto limpio antes y después de cada test.
    """
    # 1. Guardar estado inicial
    initial_has_app_ctx = has_app_context()
    initial_has_req_ctx = has_request_context()
    
    yield
    
    # 2. Verificar y limpiar después del test
    if has_request_context() != initial_has_req_ctx:
        current_app.logger.warning("Detectada fuga de request context")
        while has_request_context():
            ctx = current_app._request_ctx_stack.top
            if ctx is not None:
                ctx.pop()
                
    if has_app_context() != initial_has_app_ctx:
        current_app.logger.warning("Detectada fuga de app context")
        while has_app_context():
            ctx = current_app._app_ctx_stack.top
            if ctx is not None:
                ctx.pop()

@pytest.mark.usefixtures('base_app_context')
def test_context_count(app):
    """Verifica la cuenta de contextos"""
    logger = logging.getLogger('test_contexts')
    
    # Estado inicial: solo el contexto base
    initial_contexts = count_active_contexts()
    logger.info(f"Contextos iniciales: {initial_contexts}")
    assert initial_contexts == 1, "Debería haber exactamente un contexto base"
    
    # Verificar con request context
    with app.test_request_context():
        current_contexts = count_active_contexts()
        logger.info(f"Contextos con request: {current_contexts}")
        assert current_contexts == 2, "Debería haber dos contextos (base + request)"
    
    # Verificar estado final
    final_contexts = count_active_contexts()
    logger.info(f"Contextos finales: {final_contexts}")
    assert final_contexts == 1, "Debería volver a un solo contexto base"

def test_nested_contexts(app):
    """Verifica el comportamiento con contextos anidados"""
    base_count = count_active_contexts()
    assert base_count == 0, "No debería haber contextos al inicio"
    
    with app.app_context():
        first_level = count_active_contexts()
        assert first_level == 1, "Debería haber un app_context"
        
        with app.test_request_context():
            second_level = count_active_contexts()
            assert second_level == 2, "Deberían haber dos contextos"
            
        assert count_active_contexts() == 1, "Debería volver a un contexto"
        
    assert count_active_contexts() == 0, "No deberían quedar contextos"

def verify_sqlalchemy_state():
    """
    Verifica el estado completo de SQLAlchemy.
    Retorna (bool, str) indicando si está limpio y mensaje de error.
    """
    try:
        # 1. Verificar sesión activa
        if db.session.is_active:
            return False, "Sesión activa encontrada"
            
        # 2. Verificar sesiones en registro global
        if len(db.session.registry._scoped_sessions) > 0:
            return False, f"Hay {len(db.session.registry._scoped_sessions)} sesiones en registro"
            
        # 3. Verificar conexiones en pool
        if hasattr(db, 'engine'):
            pool = db.engine.pool
            if pool.checkedout() > 0:
                return False, f"Hay {pool.checkedout()} conexiones activas"
                
        # 4. Verificar transacciones
        if db.session.transaction.nested:
            return False, "Hay transacciones anidadas"
            
        if db.session.transaction.parent:
            return False, "Hay una transacción padre activa"
            
        return True, "Estado limpio"
        
    except Exception as e:
        return False, f"Error verificando estado: {str(e)}"

def test_db_session_context(app, db_session):
    """Verifica que el fixture db_session mantenga el contexto correctamente"""
    logger = logging.getLogger('test_contexts')
    
    with app.app_context():
        # Verificar estado inicial
        is_clean, message = verify_sqlalchemy_state()
        logger.info(f"Estado inicial de SQLAlchemy: {message}")
        assert is_clean, f"Estado inicial sucio: {message}"
        
        # Realizar operación
        with db.session.begin():
            assert db.session.is_active
            # ... test operations ...
            
        # Verificar limpieza después de operación
        is_clean, message = verify_sqlalchemy_state()
        assert is_clean, f"Estado final sucio: {message}"

def test_db_session_cleanup(app, db_session):
    """Verifica que la sesión se limpie correctamente entre tests"""
    logger = logging.getLogger('test_contexts')
    
    with app.app_context():
        # 1. Verificar estado inicial de SQLAlchemy
        logger.info("Verificando estado inicial de SQLAlchemy...")
        assert hasattr(db, 'session'), "No hay sesión de SQLAlchemy"
        assert not db.session.is_active, "La sesión no debería estar activa"
        
        # 2. Verificar registro de sesiones
        logger.info("Verificando registro de sesiones...")
        assert len(db.session.registry._scoped_sessions) == 0, (
            f"Hay {len(db.session.registry._scoped_sessions)} sesiones activas"
        )
        
        # 3. Verificar estado de transacciones
        logger.info("Verificando estado de transacciones...")
        assert not db.session.transaction.nested, "Hay transacciones anidadas"
        assert not db.session.transaction.parent, "Hay una transacción padre"
        
        # 4. Intentar operaciones CRUD
        logger.info("Probando operaciones CRUD...")
        with db.session.begin():
            assert db.session.is_active, "La sesión debería estar activa en la transacción"
            # Realizar operación de prueba
            
        assert not db.session.is_active, "La sesión debería estar inactiva después"
        
        # 5. Verificar limpieza después de error
        logger.info("Verificando manejo de errores...")
        try:
            with db.session.begin():
                raise Exception("Error de prueba")
        except:
            pass
        
        assert not db.session.is_active, "La sesión debería estar inactiva tras error"
        
        # 6. Verificar estado final
        logger.info("Verificando estado final...")
        assert len(db.session.registry._scoped_sessions) == 0, "Hay sesiones residuales"

@pytest.fixture
def check_contexts():
    """Fixture para verificar contextos antes y después de cada test"""
    initial_count = count_active_contexts()
    yield
    final_count = count_active_contexts()
    assert final_count == initial_count, (
        f"Fuga de contexto detectada: {final_count - initial_count} "
        "contextos no liberados"
    )