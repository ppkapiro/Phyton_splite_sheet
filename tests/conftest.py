import pytest
import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, current_app, _app_ctx_stack, _request_ctx_stack, has_app_context, has_request_context
from config import Config
from models.database import db, init_db, create_tables, drop_tables, init_app
from .test_utils import TestReporter
from main import app as production_app, create_app
import logging

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
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test_key',
        'JWT_PRIVATE_KEY': 'test_key',  # Agregar clave JWT para tests
        'JWT_PUBLIC_KEY': 'test_pub_key',  # Agregar clave pública
        'JWT_ALGORITHM': 'HS256',  # Usar algoritmo más simple para tests
        'DOCUSIGN_INTEGRATION_KEY': 'test_key',
        'DOCUSIGN_CLIENT_SECRET': 'test_secret',
        'DOCUSIGN_AUTH_SERVER': 'account-d.docusign.com',
        'DOCUSIGN_TOKEN_URL': 'https://account-d.docusign.com/oauth/token',
        'DOCUSIGN_REDIRECT_URI': 'http://localhost:5000/api/callback',
        'DOCUSIGN_HMAC_KEY': 'test_hmac_key'  # Agregar clave HMAC para tests
    })
    
    # Inicializar SQLAlchemy una sola vez
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    
    return app

def cleanup_sqlalchemy():
    """Limpieza exhaustiva de SQLAlchemy"""
    try:
        if not has_app_context():
            raise RuntimeError("Se requiere contexto de aplicación para limpiar SQLAlchemy")
            
        # 1. Limpiar sesiones activas
        if hasattr(db, 'session'):
            if db.session.is_active:
                db.session.rollback()
            db.session.remove()
            db.session.close_all_sessions()
            
        # 2. Limpiar registro de sesiones
        if hasattr(db.session, 'registry'):
            db.session.registry.clear()
            
        # 3. Disponer conexiones
        if hasattr(db, 'engine'):
            db.engine.dispose()
            
        # 4. Reinicializar SQLAlchemy
        if hasattr(current_app, 'extensions'):
            current_app.extensions.pop('sqlalchemy', None)
            db.init_app(current_app)
            
    except Exception as e:
        current_app.logger.error(f"Error en cleanup_sqlalchemy: {str(e)}")
        raise

@pytest.fixture(scope="function")
def db_session(app, base_app_context):
    """
    Fixture unificado para manejo de base de datos.
    Usa base_app_context para asegurar un contexto válido.
    """
    try:
        # Verificar que estamos en el contexto correcto
        assert has_app_context(), "No hay contexto de aplicación activo"
        assert current_app._get_current_object() == app, "Aplicación incorrecta"
        
        # Limpieza inicial agresiva
        cleanup_sqlalchemy()
        
        # Recrear tablas
        db.drop_all()
        db.create_all()
        
        # Verificar estado limpio
        assert not db.session.is_active, "La sesión sigue activa después de limpieza"
        assert len(db.session.registry._scoped_sessions) == 0, "Hay sesiones residuales"
        
        yield db.session
        
    finally:
        try:
            # Limpieza final exhaustiva
            cleanup_sqlalchemy()
            
            # Verificar estado final
            if has_app_context():
                assert not db.session.is_active, "La sesión quedó activa"
                assert len(db.session.registry._scoped_sessions) == 0, "Quedaron sesiones residuales"
                
        except Exception as e:
            current_app.logger.error(f"Error en limpieza final: {str(e)}")
            raise

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
    """Fixture que proporciona tokens JWT para tests"""
    with app.test_request_context():
        # Registrar usuario de prueba
        register_data = {
            "username": "test_auth",
            "password": "AuthPass123",
            "email": "auth@test.com"
        }
        client.post("/api/register", json=register_data)
        
        # Obtener tokens
        response = client.post("/api/login", json={
            "username": "test_auth",
            "password": "AuthPass123"
        })
        
        return json.loads(response.data)

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

def cleanup_contexts():
    """
    Limpia contextos activos usando métodos compatibles con Flask 2.x+
    """
    try:
        while has_request_context():
            current_app._request_ctx_stack.pop()
            
        while has_app_context():
            current_app._app_ctx_stack.pop()
            
    except Exception as e:
        current_app.logger.error(f"Error limpiando contextos: {str(e)}")

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
