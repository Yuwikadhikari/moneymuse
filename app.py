# app.py
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask import request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask import session
from datetime import datetime, timedelta
from sqlalchemy import extract
from sqlalchemy.sql.sqltypes import Date
from collections import defaultdict
from flask_login import login_required, current_user
from models import Transaction
from sqlalchemy import func
from functools import wraps




from extensions import db

# Load .env variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db
db.init_app(app)

# Import models after initializing db
with app.app_context():
    from models import User, Category, Transaction, Budget, Investment, ContactMessage
    db.create_all()   #  stays inside app.app_context()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not email.endswith("@gmail.com"):
            flash("Only @gmail.com emails are allowed!", "danger")
            return redirect(url_for('register'))
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')

            #  Redirect admins to admin dashboard
            if user.role == "admin":
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

from sqlalchemy import extract, func

# Dashboard Page (Profile + Summary + Charts)
@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])

    # ---- Totals ----
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    # ---- Income vs Expense per month (for Bar chart) ----
    monthly_data = (
        db.session.query(
            extract('month', Transaction.date).label('month'),
            Transaction.type,
            func.sum(Transaction.amount).label('total')
        )
        .filter(Transaction.user_id == user.id)
        .group_by('month', Transaction.type)
        .all()
    )

    months = []
    income_data = []
    expense_data = []

    for m in range(1, 13):
        months.append(m)
        income = next((d.total for d in monthly_data if d.month == m and d.type == "income"), 0)
        expense = next((d.total for d in monthly_data if d.month == m and d.type == "expense"), 0)
        income_data.append(float(income))
        expense_data.append(float(expense))

    # ---- Balance Trend ----
    balance_data = []
    for i in range(12):
        income = income_data[i]
        expense = expense_data[i]
        balance_data.append(income - expense)

    # ---- Expenses by Category (for Pie chart) ----
    expenses_by_category = (
        db.session.query(Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.type == "expense", Transaction.user_id == user.id)
        .group_by(Category.name)
        .all()
    )

    categories = [c[0] for c in expenses_by_category]
    amounts = [float(c[1]) for c in expenses_by_category]

    return render_template(
        'dashboard.html',
        user=user,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        months=months,
        income_data=income_data,
        expense_data=expense_data,
        balance_data=balance_data,   
        categories=categories,
        amounts=amounts
    )


@app.route('/transactions')
@login_required
def transactions_page():
    user = db.session.get(User, session['user_id'])

    filter_by = request.args.get('filter_by', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Transaction.query.filter_by(user_id=user.id)

    now = datetime.utcnow() + timedelta(hours=5, minutes=45)

    if filter_by == 'today':
        query = query.filter(db.func.date(Transaction.date) == now.date())

    elif filter_by == 'month':
        query = query.filter(
            extract('year', Transaction.date) == now.year,
            extract('month', Transaction.date) == now.month
        )

    elif filter_by == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Transaction.date >= start, Transaction.date < end)
        except ValueError:
            flash('Invalid date format.', 'error')

    transactions = query.order_by(Transaction.date.desc()).all()

    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")

    expenses_by_category = (
        db.session.query(Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.type == "expense", Transaction.user_id == user.id)
        .group_by(Category.name)
        .all()
    )

    categories = [c[0] for c in expenses_by_category] if expenses_by_category else []
    amounts = [float(c[1]) for c in expenses_by_category] if expenses_by_category else []

    all_categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user.id)
    ).all()

    return render_template(
        'transactions.html',
        user=user,
        transactions=transactions,
        filter_by=filter_by,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        amounts=amounts,
        total_income=total_income,
        total_expense=total_expense,
        all_categories=all_categories
    )

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    amount = float(request.form['amount'])
    t_type = request.form['type']
    note = request.form.get('note')
    category_id = int(request.form['category_id'])
    nepal_time = datetime.utcnow() + timedelta(hours=5, minutes=45)

    is_recurring = request.form.get('is_recurring') == "yes"
    frequency = request.form.get('frequency') if is_recurring else None

    transaction = Transaction(
        amount=amount,
        type=t_type,
        note=note,
        date=nepal_time,
        user_id=session['user_id'],
        category_id=category_id,
        is_recurring=is_recurring,
        frequency=frequency,
        next_date=(nepal_time + timedelta(days=1) if frequency == "daily"
                   else nepal_time + timedelta(weeks=1) if frequency == "weekly"
                   else nepal_time + timedelta(days=30) if frequency == "monthly"
                   else None)
    )

    db.session.add(transaction)
    db.session.commit()

    flash("Transaction added successfully!", "success")
    return redirect(url_for('transactions_page'))

