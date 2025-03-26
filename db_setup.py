import os
import click
from flask import Flask
from models.database import db, init_app
from flask_migrate import Migrate
from pathlib import Path

# Crear una aplicación Flask mínima para migraciones
def create_migration_app():
    app = Flask(__name__)
    
    # Definir una ruta absoluta para la base de datos
    instance_path = Path(os.path.dirname(__file__)) / 'instance'
    instance_path.mkdir(exist_ok=True)  # Crear el directorio 'instance' si no existe
    db_path = instance_path / 'app.db'
    
    # Configuración de base de datos desde variables de entorno o valores por defecto
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'SQLALCHEMY_DATABASE_URI', 
        f'sqlite:///{db_path}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar la base de datos
    db.init_app(app)
    
    # Inicializar Flask-Migrate con directorio explícito
    migrate = Migrate(app, db, directory='migrations')
    
    return app

@click.group()
def cli():
    """Comandos para gestionar la base de datos."""
    pass

@cli.command()
def init():
    """Inicializa la base de datos y las migraciones."""
    app = create_migration_app()
    with app.app_context():
        # Asegurarse de que el directorio instance existe
        instance_path = Path(os.path.dirname(__file__)) / 'instance'
        instance_path.mkdir(exist_ok=True)
        
        # Eliminar directorio migrations si existe
        migrations_path = Path(os.path.dirname(__file__)) / 'migrations'
        if migrations_path.exists():
            import shutil
            shutil.rmtree(migrations_path)
            print("🗑️ Directorio migrations existente eliminado")
        
        # Crear nuevo directorio migrations
        migrations_path.mkdir(exist_ok=True)
        
        # Crear configuración inicial de Alembic
        from flask_migrate import init as fm_init
        fm_init(str(migrations_path))
        
        print("✅ Inicialización de migraciones completada.")

@cli.command()
@click.option('--message', '-m', default=None, help='Mensaje de migración')
def migrate(message):
    """Crea una nueva migración basada en los cambios del modelo."""
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import migrate as fm_migrate
        fm_migrate(directory='migrations', message=message)
        print("✅ Migración creada exitosamente.")

@cli.command()
def upgrade():
    """Aplica las migraciones pendientes a la base de datos."""
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import upgrade as fm_upgrade
        fm_upgrade(directory='migrations')
        print("✅ Base de datos actualizada exitosamente.")

@cli.command()
def status():
    """Muestra el estado actual de las migraciones."""
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import current as fm_current
        from alembic.script import ScriptDirectory
        from alembic.config import Config
        
        # Ejecutar current para obtener revisión actual
        result = fm_current(directory='migrations')
        
        # Obtener información adicional sobre revisiones
        config = Config('migrations/alembic.ini')
        config.set_main_option('script_location', 'migrations')
        script = ScriptDirectory.from_config(config)
        
        # Obtener información de revisiones
        current_revision = None
        for head in script.get_heads():
            current_revision = head
        
        # Obtener revisión actual
        current_applied = result
        
        print("\n=== ESTADO DE MIGRACIONES ===")
        if current_applied:
            print(f"✅ Revisión actual: {current_applied}")
        else:
            print("❌ No hay revisiones aplicadas")
        
        print(f"📄 Última revisión disponible: {current_revision}")
        
        if current_applied != current_revision:
            print("⚠️ La base de datos NO está actualizada. Se requiere ejecutar 'upgrade'.")
        else:
            print("✅ La base de datos está actualizada.")
        
        print("\nComandos disponibles:")
        print("  • python db_setup.py upgrade - Actualizar base de datos")
        print("  • python db_setup.py history - Ver historial de migraciones")
        print("  • python db_setup.py show - Listar migraciones disponibles")

@cli.command()
def history():
    """Muestra el historial de migraciones."""
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import history as fm_history
        
        print("\n=== HISTORIAL DE MIGRACIONES ===")
        fm_history(directory='migrations', verbose=True)
        print("\nℹ️ Para más detalles sobre una revisión específica, examina el archivo en migrations/versions/")

@cli.command()
@click.argument('revision', required=False)
def downgrade(revision):
    """Revierte la base de datos a una revisión anterior.
    
    Si no se especifica REVISION, se revierte una migración.
    Para revertir a una revisión específica, proporciona el ID de revisión.
    """
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import downgrade as fm_downgrade
        
        if not revision:
            # Si no se especifica revisión, retroceder una migración
            revision = "-1"
            print(f"⚠️ Revirtiendo una migración...")
        else:
            print(f"⚠️ Revirtiendo a la revisión: {revision}")
        
        print("⚠️ ADVERTENCIA: Esta operación puede resultar en pérdida de datos.")
        confirmation = input("¿Estás seguro? (s/N): ")
        
        if confirmation.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            try:
                fm_downgrade(directory='migrations', revision=revision)
                print("✅ Base de datos revertida exitosamente.")
            except Exception as e:
                print(f"❌ Error al revertir: {e}")
        else:
            print("Operación cancelada.")

