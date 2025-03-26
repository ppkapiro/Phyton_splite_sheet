# Documentación del Backend Split Sheet

## Introducción
Split Sheet Backend es una API REST desarrollada en Flask para la gestión de documentos Split Sheet y firmas electrónicas mediante DocuSign.

El sistema permite generar documentos PDF de repartición de derechos musicales ("Split Sheet") y facilita el proceso de firma digital a través de la integración con DocuSign.

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

Para obtener información actualizada sobre el estado actual del proyecto, consulte el [Informe de Estado](Informe_Actualizacion_Proyecto.md).

## Verificación y Diagnóstico

Para ejecutar verificaciones del sistema y diagnósticos:

```bash
# Verificar entorno y configuración
python scripts/verify_docusign_connection.py

# Verificar implementación de generación PDF
python scripts/verify_pdf_implementation.py

# Ejecución de pruebas completas
pytest

# Ejecución de pruebas específicas
pytest tests/unit/test_pdf_generation.py
pytest tests/unit/test_docusign_endpoints.py
```

## Componentes Principales

### 1. Autenticación
- Sistema completo basado en JWT (JSON Web Tokens)
- Registro, login y logout de usuarios
- Manejo seguro de contraseñas y tokens

### 2. Generación de PDF
- Creación dinámica de documentos PDF con ReportLab
- Personalización de contenido y formato
- Validación de datos de entrada

### 3. Integración DocuSign
- Autenticación OAuth 2.0 con PKCE
- Envío de documentos para firma digital
- Seguimiento del estado de firmas mediante webhooks

### 4. Seguridad
- Protección de endpoints mediante JWT
- Validación exhaustiva de datos de entrada
- Manejo seguro de sesiones y transacciones

## Referencias

- [Plan de Desarrollo](Plan_Desarrollo.md)
- [Documentación de API](architecture/api_endpoints.md)
- [Informe de Estado](Informe_Actualizacion_Proyecto.md)
