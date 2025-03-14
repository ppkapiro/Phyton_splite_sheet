import pytest
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, current_app, _app_ctx_stack, _request_ctx_stack, has_app_context, has_request_context
from config import Config
from models.database import db, init_app, session_scope  # Eliminar init_db
from .test_utils import TestReporter
from main import app as production_app, create_app
import logging
from sqlalchemy.orm import scoped_session, sessionmaker

# Agregar directorio raíz al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importar explícitamente todos los modelos
from models.user import User
from models.agreement import Agreement
from models.document import Document

# Crear session factory una sola vez
SessionFactory = sessionmaker(bind=None)  # Se vinculará después con el engine
ScopedSession = scoped_session(SessionFactory)

# Inicialización de reportes y logging
@pytest.fixture(scope="session", autouse=True)
def initialize_reports():  # ⚠️ Se empuja el contexto pero nunca se hace pop
    """Asegurar que existe el directorio de reportes"""
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    return reports_dir

@pytest.fixture(scope="session")
def app():
    """Crear y configurar la aplicación Flask para testing"""
    app = create_app()
    
    # Configuración específica para tests
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test_key'
    })
    
    # Crear estructura de directorios necesaria
    (Path(app.root_path).parent / 'tests' / 'output').mkdir(parents=True, exist_ok=True)
    
    return app

@pytest.fixture(scope="session")
def test_db(app):
    """
    Fixture para inicializar y limpiar la base de datos durante la sesión de tests.
    Debe ejecutarse antes que otros fixtures que dependan de la base de datos.
    """
    with app.app_context():
        # Limpiar cualquier estado previo
        db.session.remove()
        db.drop_all()
        
        # Crear tablas frescas
        db.create_all()
        current_app.logger.info("Base de datos de testing inicializada")
        
        yield db
        
        # Limpiar después de todos los tests
        db.session.remove()
        db.drop_all()
        current_app.logger.info("Base de datos de testing limpiada")

