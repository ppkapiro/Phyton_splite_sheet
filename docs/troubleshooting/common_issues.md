# Problemas Comunes y Soluciones

Este documento detalla los problemas más frecuentes encontrados durante el desarrollo y uso de Split Sheet Backend, junto con sus soluciones recomendadas.

## Problemas de Autenticación

### Error: "Token is invalid or expired"

**Síntomas**:
- Respuesta 401 o 422 en endpoints protegidos
- Mensaje de error indicando token inválido o expirado

**Posibles Causas**:
1. El token JWT ha expirado (predeterminado: 1 hora)
2. El token tiene un formato incorrecto
3. El token fue firmado con una clave secreta diferente
4. El token ha sido añadido a la lista negra (logout)

**Soluciones**:
1. Obtener un nuevo token realizando login
2. Verificar que el formato del header sea: `Authorization: Bearer <token>`
3. Asegurar que se use la misma `JWT_SECRET_KEY` para firmar y verificar
4. Verificar si el token ha sido revocado en la lista negra:

```python
from services.auth_service import AuthService
# Extraer JTI del token
jti = decoded_token["jti"]
is_blacklisted = AuthService.is_token_blacklisted(jti)
```

### Error: "Missing Authorization Header"

**Síntomas**:
- Respuesta 401 en endpoints protegidos
- Mensaje: "Missing Authorization Header"

**Soluciones**:
1. Asegurar que se incluye el header `Authorization: Bearer <token>` en las solicitudes
2. Verificar que no hay espacios extras o caracteres no permitidos
3. Probar con un cliente HTTP como Postman o curl:

```bash
curl -X GET http://localhost:5000/api/test_protected \
  -H "Authorization: Bearer eyJhbG..."
```

## Problemas de Base de Datos

### Error: "UNIQUE constraint failed"

**Síntomas**:
- Error 400 o 500 al crear usuarios o recursos
- Mensaje de error mencionando "UNIQUE constraint"

**Causas Comunes**:
- Intentar crear un usuario con nombre o email ya existente
- Usar el mismo `envelope_id` para múltiples documentos

**Soluciones**:
1. Para tests, usar nombres de usuario únicos con timestamping:

```python
def generate_unique_username(base="test_user"):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_int = random.randint(100, 999)
    return f"{base}_{timestamp}_{random_int}"
```

2. Para la aplicación, verificar existencia antes de intentar crear:

```python
existing_user = User.query.filter_by(username=username).first()
if existing_user:
    return jsonify({"error": "Usuario ya existe"}), 409
```

### Error: "No such table"

**Síntomas**:
- Error al iniciar la aplicación o al acceder a endpoints
- Mensaje indicando una tabla faltante

**Causas**:
- Base de datos no inicializada
- Migraciones no aplicadas
- Ruta de base de datos incorrecta

**Soluciones**:
1. Inicializar la base de datos:

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

2. Verificar la ruta de la base de datos en configuración:

```python
# Verificar configuración
print(app.config['SQLALCHEMY_DATABASE_URI'])
```

3. Para tests, asegurar creación de tablas:

```python
with app.app_context():
    db.create_all()
```

## Problemas con DocuSign

### Error: "Code verifier expired"

**Síntomas**:
- Error 400 en el callback de DocuSign
- Mensaje indicando que el `code_verifier` expiró

**Causas**:
- Sesión expirada o borrada durante el flujo de autorización
- El proceso de autorización tomó más de 5 minutos

**Soluciones**:
1. Reiniciar el flujo desde `/api/docusign/auth`
2. Verificar la configuración de sesiones en Flask:

```python
app.config.update({
    'SESSION_TYPE': 'filesystem',
    'SESSION_PERMANENT': True,
    'PERMANENT_SESSION_LIFETIME': timedelta(minutes=30)
})
```

3. Para diagnosticar problemas de sesión, añadir logging:

```python
@docusign_bp.route('/callback')
def callback():
    # Diagnosticar estado de la sesión
    current_app.logger.debug(f"Session state: {session.get('docusign_state')}")
    current_app.logger.debug(f"Session verifier: {session.get('docusign_code_verifier', 'None')[:10]}...")
    current_app.logger.debug(f"Session timestamp: {session.get('code_verifier_timestamp')}")
```

### Error: "Invalid grant"

**Síntomas**:
- Error 400 al intercambiar código por token con DocuSign
- Respuesta con "error": "invalid_grant"

**Causas**:
- Código de autorización ya utilizado
- Código expirado (validez típica: 5 minutos)
- `code_verifier` incorrecto o no coincidente

**Soluciones**:
1. Reiniciar el flujo de autorización desde el inicio
2. Asegurar que el `code_verifier` se conserva durante todo el flujo
3. Verificar la configuración correcta del cliente DocuSign:

```bash
# Verificar configuración
python scripts/verify_docusign_connection.py
```

## Problemas de Contexto Flask

### Error: "Working outside of application context"

**Síntomas**:
- Error mencionando "application context"
- Ocurre frecuentemente en scripts o tests

**Causas**:
- Acceso a `current_app`, `g` o session sin contexto de aplicación
- Operaciones de base de datos fuera del contexto de aplicación

