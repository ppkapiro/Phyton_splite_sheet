# Documentación del Backend Split Sheet

## Introducción
Split Sheet Backend es una API REST desarrollada en Flask para la gestión de documentos Split Sheet y firmas electrónicas mediante DocuSign.

## Estructura de la Documentación

### Guías de Usuario
- [Instalación y Configuración](guides/installation.md)
- [Flujo de Trabajo de Desarrollo](guides/development_workflow.md)
- [Testing](guides/testing.md)

### Arquitectura
- [Visión General del Sistema](architecture/system_overview.md)
- [Esquema de Base de Datos](architecture/database_schema.md)
- [Endpoints API](architecture/api_endpoints.md)

### Integraciones
- [Configuración de DocuSign](integrations/docusign/setup.md)
- [Flujo de Trabajo DocuSign](integrations/docusign/workflow.md)
- [Webhooks DocuSign](integrations/docusign/webhooks.md)

### Detalles Técnicos
- [Generación de PDFs](technical/pdf_generation.md)
- [Sistema de Validación](technical/validation.md)
- [Seguridad](technical/security.md)

## Estado del Proyecto
Para revisar el estado actual del proyecto, consulte el [Informe de Estado](status_report.md).

## Verificación del Sistema
Para ejecutar verificaciones del sistema:
```bash
# Verificar entorno
python scripts/verificar_entorno.py

# Verificar implementación PDF
python scripts/verificar_pdf.py
```
