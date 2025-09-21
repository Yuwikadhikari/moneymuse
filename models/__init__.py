from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .category import Category
from .transaction import Transaction
from .budget import Budget
from .investment import Investment 
from .contact import ContactMessage  
