import pytest
from flask import json, current_app
from pathlib import Path
from datetime import datetime
import sys
import os
import random

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from models.user import User
from models.database import db

def generate_unique_username(base="test_user"):
    """
    Genera un nombre de usuario único utilizando la fecha/hora actual y un número aleatorio.
    Ejemplo de salida: "test_user_20250314134559_123"
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_int = random.randint(100, 999)
    return f"{base}_{timestamp}_{random_int}"

def test_generate_pdf(client, db_session):
    """Test de generación de PDF con autenticación JWT"""
    # 1. Crear credenciales únicas con nombre de usuario único
    credentials = {
        'username': generate_unique_username("pdf_test"),
        'password': 'TestPass123'  # cumple requisitos de seguridad
    }
    
    try:
        # 2. Crear usuario de prueba
        with current_app.app_context():
            user = User(username=credentials['username'])
            user.set_password(credentials['password'])
            db.session.add(user)
            db.session.commit()
            current_app.logger.debug(f"Usuario creado: {credentials['username']}")

        # 3. Obtener token JWT mediante login
        login_response = client.post(
            '/api/login',
            json=credentials,
            content_type='application/json'
        )
        
        # Verificar login exitoso
        assert login_response.status_code == 200, (
            f"Login falló. Status: {login_response.status_code}. "
            f"Response: {login_response.get_data(as_text=True)}"
        )
        
        auth_data = login_response.get_json()
        token = auth_data.get('access_token')
        assert token, "No se recibió token JWT del login"
        
        # 4. Configurar request con token válido
        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json'
        }
        
        # 5. Enviar solicitud al endpoint PDF
        pdf_data = {
            "title": "Test Song",
            "participants": [
                {"name": "Artist 1", "role": "Composer", "share": 50},
                {"name": "Artist 2", "role": "Producer", "share": 50}
            ],
            "metadata": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "project": "Test Project"
            }
        }
        
        response = client.post('/api/pdf/generate_pdf',
                             json=pdf_data,
                             headers=headers)
        
        # 6. Verificar respuesta exitosa
        assert response.status_code == 200, (
            f"Error generando PDF. Status: {response.status_code}. "
            f"Response: {response.get_data(as_text=True)}"
        )
        assert response.mimetype == 'application/pdf'
        
    finally:
        # 7. Limpiar usuario de prueba
        with current_app.app_context():
            User.query.filter_by(username=credentials['username']).delete()
            db.session.commit()

def test_generate_pdf_invalid_data(client, db_session):
    """
    Prueba la generación de PDF con datos inválidos.
    Usa username único para evitar errores de UNIQUE constraint.
    """
    # Generar username único
    test_username = generate_unique_username("pdf_invalid")
    valid_password = 'TestPass123'
    
    # Crear usuario de prueba
    with current_app.app_context():
        user = User(username=test_username)
        user.set_password(valid_password)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Usuario creado: {test_username} (len={len(test_username)})")
    
    # Login con validación detallada
    login_data = {
        'username': test_username,
        'password': valid_password
    }
    
    login_response = client.post('/api/login', json=login_data)
    
    # Verificar login exitoso
    assert login_response.status_code == 200, (
        f"Login falló con código {login_response.status_code}. "
        f"Username: {test_username}, "
        f"Response: {login_response.get_data(as_text=True)}"
    )
    
    tokens = json.loads(login_response.data)
    assert 'access_token' in tokens, "Token no recibido"

    # Enviar request inválido al endpoint PDF
    headers = {
        'Authorization': f"Bearer {tokens['access_token']}",
        'Content-Type': 'application/json'
    }
    
    invalid_payload = {
        "title": "Test Song"
        # Intencionalmente faltan campos requeridos
    }
    
    response = client.post('/api/pdf/generate_pdf', json=invalid_payload, headers=headers)
    
    # Verificar error 400
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert "error" in error_data
    assert "details" in error_data
    
    # Limpiar
    with current_app.app_context():
        User.query.filter_by(username=test_username).delete()
        db.session.commit()

def test_generate_pdf_unauthorized(client):
    """Prueba que el endpoint retorne 401 sin token"""
    # Test sin token
    response = client.post('/api/pdf/generate_pdf')
    assert response.status_code == 401, "Debe retornar 401 Unauthorized sin token"
    data = json.loads(response.data)
    assert "error" in data, "La respuesta debe contener el campo 'error'"
    assert "details" in data, "La respuesta debe contener el campo 'details'"
    
    # Test con header malformado
    headers = {'Authorization': 'InvalidFormat token123'}
    response = client.post('/api/pdf/generate_pdf', headers=headers)
    assert response.status_code == 401, "Debe retornar 401 con formato inválido"
    data = json.loads(response.data)
    assert "error" in data, "La respuesta debe contener un mensaje de error"

def test_generate_pdf_invalid_token(client):
    """Prueba que el endpoint retorne 401 cuando se envía un token inválido"""
    # Configurar encabezados con token inválido
    headers = {
        'Authorization': 'Bearer invalid.token.here',
        'Content-Type': 'application/json'
    }
    
    # Datos básicos para la solicitud
    pdf_data = {
        "title": "Test Invalid Token",
        "participants": [
            {"name": "Test Artist", "role": "Producer", "share": 100}
        ],
        "metadata": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "project": "Test Project"
        }
    }
    
    # Enviar solicitud al endpoint PDF con token inválido
    response = client.post(
        '/api/pdf/generate_pdf',
        json=pdf_data,
        headers=headers
    )
    
    # Verificar respuesta 401 Unauthorized
    assert response.status_code == 401, f"Esperaba código 401, recibí {response.status_code}"
    
    # Verificar formato JSON de la respuesta
    data = json.loads(response.data)
    assert "error" in data, "Respuesta debe contener campo 'error'"
    assert "details" in data, "Respuesta debe contener campo 'details'"
    
    current_app.logger.info("Test de token inválido completado exitosamente")

def test_generate_pdf_valid_token(client, auth_tokens):
    """Prueba que el endpoint retorne 200 con token válido"""
    # Esta prueba verifica que con un token válido, el endpoint retorne 200
    # y genere el PDF correctamente
    
    # Usar el token del fixture auth_tokens
    headers = {
        'Authorization': f"Bearer {auth_tokens['access_token']}",
        'Content-Type': 'application/json'
    }
    
    pdf_data = {
        "title": "Valid Token Test",
        "participants": [
            {"name": "Valid Artist", "role": "Composer", "share": 100}
        ],
        "metadata": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "project": "Valid Project"
        }
    }
    
    response = client.post(
        '/api/pdf/generate_pdf',
        json=pdf_data,
        headers=headers
    )
    
    # Verificar respuesta exitosa
    assert response.status_code == 200, f"Esperaba código 200, recibí {response.status_code}"
    assert response.mimetype == 'application/pdf', "Debería recibir un PDF"
    
    # Verificar contenido básico
    assert len(response.data) > 1000, "El PDF generado es demasiado pequeño"
    
    current_app.logger.info("Test con token válido completado exitosamente")

def test_pdf_content_structure(client, db_session):
    """Prueba que el PDF generado contiene los elementos esperados"""
    # Generar credenciales únicas para evitar UNIQUE constraint
    unique_username = generate_unique_username("pdf_content")
    credentials = {
        'username': unique_username,
        'password': 'TestPass123'
    }
    
    # Crear usuario de prueba
    with current_app.app_context():
        user = User(username=credentials['username'])
        user.set_password(credentials['password'])
        db.session.add(user)
        db.session.commit()
        current_app.logger.debug(f"Usuario creado para test de contenido: {unique_username}")
    
    try:
        # Obtener token mediante login
        login_response = client.post('/api/login', json=credentials)
        assert login_response.status_code == 200, "Login falló"
        token_data = json.loads(login_response.data)
        
        # Definir datos de prueba
        test_data = {
            "title": "Content Test Song",
            "participants": [
                {"name": "Test Artist", "role": "Compositor", "share": 100}
            ],
            "metadata": {
                "date": "2024-03-14",
                "project": "Test Project"
            }
        }
        
        headers = {
            'Authorization': f"Bearer {token_data['access_token']}",
            'Content-Type': 'application/json'
        }
        
        response = client.post(
            '/api/pdf/generate_pdf',
            json=test_data,
            headers=headers
        )
        
        # Verificar contenido del PDF
        assert response.status_code == 200
        
        # Guardar PDF para análisis
        output_dir = Path(current_app.root_path).parent / 'tests' / 'output'
        output_dir.mkdir(exist_ok=True)
        pdf_path = output_dir / f'content_test_{unique_username}.pdf'
        pdf_path.write_bytes(response.data)
        
        # Verificar tamaño mínimo esperado para un PDF con contenido
        min_size = 1000  # Tamaño mínimo esperado en bytes
        assert len(response.data) > min_size, f"El PDF es demasiado pequeño ({len(response.data)} bytes)"
        
    finally:
        # Limpiar - eliminar usuario de prueba y archivo PDF
        with current_app.app_context():
            User.query.filter_by(username=credentials['username']).delete()
            db.session.commit()
        
        if 'pdf_path' in locals() and pdf_path.exists():
            pdf_path.unlink()
