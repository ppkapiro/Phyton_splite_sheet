# Guía de Testing

## Visión General

Split Sheet utiliza pytest como framework principal de testing, con fixtures personalizados para facilitar las pruebas de la API Flask, la integración con DocuSign y la interacción con la base de datos.

## Estructura de los Tests

```
tests/
├── unit/                 # Tests unitarios
│   ├── test_auth.py      # Tests de autenticación
│   ├── test_docusign_endpoints.py  # Tests de endpoints DocuSign
│   ├── test_docusign_pkce.py       # Tests de PKCE
│   ├── test_pdf_generation.py      # Tests de generación PDF
│   └── test_status.py              # Tests de estado API
├── integration/          # Tests de integración
│   ├── test_docusign_flow.py  # Flujo completo DocuSign
│   └── test_pdf_flow.py       # Flujo completo PDF
├── output/               # Archivos generados durante tests
├── conftest.py           # Fixtures comunes
└── test_utils.py         # Utilidades para testing
```

## Ejecución de Tests

### Comandos Básicos

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests específicos
pytest tests/unit/test_pdf_generation.py
pytest tests/unit/test_docusign_endpoints.py

# Ejecutar test específico
pytest tests/unit/test_pdf_generation.py::test_generate_pdf_valid_token

# Generar reporte de cobertura
pytest --cov=. --cov-report=html

# Detener después del primer error
pytest -x

# Mostrar salida de print() durante los tests
pytest -v
```

### Opciones Útiles

- `-v`: Modo verbose (más detalles)
- `-x`: Detener después del primer error
- `--maxfail=n`: Detener después de n errores
- `--cov=<directorio>`: Medir cobertura de código
- `--disable-warnings`: No mostrar warnings

## Fixtures Principales

### Fixtures de Aplicación

- `app`: Instancia de la aplicación Flask configurada para tests
- `client`: Cliente HTTP para probar endpoints
- `runner`: Ejecutor de comandos CLI

```python
def test_api_status(client):
    """Prueba el endpoint de estado de la API."""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
```

### Fixtures de Base de Datos

- `test_db`: Base de datos para toda la sesión de tests
- `db_session`: Sesión SQLAlchemy para un test individual
- `reset_database`: Reinicia la base de datos para un test

```python
def test_add_user(app, db_session):
    """Prueba la creación de un usuario."""
    with app.app_context():
        user = add_user("testuser", "TestPass123", "test@example.com")
        assert user is not None
        assert user.username == "testuser"
        assert user.check_password("TestPass123")
```

### Fixtures de Autenticación

- `auth_tokens`: Proporciona tokens JWT válidos para pruebas
- `docusign_config`: Configuración básica de DocuSign para tests

```python
def test_protected_endpoint(client, auth_tokens):
    """Prueba un endpoint protegido."""
    headers = {
        'Authorization': f"Bearer {auth_tokens['access_token']}",
    }
    response = client.get('/api/test_protected', headers=headers)
    assert response.status_code == 200
```

## Estrategias para Tests Efectivos

### 1. Generación de Datos Únicos

Para evitar errores de constrains UNIQUE, usa la función `generate_unique_username()`:

```python
def generate_unique_username(base="test_user"):
    """Genera un nombre de usuario único."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_int = random.randint(100, 999)
    return f"{base}_{timestamp}_{random_int}"
```

### 2. Manejo de Contextos Flask

Los tests pueden requerir contextos de aplicación Flask. Usa los fixtures `app_context` o el context manager:

```python
def test_with_app_context(app):
    with app.app_context():
        # Código que requiere contexto de aplicación
        current_app.logger.info("Test en contexto de aplicación")
```

### 3. Pruebas con Mocks

Para tests que no deben comunicarse con servicios externos como DocuSign:

```python
@patch('services.docusign_service.DocuSignService.exchange_code_for_token')
def test_docusign_callback(mock_exchange, client, app):
    mock_exchange.return_value = {
        'access_token': 'test_token',
        'refresh_token': 'test_refresh',
        'expires_in': 3600
    }
    
    # Preparar la sesión
    with client.session_transaction() as sess:
        sess['docusign_state'] = 'test_state'
        sess['docusign_code_verifier'] = 'test_verifier'
        sess['code_verifier_timestamp'] = int(time.time())
    
    # Hacer la solicitud
    response = client.get('/api/docusign/callback?code=test_code&state=test_state')
    assert response.status_code == 200
```

## Fixture de Verificación Automática

El proyecto incluye fixtures automáticos para verificar y corregir problemas comunes:

- `verify_context_state`: Detecta fugas de contextos Flask
- `verify_sqlalchemy_state`: Detecta transacciones SQLAlchemy no cerradas
- `verify_session_state`: Valida el estado de sesiones

## Guardar Archivos Generados

Para verificar archivos generados (como PDFs):

```python
def test_pdf_content(client, auth_tokens, ensure_output_dir):
    # Generar el PDF con la API
    response = client.post('/api/pdf/generate_pdf', json=data, headers=headers)
    
    # Guardar PDF para análisis
    pdf_path = ensure_output_dir / 'test_output.pdf'
    pdf_path.write_bytes(response.data)
    
    # Verificar tamaño mínimo esperado
    assert len(response.data) > 1000
```

## Limpieza de Recursos

Los fixtures están diseñados para limpiar automáticamente después de cada test, pero siempre es buena práctica hacer limpieza explícita:

```python
def test_with_cleanup(app, db_session):
    # Crear recursos para la prueba
    user = User(username="temp_user", email="temp@example.com")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    
    try:
        # Prueba con el usuario
        assert User.query.filter_by(username="temp_user").first() is not None
    finally:
        # Limpiar explícitamente
        db.session.delete(user)
        db.session.commit()
```

## Reporte de Resultados

Los resultados de las pruebas se guardan automáticamente en la carpeta `reports/`:

- `pytest-report.json`: Informe detallado en formato JSON
- `pytest-log.txt`: Registro de eventos durante la ejecución de pruebas

## Resolución de Problemas Comunes

### Error "UNIQUE constraint failed"

**Problema**: Conflicto al intentar crear usuarios con el mismo nombre.

**Solución**: Usa `generate_unique_username()` para crear nombres de usuario únicos en cada test.

### Error "No application found" o "Working outside of application context"

**Problema**: Se está intentando acceder a `current_app` fuera de un contexto de aplicación.

**Solución**: Usa el fixture `app_context` o el context manager `with app.app_context()`.

### Error de SQLAlchemy "Session is already closed"

**Problema**: La sesión ha sido cerrada antes de que el test termine de usarla.

**Solución**: Usa el fixture `db_session` que garantiza una sesión fresca para cada test.

## Enlaces Útiles

- [Documentación de pytest](https://docs.pytest.org/)
- [Documentación de unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Documentación de pytest-flask](https://pytest-flask.readthedocs.io/)
