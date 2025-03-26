import os
import sys
import requests
import json
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("docusign_verifier")

# Añadir directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importar funciones necesarias
from config.docusign_config import validate_docusign_config
from dotenv import load_dotenv

def test_docusign_connectivity():
    """
    Prueba la conectividad con los servidores de DocuSign y valida la configuración.
    
    Returns:
        dict: Resultados de las pruebas de conectividad
    """
    load_dotenv()
    results = {
        "tests": [],
        "success": True,
        "summary": ""
    }
    
    # Test 1: Verificar variables de entorno
    test_result = {
        "name": "Variables de Entorno",
        "status": "PASS",
        "details": []
    }
    
    required_vars = [
        "DOCUSIGN_INTEGRATION_KEY",
        "DOCUSIGN_CLIENT_SECRET",
        "DOCUSIGN_REDIRECT_URI",
        "DOCUSIGN_AUTH_SERVER",
        "DOCUSIGN_BASE_URL"
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            test_result["status"] = "FAIL"
            test_result["details"].append(f"Variable {var} no configurada")
        elif value.startswith("DOCUSIGN_") or value == "your_secret_here":
            test_result["status"] = "FAIL"
            test_result["details"].append(f"Variable {var} tiene valor por defecto")
        else:
            test_result["details"].append(f"✓ {var}: {value[:5]}..." if 'SECRET' in var else f"✓ {var}: {value}")
            
    results["tests"].append(test_result)
    if test_result["status"] == "FAIL":
        results["success"] = False
    
    # Test 2: Conectividad a DocuSign Auth Server
    auth_server = os.environ.get("DOCUSIGN_AUTH_SERVER", "account-d.docusign.com")
    auth_url = f"https://{auth_server}/oauth/auth"
    
    test_result = {
        "name": "Conectividad a Auth Server",
        "status": "PASS",
        "details": []
    }
    
    try:
        response = requests.get(auth_url, timeout=5)
        test_result["details"].append(f"Respuesta: {response.status_code}")
        
        if response.status_code != 200 and response.status_code != 302:
            test_result["status"] = "FAIL"
            test_result["details"].append(f"Código de estado inesperado: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        test_result["status"] = "FAIL"
        test_result["details"].append(f"Error de conexión: {str(e)}")
    
    results["tests"].append(test_result)
    if test_result["status"] == "FAIL":
        results["success"] = False
    
    # Test 3: Verificar Redirect URI
    redirect_uri = os.environ.get("DOCUSIGN_REDIRECT_URI")
    
    test_result = {
        "name": "Validación de Redirect URI",
        "status": "PASS",
        "details": []
    }
    
    if not redirect_uri:
        test_result["status"] = "FAIL"
        test_result["details"].append("DOCUSIGN_REDIRECT_URI no configurado")
    elif "/api/docusign/callback" not in redirect_uri:
        test_result["status"] = "WARN"
        test_result["details"].append(f"Redirect URI ({redirect_uri}) no contiene la ruta esperada (/api/docusign/callback)")
    else:
        test_result["details"].append(f"URI válido: {redirect_uri}")
        # Verificar accesibilidad del URI si es http/https
        if redirect_uri.startswith(("http://", "https://")):
            try:
                uri_domain = redirect_uri.split("/")[2]
                test_result["details"].append(f"Verificando resolución de dominio para {uri_domain}")
                
                # Solo verificamos que el dominio sea resoluble
                # No hacemos un request completo para evitar problemas
                import socket
                socket.gethostbyname(uri_domain)
                test_result["details"].append(f"✓ Dominio {uri_domain} es resoluble")
            except Exception as e:
                test_result["status"] = "WARN"
                test_result["details"].append(f"No se pudo resolver el dominio: {str(e)}")
    
    results["tests"].append(test_result)
    if test_result["status"] == "FAIL":
        results["success"] = False
    
    # Generar resumen
    pass_count = sum(1 for test in results["tests"] if test["status"] == "PASS")
    fail_count = sum(1 for test in results["tests"] if test["status"] == "FAIL")
    warn_count = sum(1 for test in results["tests"] if test["status"] == "WARN")
    
    results["summary"] = (
        f"Resumen: {pass_count} pruebas exitosas, {fail_count} fallidas, {warn_count} advertencias.\n"
        f"{'✅ Configuración válida!' if results['success'] else '❌ Se encontraron problemas que deben corregirse.'}"
    )
    
    return results

def format_results(results):
    """Formatea los resultados de las pruebas para impresión."""
    output = []
    output.append("=" * 80)
    output.append("VERIFICACIÓN DE CONECTIVIDAD CON DOCUSIGN")
    output.append("=" * 80)
    
    for test in results["tests"]:
        status_icon = "✅" if test["status"] == "PASS" else "❌" if test["status"] == "FAIL" else "⚠️"
        output.append(f"\n{status_icon} {test['name']} - {test['status']}")
        output.append("-" * 50)
        for detail in test["details"]:
            output.append(f"  {detail}")
    
    output.append("\n" + "=" * 80)
    output.append(results["summary"])
    output.append("=" * 80)
    
    return "\n".join(output)

if __name__ == "__main__":
    print("Verificando conectividad con DocuSign...")
    results = test_docusign_connectivity()
    print(format_results(results))
    
    # Guardar resultados en archivo
    report_path = Path(__file__).parent.parent / "reports" / "docusign_connectivity.json"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Reporte guardado en {report_path}")
    
    # Establecer código de salida
    sys.exit(0 if results["success"] else 1)
