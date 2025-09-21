
from extensions import db
from datetime import datetime

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  
    note = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔹 Recurring fields
    is_recurring = db.Column(db.Boolean, default=False)   
    frequency = db.Column(db.String(20), nullable=True)   
    next_date = db.Column(db.DateTime, nullable=True)     

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount}>"
