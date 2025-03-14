# Generación de PDFs con ReportLab

## Estado Actual
⚠️ **IMPLEMENTACIÓN INCOMPLETA**: La verificación del sistema indica que la generación de PDFs está implementada parcialmente, aunque los tests están pasando.

## Configuración
- ReportLab versión: 4.0.4
- Dependencias: Pillow

## Uso

### Clase PDFGenerator
La implementación planificada sigue este modelo:

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class PDFGenerator:
    def generate_split_sheet(self, data):
        # Configuración del documento
        pdf = canvas.Canvas("split_sheet.pdf", pagesize=letter)
        
        # Título y metadata
        pdf.setTitle(f"Split Sheet - {data['title']}")
        
        # Contenido
        self._add_header(pdf, data)
        self._add_participants(pdf, data['participants'])
        self._add_signature_blocks(pdf, data['participants'])
        
        return pdf.getpdfdata()
        
    def _add_header(self, pdf, data):
        # Implementación pendiente
        pass
        
    def _add_participants(self, pdf, participants):
        # Implementación pendiente
        pass
        
    def _add_signature_blocks(self, pdf, participants):
        # Implementación pendiente
        pass
```

### Endpoint generate_pdf
El endpoint `/api/generate_pdf` está configurado en `routes/api.py` pero su implementación está incompleta.

## Verificación de la Implementación

Para verificar el estado de la implementación PDF:

```bash
python scripts/verificar_pdf.py
```

## Plan de Implementación

### Fase 1: Completar Clase Generadora
1. Implementar método `_add_header`
2. Implementar método `_add_participants`
3. Implementar método `_add_signature_blocks`

### Fase 2: Mejorar Formato Visual
1. Añadir estilos consistentes
2. Incluir logo y branding
3. Optimizar layout para impresión

### Fase 3: Integración con DocuSign
1. Agregar marcadores de posición para firmas
2. Optimizar formato para visualización en DocuSign

## Referencias

- [Documentación ReportLab](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Ejemplos de código](https://www.reportlab.com/dev/docs/tutorial/)
