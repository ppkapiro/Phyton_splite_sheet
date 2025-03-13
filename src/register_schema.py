from marshmallow import Schema, fields, validates, validates_schema, ValidationError
import re

class RegisterSchema(Schema):
    """
    Esquema de validación para el endpoint /api/register.
    
    Campos requeridos:
    - username: 3-30 caracteres alfanuméricos, guiones permitidos
    - password: 6-128 caracteres, debe incluir mayúsculas, minúsculas y números
    - email: formato válido de correo electrónico
    
    Campo opcional:
    - full_name: 2-100 caracteres, letras, espacios y guiones permitidos
    """
    
    # Definición de campos con mensajes de error personalizados
    username = fields.Str(
        required=True,
        error_messages={
            "required": "El username es obligatorio",
            "type": "El username debe ser una cadena de texto"
        }
    )
    
    password = fields.Str(
        required=True,
        error_messages={
            "required": "La contraseña es obligatoria",
            "type": "La contraseña debe ser una cadena de texto"
        }
    )
    
    email = fields.Email(
        required=True,
        error_messages={
            "required": "El email es obligatorio",
            "invalid": "El formato del email no es válido"
        }
    )
    
    full_name = fields.Str(
        required=False,
        allow_none=True,
        error_messages={
            "type": "El nombre completo debe ser una cadena de texto"
        }
    )

    @validates("username")
    def validate_username(self, value):
        """Validar formato del username usando regex"""
        if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', value):
            raise ValidationError(
                "El username debe contener solo letras, números, guiones o guiones bajos "
                "y tener entre 3 y 30 caracteres"
            )

    @validates("password")
    def validate_password(self, value):
        """Validar requisitos de seguridad de la contraseña"""
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{6,128}$', value):
            raise ValidationError(
                "La contraseña debe contener al menos:\n"
                "- Una letra mayúscula\n"
                "- Una letra minúscula\n"
                "- Un número\n"
                "- Entre 6 y 128 caracteres"
            )

    @validates("email")
    def validate_email(self, value):
        """Validar formato del email"""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValidationError("El formato del email no es válido")

    @validates("full_name")
    def validate_full_name(self, value):
        """Validar formato del nombre completo si está presente"""
        if value is not None and not re.match(r'^[a-zA-Z\s-]{2,100}$', value):
            raise ValidationError(
                "El nombre completo debe contener solo letras, espacios o guiones "
                "y tener entre 2 y 100 caracteres"
            )

    @validates_schema
    def validate_schema(self, data, **kwargs):
        """Validaciones adicionales a nivel de esquema"""
        # Verificar que el username no esté contenido en la password
        if 'username' in data and 'password' in data:
            if data['username'].lower() in data['password'].lower():
                raise ValidationError(
                    "La contraseña no puede contener el username",
                    field_name="password"
                )

    class Meta:
        """Configuración adicional del esquema"""
        strict = True
        ordered = True

    def handle_error(self, exc, data, **kwargs):
        """Personalizar formato de errores de validación"""
        errors = {}
        for field_name, field_errors in exc.messages.items():
            errors[field_name] = field_errors[0] if isinstance(field_errors, list) else field_errors
        
        return {
            "error": "Error de validación",
            "details": errors,
            "received_data": data
        }
