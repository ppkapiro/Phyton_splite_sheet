from flask_sqlalchemy import SQLAlchemy
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

db = SQLAlchemy()

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
    """Inicialización única y centralizada de SQLAlchemy."""
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        db.init_app(app)
        with app.app_context():
            # Verificar conexión
            db.engine.connect().close()
    return db

def init_db(app):
    """
    Inicializa la base de datos y crea las tablas.
    Este es el punto de entrada principal para la inicialización de la BD.
    """
    if not db.get_app():
        init_app(app)
    
    with app.app_context():
        db.create_all()
        current_app.logger.info("Base de datos inicializada correctamente")
    
    return db

# Importar modelos para evitar importación circular
from .user import User
from .agreement import Agreement
from .document import Document

# Funciones de utilidad para base de datos
def create_tables(app):
    """Crea todas las tablas en la base de datos"""
    with app.app_context():
        db.create_all()

def drop_tables(app):
    """Elimina todas las tablas de la base de datos"""
    with app.app_context():
        db.drop_all()

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

__all__ = ['db', 'init_app', 'session_scope', 'create_tables', 'drop_tables']
