# Esquema de Base de Datos

## Modelos y Relaciones

El backend de Split Sheet utiliza SQLAlchemy como ORM (Object-Relational Mapping) para gestionar la persistencia de datos. A continuación se detalla el esquema de la base de datos.

### Diagrama Entidad-Relación

```mermaid
erDiagram
    User ||--o{ Document : owns
    User ||--o{ Agreement : participates
    Agreement ||--o{ Document : has
    Agreement }o--o{ User : has_participants
    
    User {
        int id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
        string docusign_access_token
        string docusign_refresh_token
        datetime docusign_token_expires
    }
    
    Document {
        int id PK
        string title
        string file_path
        string envelope_id UK
        string status
        datetime created_at
        datetime updated_at
        int user_id FK
    }
    
    Agreement {
        int id PK
        string title
        string pdf_url
        string signature_status
        datetime created_at
        datetime updated_at
    }
    
    Participants {
        int user_id FK
        int agreement_id FK
        string role
        float share
    }
```

## Descripción de los Modelos

### User
Representa un usuario registrado en el sistema.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Clave primaria |
| username | String(50) | Nombre de usuario único |
| password_hash | String(128) | Hash de contraseña |
| email | String(120) | Email del usuario |
| created_at | DateTime | Fecha de creación |
| docusign_access_token | String(500) | Token de acceso DocuSign |
| docusign_refresh_token | String(500) | Token de actualización DocuSign |
| docusign_token_expires | DateTime | Fecha de expiración del token |

**Métodos principales**:
- `set_password(password)`: Genera el hash de la contraseña
- `check_password(password)`: Verifica si la contraseña coincide con el hash

### Document
Representa un documento PDF que requiere firma.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Clave primaria |
| title | String(255) | Título del documento |
| file_path | String(512) | Ruta al archivo PDF |
| envelope_id | String(100) | ID del envelope en DocuSign |
| status | String(50) | Estado del documento (draft, sent, signed, etc.) |
| created_at | DateTime | Fecha de creación |
| updated_at | DateTime | Fecha de última actualización |
| user_id | Integer | ID del propietario (FK a User) |

### Agreement
Representa un acuerdo de Split Sheet entre varios participantes.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Clave primaria |
| title | String | Título del acuerdo |
| pdf_url | String | URL del documento PDF |
| signature_status | String | Estado de las firmas |
| created_at | DateTime | Fecha de creación |
| updated_at | DateTime | Fecha de última actualización |

### Participants (Tabla de Asociación)
Relaciona usuarios con acuerdos y almacena información específica de la participación.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| user_id | Integer | ID del usuario (FK a User) |
| agreement_id | Integer | ID del acuerdo (FK a Agreement) |
| role | String | Rol del participante (Compositor, Productor, etc.) |
| share | Float | Porcentaje de participación |

## Índices y Restricciones

- `User.username`: Único
- `User.email`: Único
- `Document.envelope_id`: Único
- `Participants`: Clave primaria compuesta (user_id, agreement_id)

## Migraciones

El proyecto utiliza Flask-Migrate para gestionar las migraciones de esquema:

```bash
# Inicializar migraciones (solo primera vez)
flask db init

# Crear una nueva migración
flask db migrate -m "Descripción del cambio"

# Aplicar migraciones pendientes
flask db upgrade

# Revertir la última migración
flask db downgrade
```

## Consideraciones para Producción

Para el entorno de producción, se recomienda migrar a PostgreSQL:

```python
# Configuración de desarrollo (SQLite)
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'

# Configuración de producción (PostgreSQL)
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/splitsheet'
```

La migración a PostgreSQL está planificada en la hoja de ruta del proyecto y proporcionará mejor rendimiento, soporte para concurrencia y características avanzadas como búsqueda de texto completo.