@app.before_request
def handle_recurring():
    if 'user_id' not in session:
        return

    user_id = session['user_id']
    now = datetime.utcnow() + timedelta(hours=5, minutes=45)

    recurs = Transaction.query.filter_by(user_id=user_id, is_recurring=True).all()
    for t in recurs:
        if t.next_date and now.date() >= t.next_date.date():
            
            #  Check if already added today for this recurring transaction
            existing = Transaction.query.filter_by(
                user_id=t.user_id,
                type=t.type,
                amount=t.amount,
                note=t.note,
                date=now.date()
            ).first()
            if existing:
                continue  

            # Create new recurring transaction
            new_t = Transaction(
                amount=t.amount,
                type=t.type,
                note=f"(Recurring) {t.note or ''}",
                date=now,
                user_id=t.user_id,
                category_id=t.category_id,
                is_recurring=True,
                frequency=t.frequency,
            )

            # Set next_date for new transaction
            if t.frequency == "daily":
                new_t.next_date = now + timedelta(days=1)
            elif t.frequency == "weekly":
                new_t.next_date = now + timedelta(weeks=1)
            elif t.frequency == "monthly":
                new_t.next_date = now + timedelta(days=30)

            #  Update old transaction's next_date first
            t.next_date = new_t.next_date  

            db.session.add(new_t)

    db.session.commit()



@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form['name']
    c_type = request.form['type']

    # check if category already exists
    existing = Category.query.filter_by(name=name, type=c_type, user_id=session['user_id']).first()
    if existing:
        flash("Category already exists!", "warning")
        return redirect(url_for('transactions_page'))

    # create new category
    new_category = Category(name=name, type=c_type, user_id=session['user_id'])
    db.session.add(new_category)
    db.session.commit()

    flash("New category added!", "success")
    return redirect(url_for('transactions_page'))

def seed_default_categories():
    defaults = [
        {"name": "Salary", "type": "income"},
        {"name": "Food", "type": "expense"},
        {"name": "Rent", "type": "expense"},
        {"name": "Travel", "type": "expense"},
        {"name": "Other", "type": "expense"},
    ]
    for cat in defaults:
        exists = Category.query.filter_by(name=cat["name"], type=cat["type"], user_id=None).first()
        if not exists:
            db.session.add(Category(name=cat["name"], type=cat["type"], user_id=None))
    db.session.commit()

import csv
import io
from flask import Response

@app.route('/export_transactions')
@login_required
def export_transactions():
    user = db.session.get(User, session['user_id'])
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.date.desc()).all()

    # Use StringIO to write CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(["ID", "Date", "Type", "Amount", "Category", "Note"])

    # Write transaction rows
    for t in transactions:
        writer.writerow([
            t.id,
            t.date.strftime("%Y-%m-%d %H:%M"),
            t.type.capitalize(),
            t.amount,
            t.category.name if t.category else "N/A",
            t.note or ""
        ])

    # Move cursor back to start
    output.seek(0)

    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=transactions.csv"})

@app.route('/investments')
@login_required
def investments():
    user_id = session['user_id']

    fixed_deposits = Investment.query.filter_by(user_id=user_id, investment_type="fixed_deposit").all()
    mutual_funds = Investment.query.filter_by(user_id=user_id, investment_type="mutual_fund").all()
    shares = Investment.query.filter_by(user_id=user_id, investment_type="share").all()

    total_fd = sum(fd.amount for fd in fixed_deposits)
    total_mutual = sum(mf.current_value or 0 for mf in mutual_funds)
    total_shares = sum(s.current_value or 0 for s in shares)

    return render_template(
        "investments.html",
        fixed_deposits=fixed_deposits,
        mutual_funds=mutual_funds,
        shares=shares,
        total_fd=total_fd,
        total_mutual=total_mutual,
        total_shares=total_shares
    )

@app.route('/add_investment', methods=['POST'])
@login_required
def add_investment():
    user_id = session['user_id']
    inv_type = request.form['investment_type']
    name = request.form['name']
    notes = request.form.get('notes')

    investment = Investment(
        user_id=user_id,
        investment_type=inv_type,
        name=name,
        notes=notes
    )

    # Handle fields depending on type
    if inv_type == "fixed_deposit":
        investment.amount = float(request.form['amount'])
        investment.interest_rate = float(request.form.get('rate', 0))
        if request.form.get('maturity_date'):
            investment.maturity_date = datetime.strptime(request.form['maturity_date'], "%Y-%m-%d")

    elif inv_type == "mutual_fund":
        investment.units = float(request.form.get('units', 0))
        investment.purchase_price = float(request.form.get('nav', 0))
        investment.current_value = float(request.form.get('current_value', 0))
        investment.amount = investment.current_value  # for summary totals

    elif inv_type == "share":
        investment.units = float(request.form.get('quantity', 0))
        investment.purchase_price = float(request.form.get('price', 0))
        investment.current_value = float(request.form.get('total_value', 0))
        investment.amount = investment.current_value  # for summary totals

    db.session.add(investment)
    db.session.commit()

    flash(f"{inv_type.replace('_',' ').title()} added successfully!", "success")
    return redirect(url_for('investments'))


