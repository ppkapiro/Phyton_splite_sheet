import ssl
import sys
import platform
import os

def check_ssl():
    """Verificar configuración SSL en entorno Conda"""
    print("\nVerificación de SSL en el entorno Conda:")
    print("-----------------------------------------")
    print(f"Entorno Conda: {os.environ.get('CONDA_DEFAULT_ENV', 'No detectado')}")
    print(f"Ruta Conda: {os.environ.get('CONDA_PREFIX', 'No detectado')}")
    print(f"Versión de Python: {platform.python_version()}")
    print(f"OpenSSL Version: {ssl.OPENSSL_VERSION}")
    print(f"SSL Version: {ssl.OPENSSL_VERSION_INFO}")
    print(f"Sistema Operativo: {platform.system()} {platform.release()}")
    
    # Verificar si SSL está disponible
    try:
        _ = ssl.create_default_context()
        print("\nSSL está configurado correctamente ✓")
    except Exception as e:
        print(f"\nError en la configuración SSL: {str(e)}")

if __name__ == "__main__":
    check_ssl()
