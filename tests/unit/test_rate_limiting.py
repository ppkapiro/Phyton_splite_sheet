import pytest
from flask import Flask, jsonify, request
from config.rate_limiting import limiter, get_limit_for_route, is_exempt_from_limits
import time
from unittest.mock import patch

@pytest.fixture
def app_with_limiter():
    """Fixture que proporciona una app Flask con limiter configurado."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    limiter.init_app(app)
    
    # Ruta limitada para pruebas de autenticación
    @app.route('/api/login', methods=['POST'])
    @limiter.limit("5 per minute")
    def login():
        return jsonify({"status": "success"})
    
    # Ruta limitada para pruebas generales
    @app.route('/api/test', methods=['GET'])
    @limiter.limit("3 per minute")
    def test_endpoint():
        return jsonify({"status": "success"})
    
    # Ruta con límites dinámicos
    @app.route('/api/dynamic', methods=['GET'])
    @limiter.limit(lambda: get_limit_for_route(request.path))
    def dynamic_endpoint():
        return jsonify({"status": "success"})
    
    # Ruta con exención condicional
    @app.route('/api/conditional', methods=['GET'])
    @limiter.limit("2 per minute", exempt_when=is_exempt_from_limits)
    def conditional_endpoint():
        return jsonify({"status": "success"})
    
    return app

def test_rate_limit_exceeded(app_with_limiter):
    """Prueba que los límites de tasa se aplican correctamente."""
    client = app_with_limiter.test_client()
    
    # Hacer solicitudes hasta alcanzar el límite
    for i in range(3):
        response = client.get('/api/test')
        assert response.status_code == 200
    
    # La siguiente solicitud debe ser bloqueada
    response = client.get('/api/test')
    assert response.status_code == 429
    
    # Verificar el mensaje de error
    data = response.get_json()
    assert "error" in data
    assert "límite" in data["error"].lower() or "limit" in data["error"].lower()

def test_rate_limit_headers(app_with_limiter):
    """Prueba que los headers de rate limit se incluyen en la respuesta."""
    client = app_with_limiter.test_client()
    
    response = client.get('/api/test')
    
    # Verificar headers de rate limit
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers
    
    # Verificar valores
    assert int(response.headers['X-RateLimit-Limit']) > 0
    assert int(response.headers['X-RateLimit-Remaining']) >= 0

@patch('config.rate_limiting.get_remote_address')
def test_exemption_from_limits(mock_get_address, app_with_limiter):
    """Prueba la exención de límites para IPs específicas."""
    # Simular IP local/exenta
    mock_get_address.return_value = '127.0.0.1'
    
    client = app_with_limiter.test_client()
    
    # Hacer más solicitudes de las permitidas
    for i in range(5):  # Límite es 2 por minuto
        response = client.get('/api/conditional')
        assert response.status_code == 200, f"Solicitud {i+1} debería ser permitida para IP exenta"

def test_dynamic_rate_limits(app_with_limiter):
    """Prueba los límites de tasa dinámicos basados en la ruta."""
    client = app_with_limiter.test_client()
    
    # Verificar que se aplican los límites correctos según la ruta
    with patch('config.rate_limiting.get_limit_for_route') as mock_get_limit:
        mock_get_limit.return_value = ["1 per minute"]
        
        # Primera solicitud debe ser exitosa
        response = client.get('/api/dynamic')
        assert response.status_code == 200
        
        # Segunda solicitud debe ser bloqueada por nuestro límite personalizado
        response = client.get('/api/dynamic')
        assert response.status_code == 429

def test_login_rate_limit(client):
    """Prueba que al realizar múltiples peticiones al endpoint de login se active el rate limit."""
    login_payload = {
        "username": "some_user",
        "password": "some_password"
    }
    headers = {"Content-Type": "application/json"}

    # Se realizan 6 peticiones (el límite es 5 por minuto)
    responses = [client.post('/api/login', json=login_payload, headers=headers) for _ in range(6)]
    
    # Se espera que al menos una respuesta tenga código 429 Too Many Requests.
    statuses = [resp.status_code for resp in responses]
    assert any(status == 429 for status in statuses), "No se aplicó rate limiting (se esperaba un 429)"
