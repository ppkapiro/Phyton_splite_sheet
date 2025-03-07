import pytest
from flask import Flask
from config import Config
from models.database import db, init_db
import logging

@pytest.fixture
def app():
    """Crear aplicación de prueba"""
    app = Flask(__name__)
    app.config.from_object(Config.get_test_config())
    
    # Configurar logging para pruebas
    logging.basicConfig(level=logging.DEBUG)
    
    # Inicializar la base de datos
    init_db(app)
    
    yield app

@pytest.fixture
def client(app):
    """Cliente de prueba"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Runner de comandos de prueba"""
    return app.test_cli_runner()
