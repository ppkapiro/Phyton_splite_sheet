import pytest
from flask import json
from models.user import User
from models.database import db
from unittest.mock import patch

def test_register(app_context, client):  # Cambiar app por app_context
    """Prueba el registro de usuario"""
    # Asegurarse de que la base de datos esté lista
    db.create_all()
    
    # Datos válidos para el registro
    data = {
        "username": "test_user",
        "password": "TestPass123",
        "email": "test@example.com"
    }
    
    # Realizar la solicitud
    response = client.post(
        "/api/register",
        json=data,
        content_type='application/json'
    )
    
    # Verificar el código de estado y el contenido
    assert response.status_code == 201, f"Response error: {response.data.decode('utf-8')}"
    
    response_data = json.loads(response.data)
    assert "message" in response_data
    assert response_data["message"] == "Usuario registrado exitosamente"
    assert "user" in response_data
    assert response_data["user"]["username"] == "test_user"
    
    # Verificar que el usuario se guardó en la base de datos
    user = User.query.filter_by(username="test_user").first()
    assert user is not None
    assert user.email == "test@example.com"
    
    # Limpiar
    db.session.delete(user)
    db.session.commit()

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

def test_auth_flow(client):
    """Probar el flujo completo de autenticación"""
    # 1. Registrar usuario
    register_data = {
        "username": "test_user",
        "password": "TestPass123",
        "email": "test@example.com"
    }
    register_response = client.post('/api/register', json=register_data)
    assert register_response.status_code in [201, 400]  # 400 si ya existe

    # 2. Login
    login_data = {
        "username": "test_user",
        "password": "TestPass123"
    }
    login_response = client.post('/api/login', json=login_data)
    assert login_response.status_code == 200
    
    # Verificar respuesta del login
    login_data = json.loads(login_response.data)
    assert 'access_token' in login_data
    
    # 3. Acceder a ruta protegida
    headers = {
        'Authorization': f"Bearer {login_data['access_token']}"
    }
    protected_response = client.get('/api/test_protected', headers=headers)
    
    # Agregar más diagnóstico en caso de error
    if protected_response.status_code != 200:
        print(f"Error en respuesta protegida: {protected_response.data.decode('utf-8')}")
        
    assert protected_response.status_code == 200, f"Respuesta: {protected_response.data.decode('utf-8')}"
    
    # Verificar contenido de la respuesta
    protected_data = json.loads(protected_response.data)
    assert protected_data['status'] == 'success'
    assert 'username' in protected_data
    assert protected_data['username'] == 'test_user'

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
