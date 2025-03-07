from .database import db
from datetime import datetime

participants_table = db.Table('participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('agreement_id', db.Integer, db.ForeignKey('agreement.id'), primary_key=True)
)

class Agreement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    pdf_url = db.Column(db.String(255))
    signature_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    participants = db.relationship('User', 
                                 secondary=participants_table,
                                 lazy='subquery',
                                 backref=db.backref('agreements', lazy=True))
    
    def __repr__(self):
        return f'<Agreement {self.title}>'
