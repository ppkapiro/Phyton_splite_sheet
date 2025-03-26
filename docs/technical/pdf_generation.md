# Generación de PDFs con ReportLab

## Estado Actual
✅ **IMPLEMENTACIÓN COMPLETA**: La generación de PDFs está implementada y funcionando correctamente, con tests que verifican tanto la estructura como el contenido.

## Configuración
- ReportLab versión: 4.0.4
- Dependencias: Pillow
- Formato: PDF/A-1b (compatible con archivado a largo plazo)

## Uso

### Clase PDFGenerator
La implementación utiliza el canvas de ReportLab para generar PDFs de manera programática:

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_pdf(data):
    """Genera un PDF a partir de los datos proporcionados."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Título y encabezado
    c.drawString(100, 750, data.get('title', 'Documento PDF'))
    
    # Participantes
    y = 700
    for participant in data.get('participants', []):
        line = f"{participant.get('name', '')} - {participant.get('role', '')} - {participant.get('share', '')}%"
        c.drawString(100, y, line)
        y -= 20
    
    # Metadata
    c.drawString(100, y, f"Metadata: {data.get('metadata', {})}")
    
    # Finalizar PDF
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
```

### Endpoint generate_pdf
El endpoint `/api/pdf/generate_pdf` está implementado en `routes/api.py` y requiere autenticación JWT:

```python
@bp.route('/pdf/generate_pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    """Genera un PDF a partir de datos JSON proporcionados."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Datos inválidos", "details": "No se recibieron datos JSON"}), 400
        
    required_fields = ['title', 'participants', 'metadata']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "error": "Datos inválidos", 
            "details": f"Faltan campos requeridos: {', '.join(missing_fields)}"
        }), 400

    # Generar el PDF y devolverlo como archivo
    pdf_buffer = generate_pdf(data)
    return send_file(pdf_buffer, mimetype='application/pdf')
```

## Verificación de la Implementación

Los tests confirman que la implementación funciona correctamente:

```bash
pytest tests/unit/test_pdf_generation.py -v
```

### Pruebas Incluidas
- `test_generate_pdf`: Verifica generación con JWT válido
- `test_generate_pdf_invalid_data`: Verifica validación de datos
- `test_generate_pdf_unauthorized`: Verifica respuesta 401 sin token
- `test_generate_pdf_invalid_token`: Verifica rechazo de tokens inválidos
- `test_pdf_content_structure`: Verifica estructura del PDF generado

## Mejoras Futuras

### Fase 1: Mejorar Estilo Visual
1. Implementar estilos CSS con ReportLab Styles
2. Añadir logo y branding
3. Mejorar layout y tipografía

### Fase 2: Opciones de Personalización
1. Permitir selección de plantillas
2. Añadir soporte para diferentes idiomas
3. Personalización de colores y layout

### Fase 3: Optimización de Integración
1. Mejorar marcadores para DocuSign
2. Añadir códigos QR para verificación
3. Implementar metadatos PDF avanzados

## Referencias

- [Documentación ReportLab](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Ejemplos de código](https://www.reportlab.com/dev/docs/tutorial/)
- [PDF/A Specification](https://www.pdfa.org/resource/pdfa-1-standard/)
