# models/category.py
from extensions import db

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # "income" or "expense"
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # optional, so defaults can exist globally

    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True)

