from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = 'user'  # Table name in MySQL
    id = db.Column(db.Integer, primary_key=True)  # Primary key (auto-increment ID)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    transactions = db.relationship('Transaction', backref='user')
    budgets = db.relationship('Budget', backref='user')
    

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    transactions = db.relationship('Transaction', backref='category')
    budgets = db.relationship('Budget', backref='category')

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10))  # "income" or "expense"
    amount = db.Column(db.Float)
    date = db.Column(db.Date)
    note = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Link to user
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))  # Link to category

class Budget(db.Model):
    __tablename__ = 'budget'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    period = db.Column(db.String(50))  # Monthly, Weekly, etc.
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
