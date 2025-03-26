# Seguridad

## Visión General

Este documento describe las prácticas de seguridad implementadas en Split Sheet Backend para proteger datos sensibles y prevenir vulnerabilidades comunes.

## Autenticación y Autorización

### JWT (JSON Web Tokens)

El sistema utiliza JWT para la autenticación de usuarios:

```python
# Configuración JWT
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-secret-key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)
```

#### Generación de Tokens

```python
# Creación de tokens durante login
access_token = create_access_token(identity=user.id)
refresh_token = create_refresh_token(identity=user.id)
```

#### Protección de Endpoints

```python
@bp.route('/protected_endpoint', methods=['GET'])
@jwt_required()
def protected_endpoint():
    # Obtener ID del usuario actual desde el token
    current_user_id = get_jwt_identity()
    
    # Resto del código...
```

### Blacklisting de Tokens

Para el logout seguro, los tokens se añaden a una lista negra:

```python
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return AuthService.is_token_blacklisted(jti)

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    AuthService.blacklist_token(jti)
    return jsonify({"message": "Sesión cerrada exitosamente"})
```

## OAuth 2.0 con PKCE para DocuSign

### Flujo PKCE

El sistema utiliza el flujo OAuth 2.0 con PKCE (Proof Key for Code Exchange) para la autenticación segura con DocuSign:

```python
# Generación de code_verifier y code_challenge
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip('=')

# Almacenamiento seguro en sesión
session['docusign_code_verifier'] = code_verifier
session['code_verifier_timestamp'] = int(time.time())
```

### Prevención de CSRF

Para evitar ataques CSRF, se utiliza un parámetro `state` en el flujo OAuth:

```python
# Generación de state único
state = secrets.token_urlsafe(16)
session['docusign_state'] = state

# Validación en callback
received_state = request.args.get('state')
if received_state != session.get('docusign_state'):
    return jsonify({"error": "Invalid state parameter"}), 400
```

## Validación de Datos

### Schemas de Marshmallow

Se utilizan schemas de Marshmallow para validar datos de entrada:

```python
class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=[
        validate.Length(min=3, max=50),
        validate.Regexp(r'^[a-zA-Z0-9_]+$', error='Solo letras, números y guiones bajos')
    ])
    password = fields.Str(required=True, validate=validate.Length(min=8))
    email = fields.Email(required=True)
```

### Sanitización de Datos

```python
# Sanitización de datos de entrada
def sanitize_input(data):
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, str):
        # Eliminar caracteres potencialmente peligrosos
        return bleach.clean(data, strip=True)
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data
```

## Protección Contra Vulnerabilidades Comunes

### SQL Injection

El uso de SQLAlchemy ORM proporciona protección contra SQL injection:

```python
# Forma segura (usando ORM)
user = User.query.filter_by(username=username).first()

# En lugar de concatenación insegura como:
# query = f"SELECT * FROM user WHERE username = '{username}'"
```

### XSS (Cross-Site Scripting)

```python
# Sanitizar datos antes de incluirlos en PDFs o emails
def generate_pdf(data):
    # Sanitizar datos sensibles
    sanitized_data = sanitize_input(data)
    
    # Generar PDF con datos sanitizados
    # ...
```

### CSRF (Cross-Site Request Forgery)

```python
# Configuración de protección CSRF para formularios
csrf = CSRFProtect()
csrf.init_app(app)

# Ejemplo de uso en formularios HTML
<form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- Resto del formulario -->
</form>
```

### Rate Limiting

Para proteger contra ataques de fuerza bruta y DoS:

```python
# Configuración de limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Aplicar a endpoints específicos
@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    # ...
```

## Manejo Seguro de Contraseñas

```python
# Generación de hash seguro
def set_password(self, password):
    self.password_hash = generate_password_hash(
        password,
        method='pbkdf2:sha256:150000'  # 150,000 iteraciones
    )

# Verificación segura
def check_password(self, password):
    return check_password_hash(self.password_hash, password)
```

## Encriptación de Datos Sensibles

```python
# Encriptar datos sensibles antes de almacenarlos
def encrypt_sensitive_data(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

# Desencriptar datos
def decrypt_sensitive_data(encrypted_data, key):
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()
```

## Seguridad en la Comunicación

### HTTPS

Configuración para forzar HTTPS en producción:

```python
# En entorno de producción
if app.config['ENV'] == 'production':
    Talisman(app, content_security_policy=None)
```

### CORS (Cross-Origin Resource Sharing)

```python
# Configuración de CORS
CORS(app, resources={
    r"/api/*": {"origins": os.environ.get("ALLOWED_ORIGINS", "*")}
})
```

## Logging y Auditoría

```python
# Configuración de logging seguro
handler = logging.handlers.RotatingFileHandler(
    'logs/security.log',
    maxBytes=10000000,
    backupCount=10
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)

# Logging de eventos de seguridad
def log_security_event(event_type, user_id=None, details=None):
    """Registra eventos de seguridad para auditoría."""
    app.logger.warning(
        f"Security event: {event_type} | "
        f"User: {user_id or 'anonymous'} | "
        f"IP: {request.remote_addr} | "
        f"Details: {details or 'N/A'}"
    )
```

## Validación de Firma HMAC para Webhooks

```python
def validate_signature(request_data, signature, secret_key):
    """Valida firma HMAC para webhooks."""
    computed_signature = hmac.new(
        secret_key.encode(),
        request_data,
        hashlib.sha256
    ).digest()
    
    # Comparación resistente a timing attacks
    return hmac.compare_digest(
        base64.b64decode(signature),
        computed_signature
    )
```

## Buenas Prácticas Implementadas

1. **Principio de mínimo privilegio**: Cada usuario solo puede acceder a sus propios recursos
2. **Contraseñas seguras**: Validación de fuerza y almacenamiento con hash + salt
3. **Manejo seguro de sesiones**: Tiempos de expiración adecuados
4. **Seguridad por defecto**: Configuraciones iniciales con opciones seguras
5. **Headers de seguridad**: Configurados para prevenir vulnerabilidades comunes

## Configuración de Seguridad para Producción

```python
# Configuraciones recomendadas para producción
PRODUCTION_CONFIG = {
    'DEBUG': False,
    'TESTING': False,
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'PREFERRED_URL_SCHEME': 'https',
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'REMEMBER_COOKIE_SECURE': True,
    'REMEMBER_COOKIE_HTTPONLY': True,
    'REMEMBER_COOKIE_DURATION': timedelta(days=14)
}
```

## Proceso de Verificación de Seguridad

1. **Revisión de código**: Revisiones periódicas de seguridad
2. **Tests automatizados**: Pruebas de seguridad incluidas en CI/CD
3. **Análisis estático**: Herramientas como Bandit para Python
4. **Gestión de dependencias**: Revisión regular de vulnerabilidades

## Respuesta a Incidentes

1. **Detección**: Monitoreo y alertas para detectar actividad sospechosa
2. **Contención**: Procedimientos para limitar el impacto de una brecha
3. **Erradicación**: Eliminación de vulnerabilidades
4. **Recuperación**: Restauración de servicio normal
5. **Lecciones aprendidas**: Análisis post-incidente

## Referencias

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- [JWT Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [OAuth 2.0 Security Best Current Practice](https://oauth.net/2/oauth-best-practice/)
