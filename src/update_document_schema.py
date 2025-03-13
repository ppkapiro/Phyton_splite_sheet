from marshmallow import Schema, fields, validates, validates_schema, ValidationError
import re

class UpdateDocumentSchema(Schema):
    """
    Esquema de validación para el endpoint /api/update_document.
    
    Campos requeridos:
    - document_id: Identificador alfanumérico
    - title: Título del documento (3-255 caracteres)
    - status: Estado del documento (draft/sent/signed)
    
    Campo opcional:
    - description: Descripción detallada (10-500 caracteres)
    """
    
    VALID_STATUSES = ["draft", "sent", "signed"]
    
    document_id = fields.Str(
        required=True,
        error_messages={
            "required": "El document_id es obligatorio",
            "type": "El document_id debe ser una cadena de texto",
            "invalid": "Formato de document_id inválido"
        }
    )
    
    title = fields.Str(
        required=True,
        error_messages={
            "required": "El título es obligatorio",
            "type": "El título debe ser una cadena de texto",
            "invalid": "Formato de título inválido"
        }
    )
    
    description = fields.Str(
        required=False,
        allow_none=True,
        error_messages={
            "type": "La descripción debe ser una cadena de texto",
            "invalid": "Formato de descripción inválido"
        }
    )
    
    status = fields.Str(
        required=True,
        error_messages={
            "required": "El status es obligatorio",
            "type": "El status debe ser una cadena de texto",
            "invalid": "Status inválido"
        }
    )

    @validates("document_id")
    def validate_document_id(self, value):
        """Validar formato del document_id usando regex"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError(
                "El document_id debe contener solo letras, números, "
                "guiones o guiones bajos"
            )

    @validates("title")
    def validate_title(self, value):
        """Validar longitud del título"""
        if len(value) < 3:
            raise ValidationError("El título debe tener al menos 3 caracteres")
        if len(value) > 255:
            raise ValidationError("El título no puede exceder los 255 caracteres")

    @validates("description")
    def validate_description(self, value):
        """Validar longitud de la descripción si está presente"""
        if value is not None:
            if len(value) < 10:
                raise ValidationError("La descripción debe tener al menos 10 caracteres")
            if len(value) > 500:
                raise ValidationError("La descripción no puede exceder los 500 caracteres")

    @validates("status")
    def validate_status(self, value):
        """Validar que el status sea uno de los valores permitidos"""
        if value not in self.VALID_STATUSES:
            raise ValidationError(
                f"Status inválido. Debe ser uno de: {', '.join(self.VALID_STATUSES)}"
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
