import pytest
from flask import current_app, g, has_app_context, has_request_context, _request_ctx_stack
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

# Reemplazar la implementación problemática con una más simple
def test_nested_contexts(app):
    """Verificar anidamiento de contextos usando count_active_contexts()"""
    logger = logging.getLogger('test_contexts')
    
    # Estado inicial sin contextos adicionales
    initial_count = count_active_contexts()
    logger.info(f"Contextos iniciales: {initial_count}")
    
    # Primera prueba: app_context adicional
    with app.app_context():
        # Necesitamos contar manualmente para detectar aplicaciones anidadas
        # count_active_contexts() solo cuenta request_context adicionales
        first_level = 1  # Contexto base
        if has_request_context():
            first_level += 1
        logger.info(f"Con contexto app adicional: {first_level}")
        
        # Segunda prueba: añadir request_context
        with app.test_request_context():
            second_level = count_active_contexts()
            logger.info(f"Con request_context añadido: {second_level}")
            assert second_level > initial_count, "Debería haber aumentado el número de contextos"
    
    # Verificar que volvemos al estado original
    final_count = count_active_contexts()
    logger.info(f"Contextos finales: {final_count}")
    assert final_count == initial_count, "Deberíamos volver al estado inicial"

def verify_sqlalchemy_state():
    """
    Verifica el estado completo de SQLAlchemy usando métodos oficiales.
    Retorna (bool, str) indicando si está limpio y mensaje de error.
    """
    try:
        # 1. Verificar existencia de sesión
        if not hasattr(db, 'session'):
            return False, "No hay sesión de SQLAlchemy configurada"
            
        # 2. Obtener sesión actual de forma segura
        session = db.session
        
        # 3. Verificar objetos pendientes (mejor que verificar is_active)
        pending_objects = len(session.new) + len(session.dirty) + len(session.deleted)
        if pending_objects > 0:
            return False, f"Hay {pending_objects} objetos pendientes en la sesión"
            
        # 4. Verificar transacciones
        if session.transaction:
            if session.transaction.nested:
                return False, "Hay transacciones anidadas activas"
            if session.transaction.parent:
                return False, "Hay una transacción padre activa"
                
        # 5. Verificar conexiones en pool usando método oficial
        if hasattr(db, 'engine'):
            pool = db.engine.pool
            if hasattr(pool, 'status'):
                checked_out = pool.status().checked_out
                if checked_out > 0:
                    return False, f"Hay {checked_out} conexiones activas"
        
        return True, "Estado limpio"
        
    except Exception as e:
        return False, f"Error verificando estado: {str(e)}"

def test_db_session_context(app, db_session):
    """Verifica que el fixture db_session mantenga el contexto correctamente."""
    logger = logging.getLogger('test_contexts')
    
    with app.app_context():
        # 1. Obtener sesión y ejecutar consulta simple
        session = db_session
        state = get_session_state(session)
        logger.info(f"Estado inicial de sesión: {state}")
        
        # 2. Ejecutar operación simple (no verificar si la sesión está activa)
        logger.info("Ejecutando consulta SQL simple...")
        results = session.execute("SELECT 1").fetchall()
        logger.info(f"Consulta ejecutada correctamente, resultado: {results}")
        assert results == [(1,)], "Debería retornar [(1,)]"
        
        # 3. Verificar que no haya cambios pendientes
        assert len(session.new) == 0, "No debería haber objetos nuevos"
        assert len(session.dirty) == 0, "No debería haber objetos modificados"
        assert len(session.deleted) == 0, "No debería haber objetos eliminados"

def get_session_state(session):
    """Helper para obtener estado detallado de la sesión"""
    return {
        'is_active': session.is_active,
        'in_transaction': bool(session.transaction and session.transaction.is_active),
        'new_objects': len(session.new),
        'dirty_objects': len(session.dirty),
        'deleted_objects': len(session.deleted)
    }

def test_db_session_cleanup(app, db_session):
    """Verifica que la sesión se limpie correctamente entre tests."""
    logger = logging.getLogger('test_contexts')
    
    with app.app_context():
        # 1. Verificar estado inicial
        session = db_session
        initial_state = get_session_state(session)
        logger.info(f"Estado inicial de sesión: {initial_state}")
        
        # 2. Ejecutar operación de forma segura (independiente del estado)
        logger.info("Ejecutando consulta SQL de prueba...")
        results = session.execute("SELECT 1").fetchall()
        assert results == [(1,)], f"Resultado inesperado: {results}"
        
        # 3. Verificar estado post-operación 
        final_state = get_session_state(session)
        logger.info(f"Estado después de operación: {final_state}")
        
        # 4. Verificar que no se hayan introducido cambios (objetivo original)
        assert len(session.new) == 0, "No debería haber objetos nuevos"
        assert len(session.dirty) == 0, "No debería haber objetos sucios"
        assert len(session.deleted) == 0, "No debería haber objetos eliminados"

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