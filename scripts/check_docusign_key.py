import os
import re

def check_and_update_integration_key(env_path=".env", allow_test_values=False):
    """
    Verifica si DOCUSIGN_INTEGRATION_KEY en el archivo .env tiene un valor placeholder
    y, de ser así, solicita el valor real y actualiza el archivo.
    
    Args:
        env_path (str): Ruta al archivo .env (por defecto: ".env" en el directorio actual)
        allow_test_values (bool): Si True, permite valor 'test_integration_key' para tests
    
    Returns:
        bool: True si se actualizó la clave, False si no fue necesario o no se pudo
    """
    # Verificar si existe el archivo .env
    if not os.path.exists(env_path):
        print(f"Error: No se encontró el archivo {env_path}")
        return False
    
    # Leer el archivo línea por línea
    lines = []
    key_found = False
    key_line_index = -1
    placeholder_detected = False
    
    with open(env_path, 'r') as file:
        for line in file:
            lines.append(line)
            # Verificar si esta línea contiene la clave de DocuSign
            if re.match(r'^[ \t]*DOCUSIGN_INTEGRATION_KEY[ \t]*=', line):
                key_found = True
                key_line_index = len(lines) - 1
                # Extraer el valor actual
                value_match = re.search(r'=[ \t]*["\']?(.*?)["\']?[ \t]*(#.*)?$', line)
                if value_match:
                    value = value_match.group(1).strip()
                    if value == "" or value == "DOCUSIGN_INTEGRATION_KEY" or (not allow_test_values and value == "test_integration_key"):
                        placeholder_detected = True
    
    # Si no se encontró la clave o se detectó un placeholder, solicitar el nuevo valor
    if not key_found or placeholder_detected:
        new_key = input("Por favor, ingrese su DOCUSIGN_INTEGRATION_KEY real: ")
        if not new_key.strip():
            print("No se ingresó ningún valor. No se realizarán cambios.")
            return False
        
        if key_found:
            # Reemplazar la línea existente
            old_line = lines[key_line_index]
            # Preservar comentarios si existen
            comment_match = re.search(r'(#.*)$', old_line)
            comment = comment_match.group(1) if comment_match else ""
            lines[key_line_index] = f'DOCUSIGN_INTEGRATION_KEY="{new_key}" {comment}\n'
        else:
            # Agregar una nueva línea al final
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')  # Asegurarse que hay una línea nueva al final
            lines.append(f'DOCUSIGN_INTEGRATION_KEY="{new_key}"\n')
        
        # Guardar los cambios
        with open(env_path, 'w') as file:
            file.writelines(lines)
        
        print(f"Se actualizó DOCUSIGN_INTEGRATION_KEY en {env_path}")
        return True
    
    print("DOCUSIGN_INTEGRATION_KEY ya tiene un valor real configurado.")
    return False

# Si se ejecuta directamente
if __name__ == "__main__":
    # Permitir valores de prueba solo si estamos en entorno de testing
    import sys
    allow_test = "--testing" in sys.argv
    check_and_update_integration_key(allow_test_values=allow_test)
