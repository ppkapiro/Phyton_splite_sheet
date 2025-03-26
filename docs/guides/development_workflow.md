# Flujo de Trabajo de Desarrollo

## Visión General

Este documento describe el flujo de trabajo recomendado para desarrollar nuevas funcionalidades, corregir errores y mantener el proyecto Split Sheet Backend.

## Estructura del Proyecto

```
Backend_API_Flask_Python/
├── config/             # Configuración de la aplicación
├── models/             # Modelos de datos (SQLAlchemy)
├── routes/             # Endpoints de la API
├── services/           # Lógica de negocio
├── scripts/            # Utilidades y scripts
├── tests/              # Tests unitarios e integración
│   ├── unit/           # Tests unitarios
│   ├── integration/    # Tests de integración
│   └── conftest.py     # Fixtures de pytest
├── docs/               # Documentación
└── main.py             # Punto de entrada de la aplicación
```

## Ciclo de Desarrollo

### 1. Configuración del Entorno

Antes de comenzar a desarrollar, asegúrate de tener el entorno correctamente configurado:

```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores apropiados
```

### 2. Implementación de Nuevas Funcionalidades

#### Flujo Recomendado

1. **Crear rama de desarrollo**:
   ```bash
   git checkout -b feature/nombre-funcionalidad
   ```

2. **Desarrollar funcionalidad**:
   - Implementar tests primero (TDD)
   - Desarrollar la funcionalidad
   - Mantener commits pequeños y descriptivos

3. **Ejecutar pruebas locales**:
   ```bash
   # Ejecutar todas las pruebas
   pytest
   
   # O ejecutar pruebas específicas
   pytest tests/unit/test_nombre_funcionalidad.py
   ```

4. **Solicitar revisión**:
   - Push a GitHub
   - Crear Pull Request
   - Esperar revisión y CI/CD

### 3. Convenciones de Código

#### Estilo de Código

El proyecto sigue las convenciones de PEP 8 con algunas adaptaciones:

```bash
# Verificar estilo de código
flake8 .

# Autoformatear código
black .
```

#### Convenciones de Nombrado

- **Archivos**: snake_case (ej. `user_service.py`)
- **Clases**: PascalCase (ej. `UserService`)
- **Funciones/Variables**: snake_case (ej. `get_user()`, `user_list`)
- **Constantes**: UPPER_SNAKE_CASE (ej. `MAX_ATTEMPTS`)
- **Endpoints de API**: kebab-case (ej. `/api/docusign-auth`)

#### Documentación

- Usar docstrings de tipo Google para clases y funciones
- Mantener la documentación actualizada en la carpeta `/docs`
- Documentar todos los parámetros, excepciones y valores de retorno

```python
def function_name(param1, param2):
    """Breve descripción de la función.
    
    Descripción más detallada que puede
    abarcar múltiples líneas.
    
    Args:
        param1 (tipo): Descripción del parámetro.
        param2 (tipo): Descripción del parámetro.
        
    Returns:
        tipo: Descripción del valor de retorno.
        
    Raises:
        ExceptionType: Cuándo puede ocurrir esta excepción.
    """
    # código
```

### 4. Testing

#### Tipos de Tests

- **Tests Unitarios**: Prueban componentes individuales
- **Tests de Integración**: Prueban la interacción entre componentes
- **Tests de Sistema**: Prueban la API completa

#### Fixtures

Utiliza los fixtures definidos en `tests/conftest.py`:

- `app`: Aplicación Flask configurada para testing
- `db_session`: Sesión de base de datos para pruebas
- `client`: Cliente HTTP para probar endpoints
- `auth_tokens`: Tokens JWT válidos para endpoints protegidos

#### Ejemplo de Test Unitario

```python
def test_generate_pdf_valid_data(client, auth_tokens):
    """Test que verifica la generación correcta de un PDF."""
    headers = {
        'Authorization': f'Bearer {auth_tokens["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "title": "Test Song",
        "participants": [
            {"name": "Artist 1", "role": "Composer", "share": 50}
        ],
        "metadata": {"date": "2025-01-01"}
    }
    
    response = client.post('/api/pdf/generate_pdf', json=data, headers=headers)
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
```

### 5. Gestión de Base de Datos

#### Migraciones

Para cambios en el modelo de datos:

```bash
# Crear nueva migración basada en cambios en modelos
flask db migrate -m "Descripción del cambio"

# Aplicar migraciones
flask db upgrade

# Revertir última migración
flask db downgrade
```

#### Transacciones

Usa el contexto `session_scope` para operaciones transaccionales:

```python
from models.database import session_scope

def create_user(username, password):
    with session_scope() as session:
        user = User(username=username)
        user.set_password(password)
        session.add(user)
        # El commit se realiza automáticamente si no hay excepciones
        # El rollback se ejecuta automáticamente si hay una excepción
    return user
```

## Despliegue

### Preparación para Producción

1. **Actualizar Dependencias**:
   ```bash
   pip freeze > requirements.txt
   ```

2. **Ejecutar todos los tests**:
   ```bash
   pytest
   ```

3. **Verificar configuración**:
   - Variables de entorno de producción
   - Base de datos configurada
   - Redirecciones y URLs correctas

### Proceso de Despliegue

Para servidores tradicionales:

```bash
# Detener servicio actual
sudo systemctl stop splitsheet

# Actualizar código
git pull origin main

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
flask db upgrade

# Iniciar servicio
sudo systemctl start splitsheet
```

## Recursos Adicionales

- [Documentación de Flask](https://flask.palletsprojects.com/)
- [Documentación de SQLAlchemy](https://docs.sqlalchemy.org/)
- [Documentación de pytest](https://docs.pytest.org/)
- [Documentación de DocuSign](https://developers.docusign.com/docs/)
