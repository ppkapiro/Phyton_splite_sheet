import pytest
import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask
from config import Config
from models.database import db, init_db
from .test_utils import TestReporter
from main import app as production_app
import logging

# Empujar el contexto de la aplicación principal para toda la suite de pruebas
production_ctx = production_app.app_context()
production_ctx.push()

# Inicialización de reportes y logging
@pytest.fixture(scope="session", autouse=True)
def initialize_reports():
    """Asegurar que existe el directorio de reportes"""
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    return reports_dir

@pytest.fixture(scope="session")
def app():
    """
    Fixture que usa la app principal con sus blueprints ya registrados
    """
    # Configurar modo testing
    production_app.config['TESTING'] = True
    production_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    return production_app

@pytest.fixture(autouse=True)
def db_reset(app):
    """
    Fixture que limpia y recrea la base de datos antes de cada test.
    Se ejecuta automáticamente para cada test (autouse=True).
    Evita problemas de datos persistentes entre pruebas.
    """
    with app.app_context():
        # Eliminar todas las tablas
        db.drop_all()
        # Recrear todas las tablas limpias
        db.create_all()
        
        yield  # Aquí se ejecuta el test
        
        # Limpiar después del test también
        db.session.remove()

@pytest.fixture(autouse=True)
def app_context(app):
    """Asegura que existe un contexto de aplicación para cada test"""
    with app.app_context():
        yield

@pytest.fixture(autouse=True)
def db_session(app_context):
    """Proporciona una sesión de BD limpia para cada test"""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    yield db.session
    
    db.session.remove()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(app, db_reset):
    """Cliente de prueba usando la app principal"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    Proporciona un runner para ejecutar comandos CLI de Flask en tests.
    """
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
    
    return Report

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
