"""
app.py — SmartSpend Flask application.
Expense tracking, budget recommendations, savings goals, and financial health scoring.
"""

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
import json

import database as db

app = Flask(__name__)
app.secret_key = 'smartspend_secret_key_2024'

# Expense categories
CATEGORIES = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Education', 'Others']

# Category icons (Bootstrap Icons class names)
CATEGORY_ICONS = {
    'Food': 'bi-egg-fried',
    'Transport': 'bi-bus-front',
    'Shopping': 'bi-bag',
    'Bills': 'bi-receipt',
    'Entertainment': 'bi-controller',
    'Education': 'bi-book',
    'Others': 'bi-three-dots',
}

# Category colors for charts
CATEGORY_COLORS = {
    'Food': '#FF6B6B',
    'Transport': '#4ECDC4',
    'Shopping': '#45B7D1',
    'Bills': '#96CEB4',
    'Entertainment': '#FECA57',
    'Education': '#a29bfe',
    'Others': '#fd79a8',
}


# ---------------------------------------------------------------------------
# Initialize database on startup
# ---------------------------------------------------------------------------
with app.app_context():
    db.init_db()


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------
def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = db.get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Welcome back, {}!'.format(user['name']), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Validation
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif db.get_user_by_email(email):
            flash('Email already registered.', 'danger')
        else:
            password_hash = generate_password_hash(password)
            user_id = db.create_user(name, email, password_hash)
            session['user_id'] = user_id
            session['user_name'] = name
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    today = date.today()
    current_month = today.month
    current_year = today.year

    # Summary data
    total_income = db.get_total_income(user_id, current_month, current_year)
    total_expenses = db.get_total_expenses(user_id, current_month, current_year)
    savings = total_income - total_expenses

    # Category-wise data for pie chart
    category_data = db.get_category_totals(user_id, current_month, current_year)
    cat_labels = [row['category'] for row in category_data]
    cat_values = [row['total'] for row in category_data]
    cat_colors = [CATEGORY_COLORS.get(c, '#95a5a6') for c in cat_labels]

    # Monthly data for bar chart (last 6 months)
    expense_monthly, income_monthly = db.get_monthly_totals(user_id)
    # Build aligned data (exclude None values to prevent strptime errors)
    all_months = sorted(set(
        [r['month'] for r in expense_monthly if r['month']] +
        [r['month'] for r in income_monthly if r['month']]
    ))[-6:]

    expense_map = {r['month']: r['total'] for r in expense_monthly if r['month']}
    income_map = {r['month']: r['total'] for r in income_monthly if r['month']}

    month_labels = []
    for m in all_months:
        try:
            month_labels.append(datetime.strptime(m, '%Y-%m').strftime('%b %Y'))
        except ValueError:
            month_labels.append(m)

    month_expenses = [expense_map.get(m, 0) for m in all_months]
    month_incomes = [income_map.get(m, 0) for m in all_months]

    # Recent transactions
    recent_expenses = db.get_expenses(user_id)[:5]

    # Financial health score
    health_score = calculate_health_score(user_id, current_month, current_year)

    # Budget alerts
    alerts = get_budget_alerts(user_id, current_month, current_year)

    return render_template(
        'dashboard.html',
        total_income=total_income,
        total_expenses=total_expenses,
        savings=savings,
        health_score=health_score,
        cat_labels=json.dumps(cat_labels),
        cat_values=json.dumps(cat_values),
        cat_colors=json.dumps(cat_colors),
        month_labels=json.dumps(month_labels),
        month_expenses=json.dumps(month_expenses),
        month_incomes=json.dumps(month_incomes),
        recent_expenses=recent_expenses,
        category_icons=CATEGORY_ICONS,
        category_colors=CATEGORY_COLORS,
        alerts=alerts,
        current_month=today.strftime('%B %Y'),
    )


# ---------------------------------------------------------------------------
# Expense CRUD
# ---------------------------------------------------------------------------

@app.route('/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '').strip()
        expense_date = request.form.get('date', str(date.today()))

        if category not in CATEGORIES:
            flash('Invalid category.', 'danger')
        elif amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
        else:
            db.add_expense(session['user_id'], category, amount, description, expense_date)
            flash('Expense added successfully!', 'success')
            return redirect(url_for('expenses'))

    return render_template('add_expense.html', categories=CATEGORIES,
                           category_icons=CATEGORY_ICONS, category_colors=CATEGORY_COLORS,
                           today=str(date.today()))


@app.route('/expenses')
@login_required
def expenses():
    user_id = session['user_id']
    month_filter = request.args.get('month')
    category_filter = request.args.get('category')

    filter_month = None
    filter_year = None
    if month_filter:
        try:
            parts = month_filter.split('-')
            filter_year = int(parts[0])
            filter_month = int(parts[1])
        except (ValueError, IndexError):
            pass

    expense_list = db.get_expenses(
        user_id,
        month=filter_month,
        year=filter_year,
        category=category_filter if category_filter else None,
    )

    return render_template(
        'expenses.html',
        expenses=expense_list,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS,
        category_colors=CATEGORY_COLORS,
        month_filter=month_filter or '',
        category_filter=category_filter or '',
    )


@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    user_id = session['user_id']
    expense = db.get_expense_by_id(expense_id, user_id)

    if not expense:
        flash('Expense not found.', 'danger')
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '').strip()
        expense_date = request.form.get('date')

        if category not in CATEGORIES:
            flash('Invalid category.', 'danger')
        elif amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
        else:
            db.update_expense(expense_id, user_id, category, amount, description, expense_date)
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('expenses'))

    return render_template('edit_expense.html', expense=expense,
                           categories=CATEGORIES, category_icons=CATEGORY_ICONS)


