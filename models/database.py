from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()

def init_db(app):
    """Inicializar la base de datos"""
    db.init_app(app)
    
    with app.app_context():
        try:
            db.create_all()
        except SQLAlchemyError as e:
            app.logger.error(f"Error inicializando la base de datos: {str(e)}")
            raise

def reset_db():
    """Limpiar todas las tablas"""
    for table in reversed(db.metadata.sorted_tables):
        try:
            db.session.execute(table.delete())
        except:
            db.session.rollback()
            raise
    db.session.commit()

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
