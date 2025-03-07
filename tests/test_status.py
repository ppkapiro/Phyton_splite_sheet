import pytest
import json
import os
from datetime import datetime
from pathlib import Path

class TestReport:
    """Clase para reportes de pruebas individuales"""
    # Atributos de clase inicializados
    results = []
    start_time = datetime.now()  # Inicializar al definir la clase
    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    @classmethod
    def setup_class(cls):
        """Inicialización de clase para pytest"""
        cls.results = []
        cls.start_time = datetime.now()  # Actualizar tiempo de inicio
        cls.total_tests = 0
        cls.passed_tests = 0
        cls.failed_tests = 0

    @classmethod
    def add_result(cls, test_name, status, message=None):
        """Agregar resultado de prueba"""
        cls.results.append({
            'test_name': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        cls.total_tests += 1
        if status == 'PASS':
            cls.passed_tests += 1
        else:
            cls.failed_tests += 1

    def generate_report(self):
        # Verificar que start_time tenga un valor válido
        if self.start_time is None:
            self.start_time = datetime.now()
            print("WARNING: start_time no estaba inicializado, se estableció al tiempo actual")
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = {
            'summary': {
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'duration': f"{duration:.2f} segundos",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'details': self.results
        }
        
        # Crear directorio de reportes si no existe
        report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        # Guardar reporte en archivo JSON
        report_file = os.path.join(report_dir, f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=4)
        
        return report_file

@pytest.fixture(scope="session")
def test_report():
    report = TestReport()
    yield report
    report.generate_report()

def test_api_status(client, test_report):
    """Prueba el endpoint de estado de la API"""
    response = client.get('/api/status')  # Prefix /api agregado
    assert response.status_code == 200
    test_report.add_result('test_api_status', 'PASS')

def test_auth_flow(client, test_report):
    """Prueba el flujo completo de autenticación"""
    # Registro
    register_response = client.post('/api/register',  # Prefix /api agregado
        json={'username': 'testuser', 'password': 'testpass'})
    
    try:
        assert register_response.status_code == 201
        test_report.add_result('test_auth_register', 'PASS')
    except AssertionError:
        test_report.add_result('test_auth_register', 'FAIL',
                              f'Registro fallido: {register_response.data}')
        raise
    
    # Login
    login_response = client.post('/api/login',  # Prefix /api agregado
        json={'username': 'testuser', 'password': 'testpass'})
    
    try:
        assert login_response.status_code == 200
        assert 'access_token' in login_response.json
        test_report.add_result('test_auth_login', 'PASS')
    except AssertionError:
        test_report.add_result('test_auth_login', 'FAIL',
                              f'Login fallido: {login_response.data}')
        raise