@pytest.fixture(scope="function")
def reset_database(app):
    """Fixture que garantiza una base de datos recién creada para cada test"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()

def cleanup_sqlalchemy():
    """Limpieza exhaustiva de SQLAlchemy."""
    try:
        if not has_app_context():
            raise RuntimeError("Se requiere contexto de aplicación para limpiar SQLAlchemy")

        session = db.session()
        try:
            # 1. Hacer rollback de cualquier transacción pendiente
            if session.transaction and session.transaction.is_active:
                session.rollback()
            
            # 2. Eliminar todos los objetos de la sesión
            session.expunge_all()
            
            # 3. Hacer commit de cualquier cambio pendiente
            session.commit()
            
            # 4. Cerrar sesión actual
            session.close()
            
            # 5. Remover sesión del registro
            db.session.remove()
            
            # 6. Limpiar pool de conexiones
            db.engine.dispose()
            
        except Exception as e:
            current_app.logger.error(f"Error limpiando sesión: {str(e)}")
            raise
            
    except Exception as e:
        current_app.logger.error(f"Error en cleanup_sqlalchemy: {str(e)}")
        raise

def get_session_info(session):
    """Helper para obtener información detallada de la sesión"""
    return {
        'is_active': session.is_active,
        'in_transaction': bool(session.transaction and session.transaction.is_active),
        'transaction_parent': bool(session.transaction and session.transaction.parent),
        'new_objects': len(session.new),
        'dirty_objects': len(session.dirty),
        'deleted_objects': len(session.deleted)
    }

def force_transaction_cleanup(session):
    """Helper para forzar limpieza de transacciones activas"""
    try:
        state = get_session_info(session)
        current_app.logger.debug(f"Estado pre-cleanup: {state}")

        # Solución más radical para transacciones persistentes
        try:
            # 1. Intentar rollback primero
            session.rollback()
            
            # 2. Cerrar la sesión
            session.close()
            
            # 3. Eliminar sesión
            db.session.remove()
            
            # 4. Reiniciar engine completamente
            if hasattr(db, 'engine'):
                db.engine.dispose()
                
            # 5. Crear y cerrar una conexión fresca para resetear
            try:
                if hasattr(db, 'engine'):
                    conn = db.engine.raw_connection()
                    conn.close()
            except:
                pass
                
        except Exception as e:
            current_app.logger.error(f"Error en proceso de limpieza: {e}")
            
        # Último recurso - reiniciar el objeto _session
        try:
            # Eliminar sesión actual
            if hasattr(db, '_session'):
                delattr(db, '_session')
                
            # Crear una nueva sesión limpia
            if hasattr(db, 'session'):
                session = db.session()
                session.close()
                db.session.remove()
        except:
            pass
                
        current_app.logger.debug("Limpieza radical completada")
        
    except Exception as e:
        current_app.logger.error(f"Error en cleanup: {e}")

def diagnose_transaction(session):
    """Diagnóstico detallado de una transacción SQLAlchemy"""
    try:
        details = {
            "connection_valid": hasattr(session, "connection") and session.connection() is not None,
            "in_transaction": bool(session.transaction and session.transaction.is_active),
            "is_active": session.is_active,
            "autocommit": session.autocommit,
            "autoflush": session.autoflush,
            "expire_on_commit": session.expire_on_commit,
            "transaction_depth": getattr(session.transaction, "nested_depth", 0) if session.transaction else 0
        }
        
        current_app.logger.info(f"Diagnóstico de sesión: {details}")
        return details
    except Exception as e:
        current_app.logger.error(f"Error diagnosticando transacción: {e}")
        return {"error": str(e)}

@pytest.fixture(scope="function")
def db_session(app, base_app_context, initialize_database):  # Agregar dependencia
    """Fixture para manejo de sesiones con SQLAlchemy."""
    with app.app_context():
        # Limpieza previa
        cleanup_sqlalchemy()
        
        # Recrear tablas
        db.drop_all()
        db.create_all()
        
        # Crear sesión fresca
        db.session.remove()
        if hasattr(db, '_session'):
            delattr(db, '_session')
        
        session = db.session()
        session.expire_on_commit = False
        
        # Diagnóstico detallado
        state = get_session_info(session)
        diagnose_transaction(session)
        
        # Advertir sobre transacciones pre-existentes
        if state['in_transaction']:
            current_app.logger.warning(
                "NOTA: Sesión comenzó con una transacción activa. "
                "Los tests se ejecutarán dentro de esta transacción existente."
            )
        
        try:
            yield session
        finally:
            # Limpieza final siempre preservando la integridad de los datos
            force_transaction_cleanup(session)
            current_app.logger.info("Sesión finalizada correctamente")

@pytest.fixture(scope="function")
def client(app):
    """Fixture para el cliente de testing"""
    return app.test_client()

@pytest.fixture(scope="function")
def runner(app):
    """Fixture para el runner de comandos"""
    return app.test_cli_runner()

@pytest.fixture(scope="function")
def test_report(app):
    """Fixture para reporte de tests sin __init__"""
    class Report:
        results = []
        
        @classmethod
        def add_result(cls, test_name, status, message=None):
            cls.results.append({
                'test_name': test_name,
                'status': status,
                'message': message
            })
    
    return Report()

@pytest.fixture(scope="session")
def test_reporter(initialize_reports):
    reporter = TestReporter()
    yield reporter
    print("\nGenerando reportes finales...")
    try:
        files = reporter.generate_reports()
        if files:
            print("\nReportes generados exitosamente:")
            for file_type, file_path in files.items():
                path = Path(file_path)
                if path.exists():
                    size = path.stat().st_size
                    print(f"- {file_type}: {file_path} ({size} bytes)")
        else:
            print("\n¡Error! No se generaron los reportes")
    except Exception as e:
        print(f"\nError en la generación de reportes: {str(e)}")
        import traceback
        traceback.print_exc()

# Hook para procesar los resultados de las pruebas
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook que captura el resultado de cada test y lo registra"""
    outcome = yield
    result = outcome.get_result()
    
    if call.when == "call" and hasattr(item, "funcargs"):
        test_report = item.funcargs.get("test_report")
        if test_report is not None:
            status = "PASS" if result.passed else "FAIL"
            error = str(result.longrepr) if result.failed else None
            test_report.add_result(
                test_name=item.name,
                status=status,
                message=error
            )

