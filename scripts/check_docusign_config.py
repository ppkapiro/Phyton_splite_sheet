import os
import sys
import re
from pathlib import Path

def check_docusign_config():
    """
    Verifica la configuración de DocuSign en el archivo .env
    y sugiere correcciones si es necesario.
    """
    # Path al archivo .env
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print(f"⚠️ No se encontró el archivo .env en {env_path}")
        return False
    
    # Valores a verificar
    required_vars = {
        'DOCUSIGN_INTEGRATION_KEY': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'CLIENT_SECRET': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'DOCUSIGN_ACCOUNT_ID': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'DOCUSIGN_REDIRECT_URI': r'^https?://.*$'
    }
    
    # Placeholders que deben reemplazarse
    placeholders = {
        'CLIENT_SECRET': ['your_client_secret', 'client_secret_here', '2bfeae79-ad29-42fe-acf8-ef40c28de3ef']
    }
    
    # Leer archivo .env
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Verificar cada variable
    errors = []
    warnings = []
    
    for var_name, pattern in required_vars.items():
        # Buscar variable en el archivo
        match = re.search(f'^{var_name}=(.*)$', env_content, re.MULTILINE)
        
        if not match:
            errors.append(f"Falta la variable {var_name}")
            continue
            
        value = match.group(1).strip().strip('"\'')
        
        # Verificar si es un placeholder
        if var_name in placeholders and value in placeholders[var_name]:
            warnings.append(f"{var_name} contiene un valor placeholder: {value}")
        
        # Verificar formato con regex
        if not re.match(pattern, value):
            warnings.append(f"{var_name} no tiene el formato esperado: {value}")
    
    # Reportar resultados
    if errors or warnings:
        print("⚠️ Se encontraron problemas en la configuración de DocuSign:")
        
        if errors:
            print("\nErrores (deben corregirse):")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\nAdvertencias (revisar):")
            for warning in warnings:
                print(f"  - {warning}")
            
        return False
    else:
        print("✓ Configuración de DocuSign verificada correctamente")
        return True

if __name__ == "__main__":
    check_docusign_config()