# About Page Route
@app.route('/about')
def about():
    return render_template('about.html')

# Contact Page Route

from datetime import datetime, timedelta

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Convert to Nepal time (UTC + 5:45)
        nepal_time = datetime.utcnow() + timedelta(hours=5, minutes=45)

        new_message = ContactMessage(
            name=name,
            email=email,
            message=message,
            date_sent=nepal_time
        )
        db.session.add(new_message)
        db.session.commit()

        flash("Your message has been sent successfully!", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')


# ------------------ Budget Routes ------------------
@app.route('/budgets')
@login_required
def budgets():
    user = db.session.get(User, session['user_id'])
    budgets = Budget.query.filter_by(user_id=user.id).all()
    all_categories = Category.query.all()

    budget_progress = []
    total_spent = 0

    for b in budgets:
        spent = (
            db.session.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user.id, Transaction.category_id == b.category_id, Transaction.type == "expense")
            .scalar()
        ) or 0

        progress = int((spent / b.amount) * 100) if b.amount else 0
        exceeded = spent > b.amount

        budget_progress.append({
            "budget": b,
            "spent": spent,
            "progress": progress,
            "exceeded": exceeded
        })

        total_spent += spent

    total_budget = sum(b.amount for b in budgets)

    return render_template(
        "budgets.html",
        user=user,
        budgets=budgets,
        budget_progress=budget_progress,
        total_budget=total_budget,
        total_spent=total_spent,
        all_categories=all_categories
    )


@app.route('/add_budget', methods=['POST'])
@login_required
def add_budget():
    user = db.session.get(User, session['user_id'])
    name = request.form['name']
    amount = float(request.form['amount'])
    period = request.form['period']
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    category_name = request.form['category']

    # ✅ Require valid category
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        flash("⚠️ Invalid category. Please choose an existing category.", "danger")
        return redirect(url_for('budgets'))

    budget = Budget(
        name=name,
        amount=amount,
        period=period,
        start_date=datetime.strptime(start_date, '%Y-%m-%d') if start_date else None,
        end_date=datetime.strptime(end_date, '%Y-%m-%d') if end_date else None,
        user_id=user.id,
        category_id=category.id
    )
    db.session.add(budget)
    db.session.commit()

    flash("✅ Budget added successfully!", "success")
    return redirect(url_for('budgets'))


# ------------------ Edit Budget ------------------
@app.route('/edit_budget/<int:budget_id>', methods=['POST'])
@login_required
def edit_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)

    if budget.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('budgets'))

    budget.name = request.form['name']
    budget.amount = float(request.form['amount'])
    budget.period = request.form['period']

    db.session.commit()
    flash("Budget updated successfully!", "success")
    return redirect(url_for('budgets'))


# ------------------ Delete Budget ------------------
@app.route('/delete_budget/<int:budget_id>', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)

    if budget.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('budgets'))

    db.session.delete(budget)
    db.session.commit()
    flash("Budget deleted successfully!", "success")
    return redirect(url_for('budgets'))


from flask import abort

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))

        user = User.query.get(user_id)
        if not user or user.role != "admin":
            flash("Unauthorized access! Admins only.", "danger")
            return redirect(url_for('dashboard'))  # or abort(403)

        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    total_users = User.query.count()
    total_messages = ContactMessage.query.count()
    total_admins = User.query.filter_by(role="admin").count()

    return render_template(
        'admin_dashboard.html',
        users=users,
        total_users=total_users,
        total_messages=total_messages,
        total_admins=total_admins
    )


@app.route('/admin/messages')
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.date_sent.desc()).all()
    return render_template('admin_messages.html', messages=messages)

# @app.route('/admin/messages')
# @admin_required
# def admin_messages():
#     messages = ContactMessage.query.order_by(ContactMessage.id.desc()).all()
#     return render_template("admin_messages.html", messages=messages, user=User.query.get(session['user_id']))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # prevent admin from deleting themselves
    if user.id == session.get("user_id"):
        flash("You cannot delete your own account!", "danger")
        return redirect(url_for('admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted successfully!", "success")
    return redirect(url_for('admin_users'))


@app.route('/admin/user/<int:user_id>/toggle_role', methods=['POST'])
@admin_required
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        user.role = "user"
    else:
        user.role = "admin"

    db.session.commit()
    flash(f"User {user.username} role updated to {user.role}!", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/messages/delete/<int:msg_id>', methods=['POST'])
@admin_required
def delete_message(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted successfully!", "success")
    return redirect(url_for('admin_messages'))


if __name__ == "__main__":
    with app.app_context():
        seed_default_categories()
    app.run(debug=True)


