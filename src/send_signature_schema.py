from marshmallow import Schema, fields, validates, ValidationError
import re

class SendSignatureSchema(Schema):
    """
    Esquema de validación para el endpoint /api/send_signature.
    
    Campos requeridos:
    - document_id: Identificador alfanumérico del documento
    - recipient_email: Email del destinatario
    - recipient_name: Nombre del destinatario
    
    Campo opcional:
    - message: Mensaje personalizado para el destinatario
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
        required=True,
        error_messages={
            "required": "El email del destinatario es obligatorio",
            "invalid": "El formato del email no es válido"
        }
    )
    
    recipient_name = fields.Str(
        required=True,
        error_messages={
            "required": "El nombre del destinatario es obligatorio",
            "type": "El nombre debe ser una cadena de texto"
        }
    )
    
    message = fields.Str(
        required=False,
        allow_none=True,
        error_messages={
            "type": "El mensaje debe ser una cadena de texto"
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

    @validates("recipient_name")
    def validate_recipient_name(self, value):
        """Validar formato del nombre del destinatario"""
        if not re.match(r'^[a-zA-Z\s-]{2,100}$', value):
            raise ValidationError(
                "El nombre debe contener solo letras, espacios o guiones "
                "y tener entre 2 y 100 caracteres"
            )

    @validates("message")
    def validate_message(self, value):
        """Validar longitud del mensaje si está presente"""
        if value is not None and len(value) > 500:
            raise ValidationError(
                "El mensaje no puede exceder los 500 caracteres"
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
