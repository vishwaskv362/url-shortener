from app import db
from datetime import datetime


class URL(db.Model):
    """URL model for storing original and shortened URLs."""
    
    __tablename__ = 'urls'
    
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.Text, nullable=False)
    short_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    click_count = db.Column(db.Integer, default=0)
    
    # Relationship with clicks
    clicks = db.relationship('Click', backref='url', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<URL {self.short_code}: {self.original_url}>'
    
    def to_dict(self):
        """Convert URL object to dictionary."""
        return {
            'id': self.id,
            'original_url': self.original_url,
            'short_code': self.short_code,
            'short_url': f"{self.short_code}",  # Will be prefixed with base URL in service
            'custom': self.custom,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'click_count': self.click_count
        }


class Click(db.Model):
    """Click model for tracking analytics."""
    
    __tablename__ = 'clicks'
    
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'), nullable=False)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text)
    referer = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Click {self.id} for URL {self.url_id}>'
    
    def to_dict(self):
        """Convert Click object to dictionary."""
        return {
            'id': self.id,
            'url_id': self.url_id,
            'clicked_at': self.clicked_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'referer': self.referer
        }
