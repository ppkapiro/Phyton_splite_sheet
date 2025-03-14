import pytest
from flask import Flask
from config import Config
from models.database import db, init_app
import logging
import os
from datetime import datetime
import sys
from pathlib import Path

def setup_logging():
    """Configurar logging para pruebas"""
    # Crear directorios para logs y reportes
    base_dir = Path(__file__).parent.parent
    log_dir = base_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Crear archivo de log con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f'test_output_{timestamp}.log'
    
    # Configurar formato detallado
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Handler para archivo
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Capturar también la salida estándar y de error
    sys.stdout = FileAndConsoleWriter(log_file, sys.stdout)
    sys.stderr = FileAndConsoleWriter(log_file, sys.stderr)
    
    return log_file

class FileAndConsoleWriter:
    """Clase para escribir tanto en archivo como en consola"""
    def __init__(self, log_file, original_stream):
        self.log_file = open(log_file, 'a', encoding='utf-8')
        self.original_stream = original_stream

    def write(self, message):
        self.log_file.write(message)
        self.original_stream.write(message)
        self.flush()

    def flush(self):
        self.log_file.flush()
        self.original_stream.flush()

@pytest.fixture(scope="session", autouse=True)
def setup_test_env(request):
    """Configurar entorno de pruebas y logging"""
    log_file = setup_logging()
    logging.info(f"Iniciando suite de pruebas")
    logging.info(f"Log file: {log_file}")
    
    def cleanup():
        logging.info("Finalizando suite de pruebas")
        logging.shutdown()
    
    request.addfinalizer(cleanup)

import pytest
from flask import Flask
from config import Config
from models.database import db, init_app
import logging

@pytest.fixture
def app():
    """Crear aplicación de prueba"""
    app = Flask(__name__)
    app.config.from_object(Config.get_test_config())
    
    # Configurar logging para pruebas
    logging.basicConfig(level=logging.DEBUG)
    
    # Inicializar la base de datos
    init_app(app)  # Usar init_app en lugar de init_db
    
    yield app

@pytest.fixture
def client(app):
    """Cliente de prueba"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Runner de comandos de prueba"""
    return app.test_cli_runner()