@app.route('/delete-expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def delete_expense_route(expense_id):
    db.delete_expense(expense_id, session['user_id'])
    flash('Expense deleted.', 'info')
    return redirect(url_for('expenses'))


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------

@app.route('/add-income', methods=['GET', 'POST'])
@login_required
def add_income():
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        source = request.form.get('source', '').strip()
        income_date = request.form.get('date', str(date.today()))

        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
        elif not source:
            flash('Please enter an income source.', 'danger')
        else:
            db.add_income(session['user_id'], amount, source, income_date)
            flash('Income added successfully!', 'success')
            return redirect(url_for('add_income'))

    incomes = db.get_incomes(session['user_id'])
    return render_template('add_income.html', incomes=incomes, today=str(date.today()))


@app.route('/delete-income/<int:income_id>', methods=['GET', 'POST'])
@login_required
def delete_income_route(income_id):
    db.delete_income(income_id, session['user_id'])
    flash('Income deleted.', 'info')
    return redirect(url_for('add_income'))


# ---------------------------------------------------------------------------
# Budget Recommendations
# ---------------------------------------------------------------------------

def calculate_recommendations(user_id):
    """
    Rule-based budget recommendation engine.
    - If avg spending increased >20%: recommend current average (cap it)
    - If spending decreased: recommend avg - 10%
    - Otherwise: recommend the average
    """
    recommendations = []
    category_avgs = db.get_category_averages(user_id)

    total_income = db.get_total_income(user_id)
    total_expenses = db.get_total_expenses(user_id)

    for row in category_avgs:
        category = row['category']
        avg = row['avg_amount']
        num_months = row['num_months']

        # Get last 2 months of data to determine trend
        monthly_data = db.get_category_monthly_spending(user_id, category)
        monthly_values = [r['total'] for r in monthly_data if r['total'] is not None]

        recommended = avg
        status = 'stable'

        if len(monthly_values) >= 2:
            latest = monthly_values[0]
            previous = monthly_values[1]

            if previous > 0:
                change_pct = ((latest - previous) / previous) * 100

                if change_pct > 20:
                    # Spending increased significantly — cap at average
                    recommended = avg
                    status = 'increase'
                elif change_pct < -5:
                    # Spending decreased — reduce recommendation
                    recommended = avg * 0.9
                    status = 'decrease'
                else:
                    recommended = avg
                    status = 'stable'

        recommendations.append({
            'category': category,
            'avg_spending': round(avg, 2),
            'recommended': round(recommended, 2),
            'status': status,
            'num_months': num_months,
        })

    overspending = total_expenses > total_income if total_income > 0 else False

    return recommendations, overspending


@app.route('/recommendations')
@login_required
def recommendations():
    user_id = session['user_id']
    recs, overspending = calculate_recommendations(user_id)

    total_income = db.get_total_income(user_id)
    total_expenses = db.get_total_expenses(user_id)
    total_recommended = sum(r['recommended'] for r in recs)

    return render_template(
        'recommendations.html',
        recommendations=recs,
        overspending=overspending,
        total_income=total_income,
        total_expenses=total_expenses,
        total_recommended=total_recommended,
        category_icons=CATEGORY_ICONS,
        category_colors=CATEGORY_COLORS,
    )


# ---------------------------------------------------------------------------
# Savings Goals
# ---------------------------------------------------------------------------

@app.route('/savings-goals', methods=['GET', 'POST'])
@login_required
def savings_goals():
    user_id = session['user_id']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            goal_name = request.form.get('goal_name', '').strip()
            target = float(request.form.get('target_amount', 0))
            deadline = request.form.get('deadline', '')

            if not goal_name or target <= 0:
                flash('Please enter a valid goal name and target amount.', 'danger')
            else:
                db.add_savings_goal(user_id, goal_name, target, deadline if deadline else None)
                flash('Savings goal created!', 'success')

        elif action == 'add_funds':
            goal_id = int(request.form.get('goal_id', 0))
            amount = float(request.form.get('fund_amount', 0))
            if amount > 0:
                db.update_savings_goal_amount(goal_id, user_id, amount)
                flash(f'₹{amount:,.2f} added to your goal!', 'success')

        elif action == 'delete':
            goal_id = int(request.form.get('goal_id', 0))
            db.delete_savings_goal(goal_id, user_id)
            flash('Goal deleted.', 'info')

        return redirect(url_for('savings_goals'))

    goals = db.get_savings_goals(user_id)

    # Expense challenge data
    today = date.today()
    monthly_expenses = db.get_category_totals(user_id, today.month, today.year)
    challenges = []
    challenge_targets = {
        'Entertainment': 2000,
        'Shopping': 3000,
        'Food': 5000,
    }
    for cat, target in challenge_targets.items():
        spent = 0
        for row in monthly_expenses:
            if row['category'] == cat:
                spent = row['total']
                break
        pct = min((spent / target) * 100, 100) if target > 0 else 0
        challenges.append({
            'category': cat,
            'target': target,
            'spent': spent,
            'remaining': max(target - spent, 0),
            'percentage': round(pct, 1),
            'success': spent <= target,
        })

    return render_template('savings_goals.html', goals=goals, challenges=challenges,
                           category_icons=CATEGORY_ICONS, category_colors=CATEGORY_COLORS)


@app.route('/delete-savings-goal/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def delete_savings_goal_route(goal_id):
    db.delete_savings_goal(goal_id, session['user_id'])
    flash('Savings goal deleted.', 'info')
    return redirect(url_for('savings_goals'))


# ---------------------------------------------------------------------------
# Financial Health Score
# ---------------------------------------------------------------------------

def calculate_health_score(user_id, month, year):
    """
    Financial Health Score (0-100).
    - Savings Rate (40%): higher savings = better score
    - Expense Control (30%): spending within limits
    - Budget Adherence (30%): following past recommendations
    """
    total_income = db.get_total_income(user_id, month, year)
    total_expenses = db.get_total_expenses(user_id, month, year)

    if total_income == 0:
        return 50  # Neutral score if no income data

    # 1. Savings Rate Score (0-40)
    savings_rate = (total_income - total_expenses) / total_income
    if savings_rate >= 0.3:
        savings_score = 40
    elif savings_rate >= 0.2:
        savings_score = 35
    elif savings_rate >= 0.1:
        savings_score = 28
    elif savings_rate >= 0:
        savings_score = 20
    else:
        savings_score = max(0, 10 + savings_rate * 20)

    # 2. Expense Control Score (0-30)
    expense_ratio = total_expenses / total_income
    if expense_ratio <= 0.5:
        control_score = 30
    elif expense_ratio <= 0.7:
        control_score = 25
    elif expense_ratio <= 0.9:
        control_score = 18
    elif expense_ratio <= 1.0:
        control_score = 10
    else:
        control_score = max(0, 5 - (expense_ratio - 1) * 10)

    # 3. Budget Adherence Score (0-30)
    recs, _ = calculate_recommendations(user_id)
    if recs:
        category_totals = db.get_category_totals(user_id, month, year)
        cat_map = {r['category']: r['total'] for r in category_totals}

        adherence_scores = []
        for rec in recs:
            actual = cat_map.get(rec['category'], 0)
            recommended = rec['recommended']
            if recommended > 0:
                ratio = actual / recommended
                if ratio <= 1.0:
                    adherence_scores.append(1.0)
                elif ratio <= 1.2:
                    adherence_scores.append(0.7)
                else:
                    adherence_scores.append(max(0, 1 - (ratio - 1)))

        if adherence_scores:
            adherence_score = (sum(adherence_scores) / len(adherence_scores)) * 30
        else:
            adherence_score = 15
    else:
        adherence_score = 15  # Neutral if no recommendations yet

    total_score = round(savings_score + control_score + adherence_score)
    return min(100, max(0, total_score))


def get_budget_alerts(user_id, month, year):
    """Generate alert messages for the dashboard."""
    alerts = []
    total_income = db.get_total_income(user_id, month, year)
    total_expenses = db.get_total_expenses(user_id, month, year)

    if total_income > 0 and total_expenses > total_income:
        alerts.append({
            'type': 'danger',
            'icon': 'bi-exclamation-triangle-fill',
            'message': 'You have exceeded your monthly income! Consider reducing expenses.',
        })

    if total_income > 0 and total_expenses > total_income * 0.9:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-exclamation-circle-fill',
            'message': 'You have spent over 90% of your income this month.',
        })

    # Check individual category overspending
    recs, _ = calculate_recommendations(user_id)
    category_totals = db.get_category_totals(user_id, month, year)
    cat_map = {r['category']: r['total'] for r in category_totals}

    for rec in recs:
        actual = cat_map.get(rec['category'], 0)
        if rec['recommended'] > 0 and actual > rec['recommended'] * 1.2:
            alerts.append({
                'type': 'warning',
                'icon': 'bi-exclamation-circle',
                'message': f"You've exceeded your {rec['category']} budget by ₹{actual - rec['recommended']:,.0f}.",
            })

    return alerts[:5]  # Limit to 5 alerts


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
