import pytest
from flask import Flask
from config.security import sanitize_input, configure_security_headers, xss_protection
import json

def test_sanitize_input_simple():
    """Prueba la sanitización de datos de entrada simples."""
    # Texto con scripts
    malicious_input = '<script>alert("XSS")</script>Hello'
    sanitized = sanitize_input(malicious_input)
    assert sanitized == 'Hello'
    assert '<script>' not in sanitized
    
    # Texto con etiquetas HTML
    html_input = '<p onclick="evil()">Paragraph</p>'
    sanitized = sanitize_input(html_input)
    assert sanitized == 'Paragraph'
    assert '<p' not in sanitized

def test_sanitize_input_complex():
    """Prueba la sanitización de estructuras de datos complejas."""
    # Diccionario con valores maliciosos
    malicious_dict = {
        'name': 'User <script>alert("XSS")</script>',
        'description': '<img src="x" onerror="alert(1)">',
        'tags': ['<script>alert(1)</script>', 'normal tag']
    }
    
    sanitized = sanitize_input(malicious_dict)
    
    assert '<script>' not in sanitized['name']
    assert '<img' not in sanitized['description']
    assert '<script>' not in sanitized['tags'][0]
    assert sanitized['tags'][1] == 'normal tag'

def test_sanitize_input_nonstrings():
    """Prueba que los tipos no string no son afectados."""
    # Valores que no deben ser afectados
    data = {
        'id': 1234,
        'active': True,
        'price': 19.99,
        'null_value': None,
        'list_of_numbers': [1, 2, 3]
    }
    
    sanitized = sanitize_input(data)
    
    assert sanitized['id'] == 1234
    assert sanitized['active'] is True
    assert sanitized['price'] == 19.99
    assert sanitized['null_value'] is None
    assert sanitized['list_of_numbers'] == [1, 2, 3]

def test_security_headers():
    """Prueba que los headers de seguridad se configuran correctamente."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Configurar headers
    configure_security_headers(app)
    
    # Crear ruta de prueba
    @app.route('/test_headers')
    def test_headers():
        return 'Test'
    
    # Realizar solicitud
    with app.test_client() as client:
        response = client.get('/test_headers')
        
        # Verificar headers de seguridad
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
        assert response.headers.get('X-XSS-Protection') == '1; mode=block'
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

def test_xss_protection_decorator():
    """Prueba el decorador de protección XSS."""
    app = Flask(__name__)
    
    # Ruta con el decorador
    @app.route('/protected', methods=['POST'])
    @xss_protection
    def protected_route():
        data = app.request.json
        return json.dumps(data)
    
    # Ruta sin el decorador para comparación
    @app.route('/unprotected', methods=['POST'])
    def unprotected_route():
        data = app.request.get_json()
        return json.dumps(data)
    
    # Datos maliciosos
    malicious_data = {
        'name': '<script>alert("XSS")</script>Test',
        'comment': '<img src="x" onerror="alert(1)">'
    }
    
    with app.test_client() as client:
        # Probar ruta protegida
        response = client.post(
            '/protected',
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        result = json.loads(response.data)
        
        # Verificar sanitización
        assert '<script>' not in result['name']
        assert '<img' not in result['comment']
        
        # Probar ruta no protegida
        response = client.post(
            '/unprotected',
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        result = json.loads(response.data)
        
        # Sin sanitización
        assert '<script>' in result['name']
        assert '<img' in result['comment']