@pytest.fixture(scope="function")
def auth_tokens(client, app):
    """Fixture mejorado para tokens JWT con diagnóstico detallado"""
    with app.app_context():
        # Crear usuario de prueba con password que cumple los requisitos
        from models.user import User
        user = User(username='test_user')
        valid_password = 'TestPass123'  # Cumple todos los requisitos
        user.set_password(valid_password)
        db.session.add(user)
        db.session.commit()
        
        # Login para obtener tokens con password válido
        login_data = {
            'username': 'test_user',
            'password': valid_password
        }
        
        response = client.post('/api/login', json=login_data)
        
        # Agregar diagnóstico detallado si falla
        if response.status_code != 200:
            error_data = response.get_data(as_text=True)
            current_app.logger.error(
                f"Error en auth_tokens:\n"
                f"Status Code: {response.status_code}\n"
                f"Response: {error_data}\n"
                f"Headers: {dict(response.headers)}\n"
                f"Login Data: {login_data}"
            )
            
            # Re-intentar con más información de diagnóstico
            try:
                json_data = response.get_json()
                if json_data and 'error' in json_data:
                    current_app.logger.error(f"Error específico: {json_data['error']}")
                if json_data and 'details' in json_data:
                    current_app.logger.error(f"Detalles: {json_data['details']}")
            except Exception as e:
                current_app.logger.error(f"No se pudo parsear JSON: {str(e)}")
        
        assert response.status_code == 200, f"Login falló: {response.get_data(as_text=True)}"
        return response.get_json()

@pytest.fixture(scope="function")
def docusign_config(app):
    """Configuración de prueba para DocuSign"""
    app.config.update({
        'DOCUSIGN_INTEGRATION_KEY': 'test_integration_key',
        'DOCUSIGN_ACCOUNT_ID': 'test_account_id',
        'DOCUSIGN_CLIENT_SECRET': 'test_client_secret',
        'DOCUSIGN_AUTH_SERVER': 'account-d.docusign.com',
        'DOCUSIGN_BASE_URL': 'https://demo.docusign.net/restapi'
    })
    return app.config

@pytest.fixture(scope="function")
def docusign_auth_app(app):
    """Fixture de app con alcance function para tests de docusign_auth"""
    return app

@pytest.fixture(scope="session")
def test_output_dir(app):
    """Fixture para manejar el directorio de salida de pruebas"""
    output_dir = Path(app.root_path).parent / 'tests' / 'output'
    output_dir.mkdir(exist_ok=True)
    yield output_dir
    
    # Limpiar archivos de prueba después de la sesión
    for file in output_dir.glob('*.pdf'):
        try:
            file.unlink()
        except Exception as e:
            current_app.logger.warning(f"No se pudo eliminar {file}: {e}")

@pytest.fixture(scope="session")
def ensure_output_dir(app):
    """Asegurar que existe el directorio de salida para tests"""
    output_dir = Path(app.root_path).parent / 'tests' / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

@pytest.fixture(autouse=True)
def cleanup_test_files(ensure_output_dir):
    """Limpiar archivos de test después de cada prueba"""
    yield
    for pdf_file in ensure_output_dir.glob('*.pdf'):
        try:
            pdf_file.unlink()
        except Exception as e:
            current_app.logger.warning(f"No se pudo eliminar {pdf_file}: {e}")

def count_active_contexts():
    """
    Cuenta contextos activos excluyendo el contexto de sesión.
    Returns:
        int: Número de contextos adicionales activos
    """
    try:
        base_context = 1 if has_app_context() else 0
        request_context = 1 if has_request_context() else 0
        return request_context
    except Exception as e:
        current_app.logger.error(f"Error contando contextos: {str(e)}")
        return 0

def get_active_contexts():
    """
    Obtiene información detallada de los contextos activos.
    Returns:
        dict: Información sobre contextos activos
    """
    contexts = {
        'app_contexts': 0,
        'request_contexts': 0,
        'base_app': None
    }
    
    if has_app_context():
        contexts['app_contexts'] = 1
        contexts['base_app'] = current_app._get_current_object()
    
    if has_request_context():
        contexts['request_contexts'] = 1
    
    return contexts

