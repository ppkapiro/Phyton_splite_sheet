import os
import shutil
import subprocess
import sys

def clean_git():
    """Limpia toda la estructura de Git del proyecto"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Intenta primero usar comandos git
        subprocess.run(['git', 'rm', '-rf', '.git'], shell=True, check=True)
    except (subprocess.CalledProcessError, PermissionError):
        print("No se pudo eliminar usando git, intentando método alternativo...")
        
        try:
            # Cambiar permisos antes de eliminar
            for root, dirs, files in os.walk(os.path.join(current_dir, '.git')):
                for dir in dirs:
                    os.chmod(os.path.join(root, dir), 0o777)
                for file in files:
                    os.chmod(os.path.join(root, file), 0o777)
            
            # Intentar eliminar el directorio
            shutil.rmtree(os.path.join(current_dir, '.git'), ignore_errors=True)
        except Exception as e:
            print(f"Error al eliminar .git: {str(e)}")
            print("\nPor favor, cierra todos los programas que puedan estar usando el directorio .git")
            print("O ejecuta este script como administrador")
            sys.exit(1)
    
    # Eliminar archivos de Git
    git_files = ['.gitignore', '.gitattributes']
    for file in git_files:
        try:
            file_path = os.path.join(current_dir, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✓ Eliminado archivo {file_path}")
        except Exception as e:
            print(f"No se pudo eliminar {file}: {str(e)}")

    print("\n¡Git eliminado exitosamente!")
    print("\nPara reiniciar Git, ejecuta:")
    print("git init")
    print("git add .")
    print('git commit -m "Primer commit"')

if __name__ == "__main__":
    response = input("¿Estás seguro de que quieres eliminar toda la estructura Git? (y/n): ")
    if response.lower() == 'y':
        clean_git()
    else:
        print("Operación cancelada")
