# Implementación de Validaciones Exhaustivas en la API

## Contexto del Proyecto
Split Sheet Backend es una API REST desarrollada con Flask que gestiona documentos de reparto musical y firmas electrónicas. Actualmente cuenta con endpoints funcionales usando stubs y placeholders. La siguiente etapa requiere implementar validaciones exhaustivas para garantizar la integridad y seguridad de los datos.

## Objetivos de la Etapa

### 1. Validación de Datos
- Implementar validación exhaustiva en todos los endpoints
- Verificar formato, tipo y restricciones de datos
- Prevenir inyección de datos maliciosos
- Garantizar consistencia en la base de datos

### 2. Manejo de Errores
- Retornar códigos HTTP apropiados
- Proporcionar mensajes de error descriptivos
- Implementar logging detallado
- Facilitar debugging y monitoreo

### 3. Integración
- Mantener compatibilidad con la lógica existente
- Minimizar impacto en rendimiento
- Facilitar pruebas y mantenimiento
- Documentar cambios y nuevos requerimientos

## Ejemplo Detallado - Endpoint /api/register

### Estructura de Datos Esperada
```json
{
    "username": "usuario_ejemplo",
    "password": "contraseña123",
    "email": "usuario@ejemplo.com",
    "full_name": "Nombre Completo"
}
```

### Validaciones Requeridas

1. **Username**
   - Tipo: string
   - Longitud: 3-30 caracteres
   - Caracteres permitidos: alfanuméricos, guiones y guiones bajos
   - Único en la base de datos
   - Regex: `^[a-zA-Z0-9_-]{3,30}$`

2. **Password**
   - Tipo: string
   - Longitud: 6-128 caracteres
   - Debe incluir: mayúsculas, minúsculas, números
   - No debe contener el username
   - Regex: `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{6,128}$`

3. **Email**
   - Tipo: string
   - Formato válido de email
   - Único en la base de datos
   - Regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

4. **Full Name**
   - Tipo: string
   - Longitud: 2-100 caracteres
   - Solo letras, espacios y guiones
   - Regex: `^[a-zA-Z\s-]{2,100}$`

### Implementación

```python
def validate_register_data(data: dict) -> tuple[bool, str]:
    """
    Valida datos de registro.
    Returns: (is_valid, error_message)
    """
    # 1. Verificar presencia de campos requeridos
    required_fields = ['username', 'password', 'email']
    if missing := [f for f in required_fields if f not in data]:
        return False, f"Campos faltantes: {', '.join(missing)}"
    
    # 2. Validar username
    if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', data['username']):
        return False, "Username inválido"
    
    # 3. Validar password
    if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{6,128}$', 
                   data['password']):
        return False, "Password no cumple requisitos"
    
    # 4. Validar email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                   data['email']):
        return False, "Email inválido"
    
    return True, ""
```

### Manejo de Errores
```python
@bp.route('/register', methods=['POST'])
def register():
    try:
        # 1. Extraer y validar datos
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "Datos faltantes",
                "details": "Se requiere JSON en el body"
            }), 400
        
        # 2. Validar formato y restricciones
        is_valid, error = validate_register_data(data)
        if not is_valid:
            return jsonify({
                "error": "Datos inválidos",
                "details": error
            }), 400
        
        # 3. Verificar duplicados
        if user_exists(data['username'], data['email']):
            return jsonify({
                "error": "Usuario/email ya existe",
                "details": "Por favor use credenciales diferentes"
            }), 409
        
        # 4. Procesar registro si todo es válido
        return process_registration(data)
        
    except Exception as e:
        log_error("Error en registro", e)
        return jsonify({
            "error": "Error interno",
            "details": "Por favor contacte soporte"
        }), 500
```

## Consideraciones Técnicas

### 1. Opciones de Implementación

#### Validación Manual
```python
def validate_field(value: str, regex: str, min_len: int, max_len: int) -> bool:
    if not isinstance(value, str):
        return False
    if not min_len <= len(value) <= max_len:
        return False
    return bool(re.match(regex, value))
```

#### Usando Marshmallow
```python
from marshmallow import Schema, fields, validates, ValidationError

class RegisterSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    email = fields.Email(required=True)
    
    @validates('username')
    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', value):
            raise ValidationError("Username inválido")
```

### 2. Performance
- Implementar caché para validaciones costosas
- Optimizar expresiones regulares
- Monitorear tiempos de respuesta
- Considerar rate limiting

### 3. Testing
- Pruebas unitarias para cada validación
- Casos de borde y valores límite
- Pruebas de integración
- Pruebas de carga

## Plan de Implementación

### Fase 1: Preparación
1. Crear utilidades de validación
2. Implementar logging detallado
3. Configurar monitoreo

### Fase 2: Register Endpoint
1. Implementar validaciones
2. Actualizar tests
3. Documentar cambios
4. Revisar performance

### Fase 3: Otros Endpoints
1. Login
2. Create PDF
3. Send for Signature
4. Status Check

### Fase 4: Revisión
1. Auditoría de seguridad
2. Pruebas de carga
3. Documentación final

## Conclusión
La implementación de validaciones exhaustivas es crucial para la seguridad y robustez de la API. Este documento servirá como guía para mantener consistencia en todos los endpoints y facilitar el mantenimiento futuro.
