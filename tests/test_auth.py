import pytest
import json
from services.auth_service import AuthService

def test_register(client):
    """Prueba de registro de usuario"""
    response = client.post('/api/register',
        json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 201
    assert b'Usuario registrado exitosamente' in response.data

def test_login_success(client):
    """Prueba de login exitoso"""
    # Registrar usuario primero
    client.post('/api/register',
        json={'username': 'testuser', 'password': 'testpass'})
    
    # Intentar login
    response = client.post('/api/login',
        json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert 'refresh_token' in data

def test_protected_route(client):
    """Prueba de ruta protegida"""
    # Intentar acceder sin token
    response = client.post('/api/generate_pdf')
    assert response.status_code == 401