**Soluciones**:
1. Usar `with app.app_context():` para operaciones que requieren contexto:

```python
with app.app_context():
    # Código que requiere contexto de aplicación
    users = User.query.all()
```

2. Para tests, usar el fixture `app_context`:

```python
def test_something(app_context):
    # Aquí ya hay un contexto activo
    users = User.query.all()
```

3. Si ocurre en un blueprint, usar el decorador `@bp.before_request`:

```python
@bp.before_request
def push_app_context():
    if not has_app_context():
        app.app_context().push()
```

## Problemas de Sesiones SQLAlchemy

### Error: "Session is already closed"

**Síntomas**:
- Error "SQLAlchemy: Session is already closed" o "Session not available"
- Ocurre al intentar usar la sesión de base de datos

**Causas**:
- Sesión cerrada prematuramente
- Uso de la sesión fuera de su ámbito

**Soluciones**:
1. Utilizar el contexto `session_scope` para operaciones de base de datos:

```python
from models.database import session_scope

def create_user():
    with session_scope() as session:
        user = User(username="example")
        session.add(user)
        # Commit automático al salir del contexto
```

2. Diagnosticar estado de la sesión:

```python
def diagnose_session(session):
    """Imprime información de diagnóstico de la sesión SQLAlchemy."""
    print(f"Session identity map: {len(session.identity_map)}")
    print(f"Session new: {len(session.new)}")
    print(f"Session dirty: {len(session.dirty)}")
    print(f"Session deleted: {len(session.deleted)}")
    print(f"Is active: {session.is_active}")
    print(f"Transaction: {session.transaction}")
```

3. Limpiar explícitamente en caso de error:

```python
try:
    # Operación con la base de datos
except Exception as e:
    db.session.rollback()
    raise
finally:
    db.session.close()
```

## Problemas con la Generación de PDF

### Error: "Invalid data for PDF generation"

**Síntomas**:
- Error 400 al llamar a `/api/pdf/generate_pdf`
- Mensaje de error sobre datos inválidos

**Causas**:
- Falta de campos requeridos
- Formato incorrecto de participantes
- Suma de porcentajes diferente de 100%

**Soluciones**:
1. Verificar la estructura correcta de datos:

```json
{
    "title": "Nombre del Proyecto",
    "participants": [
        {
            "name": "Nombre del Participante",
            "role": "Compositor",
            "share": 50
        },
        {
            "name": "Otro Participante",
            "role": "Productor",
            "share": 50
        }
    ],
    "metadata": {
        "date": "2025-03-14",
        "project": "Nombre del Proyecto"
    }
}
```

2. Asegurar que la suma de porcentajes sea exactamente 100%
3. Verificar que todos los campos requeridos estén presentes

### Error: "Failed to create PDF"

**Síntomas**:
- Error 500 al generar PDF
- Mensaje relacionado con ReportLab

**Causas**:
- Problema con ReportLab
- Datos incompatibles con el generador de PDF
- Falta de dependencias relacionadas con PDF

**Soluciones**:
1. Verificar instalación de ReportLab y dependencias:

```bash
pip install reportlab Pillow
```

2. Probar el código de generación de PDF aisladamente:

```python
from tests.utils import generate_sample_pdf
pdf_buffer = generate_sample_pdf()
assert len(pdf_buffer.getvalue()) > 0
```

3. Revisar permisos de escritura en el directorio temporal

## Diagnóstico General

### Pasos de Diagnóstico Básico

1. **Verificar configuración**:
```bash
# Examinar variables de entorno
python -c "import os; print('\n'.join([f'{k}={v}' for k, v in os.environ.items() if 'FLASK' in k or 'JWT' in k or 'DOCUSIGN' in k]))"

# Verificar configuración de DocuSign
python scripts/verify_docusign_connection.py
```

2. **Verificar estado de la API**:
```bash
# Verificar endpoint de estado
curl http://localhost:5000/api/status
```

3. **Revisar logs**:
```bash
# Ver últimas 100 líneas del log
tail -n 100 logs/splitsheet.log
```

4. **Verificar estado de la base de datos**:
```bash
# Verificar migraciones
flask db current
flask db check
```

5. **Verificar test suite**:
```bash
# Ejecutar pruebas básicas
pytest tests/unit/test_status.py
```

## Comandos Útiles para Troubleshooting

```bash
# Verificar conexión con DocuSign
python scripts/verify_docusign_connection.py

# Verificar estado de la base de datos
python scripts/check_database.py

# Logs detallados en modo debug
FLASK_DEBUG=1 FLASK_ENV=development flask run

# Pruebas con reporte detallado
pytest -vvs tests/unit/test_problematic_module.py

# Generar reporte de tests a archivo
pytest --verbose > test_report.txt 2>&1
```

## Contacto para Soporte

Para problemas que no puedas resolver usando esta guía:

1. Revisa los [Issues](https://github.com/your-org/split-sheet/issues) en GitHub
2. Abre un nuevo issue con detalles del problema:
   - Descripción detallada del error
   - Pasos para reproducir
   - Logs relevantes
   - Entorno (versión de Python, OS, dependencias)
