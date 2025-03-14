import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

# Importar la función guardar_informe si está disponible
try:
    from verificar_entorno import guardar_informe
except ImportError:
    # Si no está disponible, definirla aquí (mismo código que en verificar_entorno.py)
    def guardar_informe(contenido, titulo, es_nuevo=False):
        """
        Guarda o actualiza el informe de verificación del sistema.
        
        Args:
            contenido: Contenido de la sección a añadir/actualizar
            titulo: Título de la sección
            es_nuevo: Si es True, crea un nuevo informe; si es False, actualiza el existente
        """
        ruta_base = Path(__file__).parent.parent
        ruta_informe = ruta_base / "docs" / "verificacion_sistema.md"
        
        # Asegurar que el directorio docs existe
        (ruta_base / "docs").mkdir(exist_ok=True)
        
        # Fecha y hora actual con precisión de segundos
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if es_nuevo or not ruta_informe.exists():
            # Crear un nuevo informe
            with open(ruta_informe, 'w', encoding='utf-8') as f:
                f.write(f"# Informe de Verificación del Sistema\n\n")
                f.write(f"*Última actualización: {ahora}*\n\n")
                f.write(f"## {titulo}\n\n")
                f.write(contenido)
                f.write("\n\n")
        else:
            # Leer el informe existente
            with open(ruta_informe, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
            
            # Actualizar la fecha
            fecha_actualizada = False
            for i, linea in enumerate(lineas):
                if linea.startswith("*Última actualización:"):
                    lineas[i] = f"*Última actualización: {ahora}*\n"
                    fecha_actualizada = True
                    break
            
            # Si no encontró la línea de fecha, agrégala después del título principal
            if not fecha_actualizada:
                for i, linea in enumerate(lineas):
                    if linea.startswith("# Informe"):
                        lineas.insert(i+1, f"\n*Última actualización: {ahora}*\n")
                        break
            
            # Buscar la sección existente o añadir una nueva
            seccion_encontrada = False
            seccion_inicio = -1
            seccion_fin = -1
            
            for i, linea in enumerate(lineas):
                if linea.strip() == f"## {titulo}":
                    seccion_encontrada = True
                    seccion_inicio = i
                    
                    # Buscar el final de la sección (siguiente encabezado ## o fin del archivo)
                    for j in range(i + 1, len(lineas)):
                        if lineas[j].startswith("## "):
                            seccion_fin = j
                            break
                    
                    if seccion_fin == -1:  # No se encontró otro encabezado ##
                        seccion_fin = len(lineas)
                    
                    break
            
            # Actualizar o añadir la sección
            if seccion_encontrada:
                # Reemplazar la sección existente
                lineas_nuevas = lineas[:seccion_inicio + 1]  # Incluye el título de la sección
                lineas_nuevas.append("\n")
                lineas_nuevas.extend(contenido.splitlines(True))
                lineas_nuevas.append("\n\n")
                lineas_nuevas.extend(lineas[seccion_fin:])
                lineas = lineas_nuevas
            else:
                # Añadir nueva sección al final
                lineas.append(f"\n## {titulo}\n\n")
                lineas.append(contenido)
                lineas.append("\n\n")
            
            # Guardar el informe actualizado
            with open(ruta_informe, 'w', encoding='utf-8') as f:
                f.writelines(lineas)
        
        return str(ruta_informe)


def buscar_en_archivo(archivo, patron):
    """Busca un patrón en un archivo y devuelve las líneas que coinciden."""
    resultados = []
    try:
        if not Path(archivo).exists():
            return [(0, f"Error: El archivo {archivo} no existe.")]
        
        with open(archivo, 'r', encoding='utf-8') as f:
            for i, linea in enumerate(f, 1):
                if patron in linea:
                    resultados.append((i, linea.strip()))
        
        if not resultados:
            resultados.append((0, f"No se encontró '{patron}' en {archivo}"))
    except Exception as e:
        resultados.append((0, f"Error al leer {archivo}: {str(e)}"))
    
    return resultados


def ejecutar_comando(comando):
    """Ejecuta un comando del sistema y devuelve la salida."""
    try:
        resultado = subprocess.run(comando, shell=True, text=True, capture_output=True)
        if resultado.returncode == 0:
            return resultado.stdout.strip()
        else:
            return f"Error al ejecutar '{comando}': {resultado.stderr}"
    except Exception as e:
        return f"Excepción al ejecutar '{comando}': {str(e)}"


def contar_lineas_codigo(archivo):
    """Cuenta las líneas de código en un archivo específico."""
    try:
        if not Path(archivo).exists():
            return 0
            
        with open(archivo, 'r', encoding='utf-8') as f:
            return len([l for l in f.readlines() if l.strip() and not l.strip().startswith('#')])
    except Exception:
        return 0


def obtener_version_git():
    """Obtiene la última información de commit de git si está disponible."""
    try:
        commit_hash = ejecutar_comando("git rev-parse --short HEAD")
        commit_date = ejecutar_comando("git log -1 --format=%cd --date=short")
        
        if "Error" not in commit_hash and "Error" not in commit_date:
            return f"Git: {commit_hash} ({commit_date})"
        return "Git: No disponible"
    except Exception:
        return "Git: No disponible"


def verificar_pdf_implementation(guardar_en_informe=True):
    """Verifica la implementación de generación de PDFs en el proyecto."""
    # Fecha y hora para el informe
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    salida = []
    salida.append(f"### Implementación de Generación de PDFs\n")
    salida.append(f"*Verificación ejecutada: {timestamp}*\n\n")
    salida.append(f"*Información del sistema: {sys.platform}, Python {sys.version.split()[0]}, {obtener_version_git()}*\n\n")
    
    # Determinar la ruta base del proyecto
    ruta_base = Path(__file__).parent.parent
    
    # 1. Buscar función generate_pdf en routes/api.py
    salida.append("#### 1. Función `generate_pdf` en routes/api.py\n")
    api_path = ruta_base / "routes" / "api.py"
    resultados = buscar_en_archivo(api_path, "def generate_pdf")
    
    if resultados[0][0] > 0:  # Si se encontró algo (la línea no es 0)
        salida.append("✅ **Encontrada** en:\n")
        for linea, contenido in resultados:
            salida.append(f"- Línea {linea}: `{contenido}`\n")
        
        # Análisis adicional del código de generate_pdf
        lineas_codigo = contar_lineas_codigo(api_path)
        salida.append(f"\n*Tamaño del archivo: {lineas_codigo} líneas de código*\n")
        
        salida.append("\n**Detalles de implementación:**\n")
        for term, desc in [
            ("canvas.Canvas", "Creación de PDF"), 
            ("pdf.drawString", "Escritura de texto"), 
            ("pdf.save", "Finalización del PDF"),
            ("send_file", "Envío al cliente")
        ]:
            resultados_term = buscar_en_archivo(api_path, term)
            if resultados_term[0][0] > 0:
                salida.append(f"- ✅ **{desc}**: Implementado\n")
            else:
                salida.append(f"- ❌ **{desc}**: No implementado\n")
    else:
        salida.append("❌ **No encontrada**. La función no está implementada.\n")
    
    # 2. Verificar registro del Blueprint en main.py
    salida.append("\n#### 2. Registro del Blueprint en main.py\n")
    main_path = ruta_base / "main.py"
    resultados = buscar_en_archivo(main_path, "register_blueprint")
    
    if resultados[0][0] > 0:
        salida.append("✅ **Encontrado registro de blueprints**:\n")
        for i, (linea, contenido) in enumerate(resultados[:3]):  # Limitamos a 3 resultados
            salida.append(f"- Línea {linea}: `{contenido}`\n")
        if len(resultados) > 3:
            salida.append(f"- ... y {len(resultados)-3} más\n")
    else:
        salida.append("❌ **No encontrado registro de blueprints**\n")
    
    # 3. Comprobar si reportlab está en requirements.txt
    salida.append("\n#### 3. ReportLab en requirements.txt\n")
    req_path = ruta_base / "requirements.txt"
    resultados = buscar_en_archivo(req_path, "reportlab")
    
    if resultados[0][0] > 0:
        salida.append("✅ **ReportLab encontrado** en requirements.txt:\n")
        for linea, contenido in resultados:
            salida.append(f"- `{contenido}`\n")
    else:
        salida.append("❌ **ReportLab no encontrado** en requirements.txt\n")
        salida.append("- Recomendación: Añadir `reportlab==4.0.4` a requirements.txt\n")
    
    # 4. Revisar instalación de reportlab
    salida.append("\n#### 4. Instalación de ReportLab\n")
    salida_cmd = ejecutar_comando(f"{sys.executable} -m pip show reportlab")
    
    if "Error" not in salida_cmd:
        lines = salida_cmd.split('\n')
        salida.append("✅ **ReportLab está instalado**:\n")
        for line in lines:
            salida.append(f"   {line}\n")
        version = next((line for line in lines if line.startswith("Version")), "Version: No encontrada")
        version = version.split(": ")[1] if ": " in version else "Desconocida"
    else:
        salida.append(f"   ⚠️  {salida_cmd}\n")
        version = "No instalado"
    
    # 5. Revisar implementación de routes/api.py
    salida.append("\n#### 5. Implementación detallada de generate_pdf\n")
    
    # Buscar elementos específicos de la implementación
    searches = [
        ("📄 Validación de datos:", "Validar datos"),
        ("📊 Procesamiento de participantes:", "participantes"),
        ("📝 Creación del PDF:", "canvas.Canvas"),
        ("📤 Respuesta al cliente:", "send_file"),
        ("⚠️ Manejo de errores:", "except")
    ]
    
    for title, search_term in searches:
        results = buscar_en_archivo(api_path, search_term)
        if results and "No se encontró" not in results[0][1]:
            salida.append(f"   {title} ✓\n")
        else:
            salida.append(f"   {title} ❌\n")
    
    # 6. Verificar integración con DocuSign
    salida.append("\n#### 6. Integración con DocuSign\n")
    docusign_integrado = len(buscar_en_archivo(api_path, "DocuSignService")) > 0
    if docusign_integrado:
        salida.append("✅ **Integración con DocuSign detectada**\n")
    else:
        salida.append("⚠️ **No se detectó integración con DocuSign en la generación de PDFs**\n")
    
    # Evaluar tests y cobertura
    salida.append("\n#### 7. Tests de PDFs\n")
    tests_path = ruta_base / "tests" / "unit" / "test_pdf_generation.py"
    if tests_path.exists():
        test_count = len(buscar_en_archivo(tests_path, "def test_"))
        salida.append(f"✅ **{test_count} tests encontrados** para generación de PDFs\n")
    else:
        salida.append("❌ **No se encontraron tests específicos para PDFs**\n")
    
    # Conclusión
    salida.append("\n" + "="*70 + "\n")
    salida.append(f"🏁 VERIFICACIÓN COMPLETADA - ReportLab v{version}\n")
    
    # Evaluar estado general
    implementacion_completa = (
        "def generate_pdf" in str(resultados) and
        "canvas.Canvas" in open(api_path, 'r', encoding='utf-8').read() and
        "send_file" in open(api_path, 'r', encoding='utf-8').read() and
        "except" in open(api_path, 'r', encoding='utf-8').read() and
        "No instalado" not in version
    )
    
    if implementacion_completa:
        salida.append("✅ LA IMPLEMENTACIÓN DE GENERACIÓN DE PDFs ESTÁ COMPLETA\n")
    elif "No instalado" in version:
        salida.append("❌ REPORTLAB NO ESTÁ INSTALADO - Ejecute: pip install reportlab\n")
    else:
        salida.append("⚠️ LA IMPLEMENTACIÓN DE GENERACIÓN DE PDFs ESTÁ INCOMPLETA\n")
        
        # Indicar qué falta específicamente
        if "canvas.Canvas" not in open(api_path, 'r', encoding='utf-8').read():
            salida.append("   - Falta creación de PDF con canvas.Canvas\n")
        if "send_file" not in open(api_path, 'r', encoding='utf-8').read():
            salida.append("   - Falta envío del PDF al cliente con send_file\n")
        if "except" not in open(api_path, 'r', encoding='utf-8').read():
            salida.append("   - Falta manejo de errores apropiado\n")
    
    salida.append("="*70 + "\n")
    
    # Guardar en informe si es necesario
    if guardar_en_informe:
        ruta_informe = guardar_informe("\n".join(salida), "Implementación de Generación de PDFs")
        print(f"📝 Informe actualizado: {ruta_informe}")
        print("\n".join([linea for linea in salida if linea.startswith("✅") or linea.startswith("❌") or linea.startswith("⚠️")]))
    else:
        print("\n".join(salida))
    
    return "\n".join(salida)


if __name__ == "__main__":
    verificar_pdf_implementation()