@cli.command()
@click.argument('revision', required=True)
def stamp(revision):
    """Marca una revisión como aplicada sin ejecutar la migración.
    
    Args:
        revision: ID de la revisión a marcar como aplicada
    """
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import stamp as fm_stamp
        
        try:
            fm_stamp(directory='migrations', revision=revision)
            print(f"✅ Base de datos marcada en revisión: {revision}")
        except Exception as e:
            print(f"❌ Error al marcar revisión: {e}")

@cli.command()
def show():
    """Muestra las migraciones disponibles."""
    migrations_path = Path(os.path.dirname(__file__)) / 'migrations' / 'versions'
    
    if not migrations_path.exists():
        print("❌ No se encontró el directorio de versiones de migraciones.")
        return
    
    print("\n=== MIGRACIONES DISPONIBLES ===")
    
    # Obtener la revisión actual
    app = create_migration_app()
    with app.app_context():
        from flask_migrate import current as fm_current
        current_revision = fm_current(directory='migrations')
    
    found_migrations = False
    for migration_file in sorted(migrations_path.glob('*.py')):
        found_migrations = True
        # Extraer identificador y mensaje de migración del nombre de archivo
        filename = migration_file.name
        if '_' in filename:
            parts = filename.split('_', 1)
            migration_id = parts[0]
            message = parts[1].replace('.py', '').replace('_', ' ')
            
            # Marcar la revisión actual
            status_marker = "🔶 " if migration_id == current_revision else "   "
            print(f"{status_marker}{migration_id}: {message}")
        else:
            print(f"  - {filename}")
    
    if not found_migrations:
        print("❌ No se encontraron archivos de migración.")
        print("   Ejecuta 'python db_setup.py migrate -m \"Primera migración\"' para crear la primera migración.")

@cli.command()
def reset():
    """Elimina la base de datos y las migraciones e inicia desde cero."""
    print("⚠️ ADVERTENCIA: Esta operación eliminará la base de datos y todas las migraciones.")
    confirmation = input("¿Estás seguro? Esta acción NO se puede deshacer. (s/N): ")
    
    if confirmation.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        try:
            # 1. Eliminar archivo de base de datos
            instance_path = Path(os.path.dirname(__file__)) / 'instance'
            if instance_path.exists():
                import shutil
                shutil.rmtree(instance_path)
                print("🗑️ Directorio instance y base de datos eliminados")
            
            # 2. Eliminar directorio migrations
            migrations_path = Path(os.path.dirname(__file__)) / 'migrations'
            if migrations_path.exists():
                shutil.rmtree(migrations_path)
                print("🗑️ Directorio migrations eliminado")
            
            # 3. Eliminar alembic_version si existe
            app = create_migration_app()
            with app.app_context():
                try:
                    db.engine.execute('DROP TABLE IF EXISTS alembic_version')
                    print("🗑️ Tabla alembic_version eliminada")
                except:
                    pass
            
            # 4. Recrear todo
            print("\nIniciando configuración limpia...")
            
            # Inicializar migraciones
            init()
            
            # Crear migración inicial
            migrate(message="Migración inicial")
            
            # Aplicar migración
            upgrade()
            
            print("\n✅ Configuración limpia completada exitosamente")
        except Exception as e:
            print(f"❌ Error durante el reset: {e}")
    else:
        print("Operación cancelada")

@cli.command()
def clean():
    """Limpia completamente la base de datos y las migraciones."""
    print("⚠️ ADVERTENCIA: Esta operación eliminará TODOS los datos y migraciones.")
    confirmation = input("¿Estás seguro? Esta acción NO se puede deshacer. (s/N): ")
    
    if confirmation.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        try:
            # 1. Eliminar base de datos y su directorio
            instance_path = Path(os.path.dirname(__file__)) / 'instance'
            if instance_path.exists():
                import shutil
                shutil.rmtree(instance_path)
                print("🗑️ Directorio instance y base de datos eliminados")
            
            # 2. Eliminar directorio migrations y su contenido
            migrations_path = Path(os.path.dirname(__file__)) / 'migrations'
            if migrations_path.exists():
                shutil.rmtree(migrations_path)
                print("🗑️ Directorio migrations eliminado")
            
            # 3. Eliminar alembic_version si existe
            app = create_migration_app()
            with app.app_context():
                try:
                    db.engine.execute('DROP TABLE IF EXISTS alembic_version')
                    print("🗑️ Tabla alembic_version eliminada")
                except:
                    pass
            
            print("✅ Limpieza completada. Ejecuta 'python db_setup.py init' para comenzar de nuevo.")
        except Exception as e:
            print(f"❌ Error durante la limpieza: {e}")
    else:
        print("Operación cancelada")

if __name__ == '__main__':
    cli()
