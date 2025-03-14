# Plan de Desarrollo - Split Sheet Backend
*Última actualización: 2025-03-16*

## 1. Objetivos Completados

### 1.1 Autenticación Centralizada
- ✓ Implementado middleware en protected_bp
- ✓ Configurado before_request para validación JWT
- ✓ Tests unitarios validando respuestas 401
- ✓ Logging detallado de intentos no autorizados

### 1.2 Generación de PDFs
- ✓ Endpoint /api/pdf/generate_pdf implementado
- ✓ Validación de datos de entrada
- ✓ Generación de PDF con ReportLab
- ✓ Tests de estructura y contenido

## 2. Objetivos Inmediatos (Sprint Actual)

### 2.1 Completar Integración DocuSign
1. [HOY] Flujo OAuth 2.0 con PKCE:
   - Implementar función generate_pkce_pair()
   - Finalizar endpoint /api/docusign/auth
   - Completar endpoint /api/docusign/callback

2. [MAÑANA] Envío de Envelopes:
   - Implementar send_envelope_to_docusign()
   - Validar envío en sandbox
   - Manejar respuestas y errores

3. [ESTA SEMANA] Webhooks:
   - Configurar endpoint para callbacks
   - Implementar validación HMAC
   - Actualizar estado de documentos

### 2.2 Testing DocuSign
- [ ] Crear tests unitarios para flujo OAuth
- [ ] Simular callbacks y verificar manejo
- [ ] Validar flow completo en entorno sandbox

## 3. Próximos Pasos

### 3.1 Alta Prioridad (Próximo Sprint)
1. Implementar rate limiting
2. Migrar a PostgreSQL producción
3. Configurar monitoreo
4. Finalizar documentación API

### 3.2 Media Prioridad
1. Implementar caché Redis
2. Optimizar queries
3. Configurar CI/CD

## 4. Seguridad y Autenticación

### 4.1 Mecanismos de Seguridad
- [ ] Revisar JWT y blacklisting
- [ ] Implementar CSRF protection
- [ ] Configurar rate limiting

### 4.2 Validación
- [ ] Probar endpoints protegidos
- [ ] Simular ataques
- [ ] Verificar CORS

## 5. Migración y Optimización de Base de Datos

### 5.1 PostgreSQL
- [ ] Planificar migración desde SQLite
- [ ] Ajustar configuración
- [ ] Verificar integridad

### 5.2 Rendimiento
- [ ] Pruebas de conexión
- [ ] Optimización de queries
- [ ] Monitoreo de tiempos

## 6. Integración con WordPress

### 6.1 Frontend
- [ ] Revisar formulario actual
- [ ] Optimizar comunicación AJAX
- [ ] Desarrollar plugin si necesario

### 6.2 Testing
- [ ] Validar envío de datos
- [ ] Verificar recepción
- [ ] Probar procesamiento

## 7. Testing y Validación

### 7.1 Pruebas
- [ ] Ampliar cobertura
- [ ] Configurar logging
- [ ] Implementar monitoreo

### 7.2 Verificación
- [ ] Ejecutar pruebas de carga
- [ ] Analizar logs
- [ ] Documentar resultados

## 8. Preparación para Producción

### 8.1 Infraestructura
- [ ] Configurar HTTPS
- [ ] Ajustar variables de entorno DocuSign para producción
- [ ] Documentar despliegue

### 8.2 Staging
- [ ] Pruebas en entorno similar
- [ ] Tests de carga
- [ ] Validación de seguridad

## 9. Comandos de Testing
```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar pruebas específicas de generación de PDF
pytest tests/unit/test_pdf_generation.py

# Detener después del primer fallo y guardar resultados
pytest --maxfail=1 --disable-warnings -q > pytest_output.txt
```

---
**Nota**: Este plan refleja las prioridades actuales con énfasis en la integración con DocuSign y la mejora de la generación de PDF.

---
🔄 Última actualización: 2025-03-16
