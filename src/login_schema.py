from marshmallow import Schema, fields, validates, ValidationError
import re

class LoginSchema(Schema):
    """
    Esquema de validación para el endpoint /api/login.
    
    Campos requeridos:
    - username: 3-30 caracteres alfanuméricos, guiones permitidos
    - password: 6-128 caracteres, debe incluir mayúsculas, minúsculas y números
    """
    
    username = fields.Str(
        required=True,
        error_messages={
            "required": "El username es obligatorio",
            "type": "El username debe ser una cadena de texto",
            "null": "El username no puede ser nulo",
            "invalid": "Formato de username inválido"
        }
    )
    
    password = fields.Str(
        required=True,
        error_messages={
            "required": "La password es obligatoria",
            "type": "La password debe ser una cadena de texto",
            "null": "La password no puede ser nula",
            "invalid": "Formato de password inválido"
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
        """Validar requisitos de seguridad de la password"""
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{6,128}$', value):
            raise ValidationError(
                "La password debe contener al menos:\n"
                "- Una letra mayúscula\n"
                "- Una letra minúscula\n"
                "- Un número\n"
                "- Entre 6 y 128 caracteres"
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
