from marshmallow import Schema, fields, validates, ValidationError
import re

class SendSignatureSchema(Schema):
    """Esquema de validación para el endpoint send_for_signature"""
    document_id = fields.Str(required=True, error_messages={
        'required': 'El document_id es obligatorio',
        'null': 'El document_id no puede ser nulo',
        'invalid': 'El document_id no es válido'
    })
    recipient_email = fields.Email(required=True, error_messages={
        'required': 'El email del destinatario es obligatorio',
        'invalid': 'El email proporcionado no es válido'
    })
    recipient_name = fields.Str(required=True, error_messages={
        'required': 'El nombre del destinatario es obligatorio',
        'null': 'El nombre del destinatario no puede ser nulo'
    })
    
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
        error_messages = {}
        for field_name, field_errors in exc.messages.items():
            if isinstance(field_errors, list):
                error_messages[field_name] = field_errors[0]
            else:
                error_messages[field_name] = field_errors

        return error_messages
