from datetime import datetime
from extensions import db

class Investment(db.Model):
    __tablename__ = 'investment'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    investment_type = db.Column(db.String(50), nullable=False)  # mutual_fund, fixed_deposit, share
    amount = db.Column(db.Float, nullable=False)

    units = db.Column(db.Float, nullable=True)
    purchase_price = db.Column(db.Float, nullable=True)
    current_value = db.Column(db.Float, nullable=True)

    purchase_date = db.Column(db.Date, nullable=True)
    maturity_date = db.Column(db.Date, nullable=True)
    interest_rate = db.Column(db.Float, nullable=True)

    ticker_or_isin = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default='active')  # active, matured, sold

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    #  Define relationship
    user = db.relationship('User', backref='investments', lazy=True)

    def __repr__(self):
        return f"<Investment {self.name} ({self.investment_type})>"
