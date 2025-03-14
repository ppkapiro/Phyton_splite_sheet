from .database import db, session_scope

class BaseModel:
    """Clase base con gestión segura de sesiones."""
    
    @classmethod
    def create(cls, **kwargs):
        with session_scope() as session:
            instance = cls(**kwargs)
            session.add(instance)
            session.flush()  # Asegurar ID generado
            return instance

    @classmethod
    def get_by_id(cls, id):
        with session_scope() as session:
            return session.query(cls).get(id)