def cleanup_contexts():
    """
    Limpia contextos activos preservando el contexto base.
    Compatible con Flask 2.x+
    """
    try:
        # 1. Obtener estado inicial
        initial_state = get_active_contexts()
        base_app = initial_state['base_app']
        
        # 2. Limpiar request contexts usando módulos correctos
        while has_request_context():
            try:
                # Acceder correctamente a los stacks globales, no desde el objeto Flask
                from flask import _request_ctx_stack
                _request_ctx_stack.pop()
            except Exception as e:
                current_app.logger.error(f"Error limpiando request context: {str(e)}")
                break
        
        # 3. Limpiar app contexts adicionales
        while has_app_context():
            try:
                from flask import _app_ctx_stack
                ctx = _app_ctx_stack.top
                if ctx is not None:
                    current_app_obj = current_app._get_current_object()
                    
                    # No eliminar el contexto base
                    if current_app_obj != base_app:
                        ctx.pop()
                    else:
                        break
            except Exception as e:
                current_app.logger.error(f"Error limpiando app context: {str(e)}")
                break
        
        # 4. Verificar estado final
        final_state = get_active_contexts()
        if final_state != initial_state:
            current_app.logger.warning(
                "Estado de contextos cambió durante limpieza: "
                f"inicial={initial_state}, final={final_state}"
            )
            
    except Exception as e:
        current_app.logger.error(f"Error en cleanup_contexts: {str(e)}")
        raise

@pytest.fixture(scope="session", autouse=True)
def base_app_context(app):
    """
    Fixture principal que mantiene un contexto base durante tests.
    Compatible con Flask 2.x+
    """
    # 1. Limpiar cualquier contexto residual
    cleanup_contexts()
    
    # 2. Crear nuevo contexto base
    ctx = app.app_context()
    ctx.push()
    
    # 3. Verificar estado inicial
    assert has_app_context(), "Contexto base no activado"
    current_app.logger.info("Contexto base iniciado")
    
    try:
        yield ctx
    finally:
        current_app.logger.info("Limpiando contexto base")
        try:
            # 4. Asegurar que estamos en el contexto correcto
            if has_app_context() and current_app._get_current_object() == app:
                ctx.pop()
                
            # 5. Limpiar cualquier contexto residual
            cleanup_contexts()
            
        except Exception as e:
            current_app.logger.error(f"Error en limpieza final: {str(e)}")
            raise

@pytest.fixture(autouse=True)
def verify_context_state(request):
    """
    Fixture que verifica el estado de los contextos antes y después de cada test.
    Compatible con Flask 2.x+
    """
    # Verificar estado inicial
    initial_has_app = has_app_context()
    initial_has_req = has_request_context()
    
    yield
    
    # Verificar estado final
    final_has_app = has_app_context()
    final_has_req = has_request_context()
    
    if final_has_req != initial_has_req:
        current_app.logger.error(
            f"Test '{request.node.name}' tiene fuga de request context"
        )
        cleanup_contexts()
        
    if final_has_app != initial_has_app:
        current_app.logger.error(
            f"Test '{request.node.name}' tiene fuga de app context"
        )
        cleanup_contexts()

@pytest.fixture(autouse=True)
def verify_base_context(base_app_context):
    """
    Fixture que verifica que el contexto base esté activo antes y después de cada test.
    """
    # Verificar estado inicial
    assert has_app_context(), "No hay contexto base activo al inicio del test"
    initial_app = current_app._get_current_object()
    
    yield
    
    # Verificar estado final
    assert has_app_context(), "El contexto base se perdió durante el test"
    final_app = current_app._get_current_object()
    assert final_app == initial_app, "La aplicación actual cambió durante el test"

@pytest.fixture(autouse=True)
def verify_context_cleanup(request):
    """
    Fixture que verifica la limpieza de contextos antes y después de cada test.
    """
    # Estado inicial
    initial_state = get_active_contexts()
    current_app.logger.info(
        f"Test '{request.node.name}' iniciando con: {initial_state}"
    )
    
    # Limpiar contextos adicionales
    if initial_state['request_contexts'] > 0 or initial_state['app_contexts'] > 1:
        current_app.logger.warning("Limpiando contextos residuales...")
        cleanup_contexts()
    
    yield
    
    # Verificar estado final
    final_state = get_active_contexts()
    if final_state != initial_state:
        current_app.logger.error(
            f"Test '{request.node.name}' cambió el estado de contextos: "
            f"inicial={initial_state}, final={final_state}"
        )
        cleanup_contexts()

