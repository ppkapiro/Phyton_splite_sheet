from .database import db
from datetime import datetime

class Document(db.Model):
    """Modelo para documentos que requieren firma DocuSign"""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512))
    envelope_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(50), default='draft')  # draft, sent, delivered, signed, completed, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('documents', lazy=True))
    
    def __repr__(self):
        return f'<Document {self.title}>'
