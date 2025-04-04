from marshmallow import Schema, fields, validates, ValidationError
import re

class StatusCheckSchema(Schema):
    """
    Esquema de validación para el endpoint /api/status_check.
    
    Campos:
    - document_id: Obligatorio, identificador alfanumérico
    - recipient_email: Opcional, email del destinatario específico
    """
    
    document_id = fields.Str(
        required=True,
        error_messages={
            "required": "El document_id es obligatorio",
            "type": "El document_id debe ser una cadena de texto",
            "invalid": "Formato de document_id inválido"
        }
    )
    
    recipient_email = fields.Email(
        required=False,
        allow_none=True,
        error_messages={
            "invalid": "El formato del email no es válido"
        }
    )

    @validates("document_id")
    def validate_document_id(self, value):
        """Validar formato del document_id"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError(
                "El document_id debe contener solo letras, números, "
                "guiones o guiones bajos"
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