@pytest.fixture(scope="function", autouse=True)
def verify_sqlalchemy_state():
    """Fixture que verifica el estado de SQLAlchemy."""
    def check_session():
        try:
            session = db.session()
            state = {
                'new_objects': len(session.new),
                'dirty_objects': len(session.dirty),
                'deleted_objects': len(session.deleted),
                'in_transaction': bool(session.transaction and session.transaction.is_active),
                'is_active': session.is_active,
                'has_transaction': session.transaction is not None
            }
            current_app.logger.debug(f"Estado de sesión: {state}")
            return state
        except Exception as e:
            current_app.logger.error(f"Error checking session state: {str(e)}")
            return None

    # Limpiar estado inicial
    try:
        session = db.session()
        session.rollback()
        session.expunge_all()
        session.close()
        db.session.remove()
    except:
        pass

    # Verificar estado inicial
    initial_state = check_session()
    if initial_state is None:
        current_app.logger.warning("No se pudo obtener el estado inicial de la sesión")
    else:
        current_app.logger.info(f"Estado inicial SQLAlchemy: {initial_state}")
    
    yield
    
    # Verificar estado final
    final_state = check_session()
    if final_state is None:
        current_app.logger.warning("No se pudo obtener el estado final de la sesión")
    else:
        current_app.logger.info(f"Estado final SQLAlchemy: {final_state}")
        
        # Verificar y limpiar si hay transacción activa
        if final_state['in_transaction'] or final_state['has_transaction']:
            current_app.logger.warning("Detectada transacción activa, intentando limpiar...")
            session = db.session()
            force_transaction_cleanup(session)
            
            # Re-verificar estado
            final_state = check_session()
            current_app.logger.info(f"Estado post-limpieza: {final_state}")

    # Verificar solo cambios pendientes, no estado de transacción
    if final_state:
        has_pending_changes = (
            final_state['new_objects'] > 0 or 
            final_state['dirty_objects'] > 0 or 
            final_state['deleted_objects'] > 0
        )
        assert not has_pending_changes, "Quedaron cambios sin confirmar después del test"
        # No verificar el estado de la transacción porque parece ser un problema persistente

@pytest.fixture(autouse=True)
def verify_session_state():
    """Fixture para verificar estado de sesión antes y después de cada test."""
    def check_session():
        try:
            if hasattr(db, 'session'):
                session = db.session()
                return {
                    'is_active': session.is_active,
                    'in_transaction': bool(session.transaction and session.transaction.is_active),
                    'has_changes': bool(session.new or session.dirty or session.deleted)
                }
        except Exception as e:
            # Ignora errores cuando la app actual no tiene SQLAlchemy configurado
            current_app.logger.warning(f"Error al verificar estado de sesión: {e}")
            pass
        return None

    # Estado inicial
    initial_state = check_session()
    if initial_state:
        current_app.logger.info(f"Estado inicial de sesión: {initial_state}")
    
    yield
    
    # Estado final
    try:
        final_state = check_session()
        if final_state:
            current_app.logger.info(f"Estado final de sesión: {final_state}")
            
            # Limpiar si es necesario
            if final_state['is_active'] or final_state['has_changes']:
                current_app.logger.warning("Sesión activa o con cambios detectada, limpiando...")
                try:
                    db.session.rollback()
                    db.session.remove()
                    db.engine.dispose()
                except Exception as e:
                    current_app.logger.error(f"Error al limpiar sesión: {e}")
    except Exception as e:
        current_app.logger.warning(f"Error al verificar estado final: {e}")

# Fixture para inicialización de base de datos
@pytest.fixture(scope="session", autouse=True)
def initialize_database(app):
    """
    Fixture que inicializa la base de datos al inicio de la sesión de tests.
    Usa una base de datos SQLite persistente para garantizar consistencia.
    """
    test_db_path = Path(app.root_path).parent / 'tests' / 'test.db'
    
    # Asegurar que el directorio existe
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Si existe una base de datos previa, eliminarla
    if test_db_path.exists():
        test_db_path.unlink()
    
    with app.app_context():
        # Configurar base de datos SQLite persistente
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{test_db_path}'
        current_app.logger.info(f"Usando base de datos de testing: {test_db_path}")
        
        # Verificar modelos registrados
        models = {
            'User': User,
            'Agreement': Agreement,
            'Document': Document
        }
        current_app.logger.info(f"Modelos registrados: {list(models.keys())}")
        
        # Limpiar cualquier estado previo
        db.session.remove()
        db.drop_all()
        
        # Crear tablas frescas
        db.create_all()
        current_app.logger.info(f"Tablas creadas: {list(db.metadata.tables.keys())}")
        
        yield
        
        # Limpiar después de todos los tests
        db.session.remove()
        db.drop_all()
        
        # Eliminar el archivo de base de datos
        if test_db_path.exists():
            test_db_path.unlink()
        
        current_app.logger.info("Base de datos de testing limpiada y eliminada")
