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

def add_user(username: str, password: str):
    from .user import User
    try:
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    except SQLAlchemyError as e:
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

__all__ = ['db', 'init_app', 'session_scope', 'create_tables', 'drop_tables']
