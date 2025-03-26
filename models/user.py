from .database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campos para DocuSign
    docusign_access_token = db.Column(db.String(500), nullable=True)
    docusign_refresh_token = db.Column(db.String(500), nullable=True)
    docusign_token_expires = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Establece el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
