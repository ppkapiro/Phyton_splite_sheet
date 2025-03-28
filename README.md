# Split Sheet Backend API

API REST desarrollada en Flask para la gestión de documentos Split Sheet y firmas electrónicas.

## Estructura del Proyecto
```
Split_Sheet/
├── config/
├── models/
├── routes/
├── services/
└── tests/
```

## Configuración

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
- Copiar `config_example.py` a `config.py`
- Actualizar las credenciales de DocuSign

## Endpoints Disponibles

### Autenticación
- POST /api/register - Registro de usuario
- POST /api/login - Inicio de sesión
- POST /api/logout - Cierre de sesión

### Documentos
- POST /api/generate_pdf - Genera PDF Split Sheet
- POST /api/send_for_signature - Envía documento a firmar
- GET /api/signature_status/<envelope_id> - Consulta estado de firma

## Desarrollo

Para ejecutar en modo desarrollo:
```bash
python main.py
```

## Tests

Para ejecutar las pruebas:
```bash
pytest
```
#   B a c k e n d _ A P I _ F l a s k _ P y t h o n  
 #   B a c k e n d _ A P I _ F l a s k _ P y t h o n  
 #   B a c k e n d _ A P I _ F l a s k _ P y t h o n  
 #   B a c k e n d _ A P I _ F l a s k _ P y t h o n  
 #   P h y t o n _ s p l i t e _ s h e e t  
 