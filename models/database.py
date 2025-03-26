from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import current_app
import logging
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path

db = SQLAlchemy()
migrate = Migrate()

@contextmanager
def session_scope():
    """Contexto seguro para manejo de sesiones."""
    session = db.session()
    try:
        yield session
        # Solo hacer commit si la sesión no ha sido cerrada
        if session.is_active:
            session.commit()
    except:
        # Solo hacer rollback si la sesión no ha sido cerrada
        if session.is_active:
            session.rollback()
        raise
    finally:
        # Asegurarse de que la sesión se cierra siempre
        try:
            session.close()
        except:
            # Si hay error al cerrar, ignorarlo y continuar
            pass

def init_app(app):
    """Inicializa la base de datos y las migraciones con la aplicación."""
    db.init_app(app)
    migrate.init_app(app, db)
    return db

# Importar modelos para evitar importación circular
from .user import User
from .agreement import Agreement
from .document import Document

def create_tables(app):
    """
    Crea tablas solo en modo testing.
    En producción/desarrollo, usar migraciones.
    """
    if not (app.config.get('TESTING', False) or app.config.get('ENV') == 'testing'):
        app.logger.warning(
            "create_tables() solo debe usarse en testing. "
            "En producción, use 'flask db upgrade'"
        )
        return False
        
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Tablas creadas (modo testing)")
            return True
        except Exception as e:
            app.logger.error(f"Error creando tablas: {str(e)}")
            return False

def drop_tables(app):
    """
    Elimina todas las tablas.
    ¡PRECAUCIÓN! Solo usar en testing o desarrollo.
    """
    if not app.config.get('TESTING', False):
        app.logger.warning(
            "⚠️ Intentando eliminar tablas en modo producción/desarrollo. "
            "Use 'flask db downgrade' para gestionar schema"
        )
        return
        
    with app.app_context():
        db.drop_all()
        app.logger.info("Tablas eliminadas (modo testing)")

def reset_db():
    """Limpiar todas las tablas de forma segura."""
    with session_scope() as session:
        for table in reversed(db.metadata.sorted_tables):
            session.execute(table.delete())

def add_user(username, password, email=None):
    """
    Crea un nuevo usuario en la base de datos.
    
    Args:
        username (str): Nombre de usuario único
        password (str): Contraseña no encriptada
        email (str, opcional): Email del usuario. Si no se proporciona, se genera uno basado en el username
        
    Returns:
        User: El objeto usuario creado
        
    Raises:
        ValueError: Si hay errores en la creación
    """
    try:
        from models.user import User
        
        # Si no se proporciona email, generar uno basado en el username
        if email is None:
            email = f"{username}@example.com"
        
        # Crear instancia de usuario
        user = User(username=username, email=email)
        user.set_password(password)
        
        # Agregar a la sesión y confirmar
        db.session.add(user)
        db.session.commit()
        
        return user
    except Exception as e:
        # Revertir cambios en caso de error
        db.session.rollback()
        raise ValueError(f"Error al crear usuario: {str(e)}")

def add_agreement(title: str, participants: list, pdf_url: str):
    from .agreement import Agreement
    try:
        agreement = Agreement(
            title=title,
            pdf_url=pdf_url,
            signature_status='pending'
        )
        agreement.participants = participants
        db.session.add(agreement)
        db.session.commit()
        return agreement
    except SQLAlchemyError as e:
        db.session.rollback()
        raise ValueError(f"Error al crear acuerdo: {str(e)}")

def get_user(username: str):
    from .user import User
    return User.query.filter_by(username=username).first()

def get_agreement(agreement_id: int):
    from .agreement import Agreement
    return Agreement.query.get(agreement_id)

def save_docusign_tokens(user_id: int, access_token: str, refresh_token: str):
    """Guarda o actualiza los tokens de DocuSign para un usuario"""
    try:
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        user.docusign_access_token = access_token
        user.docusign_refresh_token = refresh_token
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Error guardando tokens: {str(e)}")

def get_document(document_id: int):
    """Obtener documento por ID"""
    return Document.query.get(document_id)

def get_document_by_envelope(envelope_id: str):
    """Obtener documento por envelope_id de DocuSign"""
    return Document.query.filter_by(envelope_id=envelope_id).first()

def verify_migrations():
    """
    Verifica el estado de las migraciones.
    Útil para diagnóstico en desarrollo/producción.
    """
    try:
        from flask import current_app
        from flask_migrate import current
        
        with current_app.app_context():
            migration_ctx = current.get_context()
            if migration_ctx is None:
                return False, "No hay contexto de migración"
                
            head_rev = migration_ctx.get_head_revision()
            current_rev = migration_ctx.get_current_revision()
            
            if head_rev == current_rev:
                return True, "Base de datos actualizada"
            else:
                return False, f"Migraciones pendientes: actual={current_rev}, última={head_rev}"
                
    except Exception as e:
        return False, f"Error verificando migraciones: {str(e)}"

def force_transaction_cleanup(session):
    """Helper mejorado para forzar limpieza de transacciones activas."""
    try:
        # 1. Intentar rollback si hay una transacción activa
        if hasattr(session, 'transaction') and session.transaction and getattr(session.transaction, 'is_active', False):
            try:
                session.rollback()
            except Exception as e:
                if current_app:
                    current_app.logger.warning(f"Error en rollback: {str(e)}")
        
        # 2. Cerrar sesión
        try:
            if hasattr(session, 'close'):
                session.close()
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Error cerrando sesión: {str(e)}")
        
        # 3. Remover sesión
        try:
            if hasattr(db, 'session') and hasattr(db.session, 'remove'):
                db.session.remove()
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Error en session.remove(): {str(e)}")
        
        # 4. Limpiar conexiones
        try:
            if hasattr(db, 'engine') and hasattr(db.engine, 'dispose'):
                db.engine.dispose()
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Error en engine.dispose(): {str(e)}")
        
        # 5. Intentar restaurar una sesión limpia
        try:
            if session and hasattr(session, 'transaction') and session.transaction and getattr(session.transaction, 'is_active', False):
                if current_app:
                    current_app.logger.warning("Transacción persistente detectada, intentando recrear la sesión")
                db.session = db.create_scoped_session()
                session = db.session()
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error recreando sesión: {str(e)}")
    
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error en force_transaction_cleanup: {str(e)}")

__all__ = ['db', 'init_app', 'session_scope', 'create_tables', 'drop_tables']
