import pytest
from flask import json
from models.user import User
from unittest.mock import patch

def test_register(client, app):
    """Prueba el registro de usuario"""
    with app.test_request_context():
        # Datos válidos según el schema
        data = {
            "username": "test_user",
            "password": "TestPass123",
            "email": "test@example.com"  # Campo requerido por RegisterSchema
        }
        
        response = client.post(
            "/api/register",
            json=data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["message"] == "Usuario registrado exitosamente"
        assert "user" in data

def test_login_success(client, app, db_session):
    """Prueba el login exitoso"""
    with app.test_request_context():
        # 1. Primero registrar un usuario
        register_data = {
            "username": "login_test",
            "password": "SecurePass123",
            "email": "login@test.com"
        }
        client.post("/api/register", json=register_data)
        
        # 2. Intentar login
        login_data = {
            "username": "login_test",
            "password": "SecurePass123"
        }
        
        response = client.post(
            "/api/login",
            json=login_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "access_token" in data
        assert "refresh_token" in data

@patch('services.docusign_auth.DocuSignAuth.get_access_token', return_value="test_token")
def test_auth_flow(mock_token, client, app, db_session):
    """Prueba el flujo completo de autenticación"""
    with app.test_request_context():
        # Configurar entorno de prueba
        app.config['JWT_PRIVATE_KEY'] = 'test_key'  # Usar clave de prueba
        
        # 1. Registro
        register_data = {
            "username": "flow_test",
            "password": "FlowPass123",
            "email": "flow@test.com"
        }
        register_response = client.post(
            "/api/register",
            json=register_data,
            content_type='application/json'
        )
        assert register_response.status_code == 201

        # 2. Login y obtención de token
        login_data = {
            "username": "flow_test",
            "password": "FlowPass123"
        }
        login_response = client.post(
            "/api/login",
            json=login_data,
            content_type='application/json'
        )
        assert login_response.status_code == 200
        token_data = json.loads(login_response.data)
        assert "access_token" in token_data
        
        # 3. Acceder a ruta protegida (usando generate_pdf en lugar de status_check)
        test_data = {
            "title": "Test Song",
            "participants": [
                {"name": "John Doe", "role": "Composer", "share": 50}
            ],
            "metadata": {
                "date": "2024-03-14",
                "project": "Test Project"
            }
        }
        protected_response = client.post(
            "/api/generate_pdf",
            json=test_data,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            content_type='application/json'
        )
        assert protected_response.status_code == 200

def test_invalid_login_format(client):
    """Prueba intentos de login con formato inválido"""
    # Test 1: JSON vacío
    response = client.post(
        "/api/login",
        json={},
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "details" in data

    # Test 2: Campos requeridos faltantes
    response = client.post(
        "/api/login",
        json={"username": ""},
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "details" in data
    assert "password" in data["details"]

    # Test 3: Datos malformados
    response = client.post(
        "/api/login",
        json={"bad_field": "wrong_value"},
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "details" in data

def test_wrong_credentials(client, app, db_session):
    """Prueba intentos de login con credenciales incorrectas"""
    with app.test_request_context():
        # 1. Primero registrar un usuario válido
        register_data = {
            "username": "test_user",
            "password": "TestPass123",
            "email": "test@example.com"
        }
        client.post("/api/register", json=register_data)

        # Test 1: Usuario no existente
        response = client.post(
            "/api/login",
            json={
                "username": "nonexistent",
                "password": "TestPass123"
            },
            content_type='application/json'
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "Credenciales inválidas"

        # Test 2: Contraseña incorrecta para usuario existente
        response = client.post(
            "/api/login",
            json={
                "username": "test_user",
                "password": "WrongPass123"
            },
            content_type='application/json'
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "Credenciales inválidas"
