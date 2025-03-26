# Guía de Instalación

## Requisitos Previos

- Python 3.9 o superior
- pip (gestor de paquetes de Python)
- Git
- Conocimientos básicos de línea de comandos

## Instalación del Entorno de Desarrollo

### 1. Clonar el Repositorio

```bash
git clone https://github.com/your-username/split-sheet.git
cd Split_Sheet/Backend_API_Flask_Python
```

### 2. Crear y Activar Entorno Virtual

#### Usando venv (Python estándar)
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### Usando Conda (alternativa)
```bash
# Crear entorno conda
conda create -n Backend_API_Flask_Python python=3.9
# Activar entorno
conda activate Backend_API_Flask_Python
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y configura las variables necesarias:

```bash
cp .env.example .env
```

Edita el archivo `.env` con los valores adecuados para tu entorno:

```
# Configuración de Flask
FLASK_APP=main.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=tu_clave_secreta_segura

# Base de datos
SQLALCHEMY_DATABASE_URI=sqlite:///app.db

# JWT
JWT_SECRET_KEY=tu_clave_jwt_segura
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# DocuSign (requerido para integración)
DOCUSIGN_INTEGRATION_KEY=tu_integration_key
DOCUSIGN_CLIENT_SECRET=tu_client_secret
DOCUSIGN_ACCOUNT_ID=tu_account_id
DOCUSIGN_AUTH_SERVER=account-d.docusign.com
DOCUSIGN_BASE_URL=https://demo.docusign.net/restapi
DOCUSIGN_REDIRECT_URI=http://localhost:5000/api/docusign/callback
```

### 5. Inicializar la Base de Datos

```bash
# Inicializar las migraciones (primera vez)
flask db init

# Crear migración inicial
flask db migrate -m "Estructura inicial"

# Aplicar migraciones
flask db upgrade
```

### 6. Verificar la Instalación

```bash
# Ejecutar servidor de desarrollo
flask run

# Verificar conexión con DocuSign
python scripts/verify_docusign_connection.py

# Ejecutar pruebas básicas
pytest tests/unit/test_status.py
```

## Configuración para Producción

### Recomendaciones de Seguridad

1. Usa claves secretas fuertes y diferentes para cada entorno
2. Configura HTTPS para todas las comunicaciones
3. Utiliza PostgreSQL en lugar de SQLite
4. Configura logs adecuados y monitorización

### Opciones de Despliegue

#### 1. Servidor Tradicional (Gunicorn + Nginx)

```bash
# Instalar Gunicorn
pip install gunicorn

# Ejecutar con Gunicorn
gunicorn --bind 0.0.0.0:8000 "main:app"
```

#### 2. Contenedores (Docker)

Un `Dockerfile` básico para el proyecto:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

## Solución de Problemas

### Problemas Comunes

1. **Error de importación de módulos**:
   - Verifica que estás ejecutando desde el directorio raíz del proyecto
   - Asegúrate de que el entorno virtual está activado

2. **Error al conectar con DocuSign**:
   - Verifica las credenciales en el archivo `.env`
   - Ejecuta el script de verificación: `python scripts/verify_docusign_connection.py`

3. **Errores de base de datos**:
   - Asegúrate de que las migraciones se aplicaron correctamente
   - Verifica los permisos de escritura en el directorio de la base de datos

### Obtener Ayuda Adicional

- Revisa la [documentación completa](../README.md)
- Consulta el [plan de desarrollo](../Plan_Desarrollo.md)
- Abre un issue en el repositorio de GitHub
