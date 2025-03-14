import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime

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
    
    # Fecha y hora actual
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
        for i, linea in enumerate(lineas):
            if linea.startswith("*Última actualización:"):
                lineas[i] = f"*Última actualización: {ahora}*\n"
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

def capturar_salida(func):
    """Captura la salida estándar de una función y la devuelve como string."""
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        func()
    
    return f.getvalue()

def verificar_entorno(guardar_en_informe=True):
    """Verifica la configuración del entorno del proyecto Split Sheet Backend."""
    
    salida = []
    salida.append("### Configuración del Entorno\n")
    
    # Paso 1: Obtener la ruta actual del proyecto
    ruta_actual = os.getcwd()
    salida.append(f"#### Información del Proyecto\n")
    salida.append(f"- **Ruta actual:** `{ruta_actual}`\n")
    
    # Verificar si estamos en el directorio correcto del proyecto
    backend_dir = Path(ruta_actual).name
    if "Backend_API_Flask_Python" in backend_dir:
        salida.append("- ✅ **Directorio del proyecto:** Identificado correctamente\n")
    else:
        salida.append("- ⚠️ **Directorio del proyecto:** No parece ser el directorio principal del backend\n")
    
    # Paso 2: Verificar el entorno Conda
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "No detectado")
    python_version = platform.python_version()
    
    salida.append("\n#### Entorno Python\n")
    salida.append(f"- **Versión Python:** {python_version}\n")
    salida.append(f"- **Ejecutable Python:** `{sys.executable}`\n")
    salida.append(f"- **Entorno Conda activo:** {conda_env}\n")
    
    if conda_env == "No detectado":
        salida.append("- ⚠️ **Advertencia:** No se detectó un entorno Conda activo\n")
    elif conda_env != "Backend_API_Flask_Python":
        salida.append(f"- ⚠️ **Advertencia:** El entorno activo '{conda_env}' no coincide con 'Backend_API_Flask_Python'\n")
    
    # Paso 3: Verificar dependencias instaladas
    salida.append("\n#### Dependencias Instaladas\n")
    try:
        installed_packages = subprocess.check_output([sys.executable, "-m", "pip", "freeze"]).decode("utf-8")
        packages_list = installed_packages.split("\n")
        
        # Verificar dependencias clave
        dependencies = {
            "flask": False,
            "sqlalchemy": False,
            "flask-jwt-extended": False,
            "flask-cors": False,
            "reportlab": False,
            "docusign-esign": False,
            "pytest": False
        }
        
        # Buscar cada dependencia en la lista de paquetes instalados
        for package in packages_list:
            package_lower = package.lower()
            for dep in dependencies:
                if dep in package_lower:
                    dependencies[dep] = True
        
        # Mostrar estado de dependencias
        salida.append("| Dependencia | Estado |\n|------------|--------|\n")
        for dep, installed in dependencies.items():
            status = "✅ Instalado" if installed else "❌ No encontrado"
            salida.append(f"| {dep} | {status} |\n")
            
    except Exception as e:
        salida.append(f"⚠️ **Error al verificar paquetes:** {str(e)}\n")
    
    # Paso 4: Mostrar variables de entorno relevantes
    salida.append("\n#### Variables de Entorno\n")
    env_vars = {
        "FLASK_APP": os.environ.get("FLASK_APP", "No definida"),
        "FLASK_ENV": os.environ.get("FLASK_ENV", "No definida"),
        "FLASK_DEBUG": os.environ.get("FLASK_DEBUG", "No definida"),
        "DOCUSIGN_INTEGRATION_KEY": "***" if os.environ.get("DOCUSIGN_INTEGRATION_KEY") else "No definida",
        "SQLALCHEMY_DATABASE_URI": "Verificando...",
        "JWT_SECRET_KEY": "Verificando..."
    }
    
    # Verificar config.py para buscar otras variables sin exponerlas
    config_path = os.path.join(ruta_actual, "config.py")
    env_vars_found = []
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_content = f.read()
                if "SQLALCHEMY_DATABASE_URI" in config_content:
                    env_vars["SQLALCHEMY_DATABASE_URI"] = "Definida en config.py ✅"
                if "JWT_SECRET_KEY" in config_content or "JWT_PRIVATE_KEY" in config_content:
                    env_vars["JWT_SECRET_KEY"] = "Definida en config.py ✅"
                
                # Buscar otras variables de entorno en config.py
                for line in config_content.split("\n"):
                    if "os.environ.get" in line:
                        try:
                            var_name = line.split("os.environ.get")[1].split(",")[0].strip("(' \")")
                            if var_name not in env_vars and var_name not in env_vars_found:
                                env_vars_found.append(var_name)
                        except:
                            pass
        except:
            salida.append("⚠️ **Error:** No se pudo analizar config.py\n")
    
    # Mostrar variables de entorno
    salida.append("| Variable | Valor |\n|----------|-------|\n")
    for var, value in env_vars.items():
        salida.append(f"| {var} | {value} |\n")
    
    # Mostrar otras variables encontradas
    if env_vars_found:
        salida.append("\n**Otras variables detectadas en config.py:**\n")
        for var in env_vars_found:
            salida.append(f"- `{var}`\n")
    
    # Imprimir en pantalla
    print("\n" + "="*70)
    print("🔍 VERIFICACIÓN DEL ENTORNO - SPLIT SHEET BACKEND")
    print("="*70)
    print("\n".join([linea for linea in salida if not linea.startswith("|") and not linea.startswith("- ")]))
    print("\n" + "="*70)
    print("🏁 VERIFICACIÓN COMPLETADA")
    print("="*70 + "\n")
    
    # Guardar en el informe
    if guardar_en_informe:
        ruta_informe = guardar_informe("".join(salida), "Entorno del Sistema", es_nuevo=True)
        print(f"📝 Informe actualizado: {ruta_informe}")
    
    return "".join(salida)

if __name__ == "__main__":
    verificar_entorno()
