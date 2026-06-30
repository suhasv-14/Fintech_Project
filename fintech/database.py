"""
database.py — SQLite database initialization and helper functions for SmartSpend.
"""

import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize the database with all required tables."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Income table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            source TEXT NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Budget recommendations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            recommended_amount REAL NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Savings goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Helper query functions
# ---------------------------------------------------------------------------

def get_user_by_email(email):
    """Fetch a user record by email."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    """Fetch a user record by ID."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def create_user(name, email, password_hash):
    """Insert a new user and return the new user ID."""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
        (name, email, password_hash)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


# --- Income helpers --------------------------------------------------------

def add_income(user_id, amount, source, date):
    conn = get_db()
    conn.execute(
        'INSERT INTO income (user_id, amount, source, date) VALUES (?, ?, ?, ?)',
        (user_id, amount, source, date)
    )
    conn.commit()
    conn.close()


def get_incomes(user_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM income WHERE user_id = ? ORDER BY date DESC', (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_total_income(user_id, month=None, year=None):
    conn = get_db()
    if month and year:
        row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total FROM income '
            'WHERE user_id = ? AND strftime("%m", date) = ? AND strftime("%Y", date) = ?',
            (user_id, f'{month:02d}', str(year))
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = ?',
            (user_id,)
        ).fetchone()
    conn.close()
    return row['total']


# --- Expense helpers -------------------------------------------------------

def add_expense(user_id, category, amount, description, date):
    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (user_id, category, amount, description, date) '
        'VALUES (?, ?, ?, ?, ?)',
        (user_id, category, amount, description, date)
    )
    conn.commit()
    conn.close()


def get_expenses(user_id, month=None, year=None, category=None):
    conn = get_db()
    query = 'SELECT * FROM expenses WHERE user_id = ?'
    params = [user_id]

    if month and year:
        query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
        params.extend([f'{month:02d}', str(year)])
    if category:
        query += ' AND category = ?'
        params.append(category)

    query += ' ORDER BY date DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM expenses WHERE id = ? AND user_id = ?',
        (expense_id, user_id)
    ).fetchone()
    conn.close()
    return row


def update_expense(expense_id, user_id, category, amount, description, date):
    conn = get_db()
    conn.execute(
        'UPDATE expenses SET category = ?, amount = ?, description = ?, date = ? '
        'WHERE id = ? AND user_id = ?',
        (category, amount, description, date, expense_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM expenses WHERE id = ? AND user_id = ?',
        (expense_id, user_id)
    )
    conn.commit()
    conn.close()


def get_total_expenses(user_id, month=None, year=None):
    conn = get_db()
    if month and year:
        row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total FROM expenses '
            'WHERE user_id = ? AND strftime("%m", date) = ? AND strftime("%Y", date) = ?',
            (user_id, f'{month:02d}', str(year))
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?',
            (user_id,)
        ).fetchone()
    conn.close()
    return row['total']


def get_category_totals(user_id, month=None, year=None):
    """Return category-wise expense totals."""
    conn = get_db()
    if month and year:
        rows = conn.execute(
            'SELECT category, SUM(amount) as total FROM expenses '
            'WHERE user_id = ? AND strftime("%m", date) = ? AND strftime("%Y", date) = ? '
            'GROUP BY category ORDER BY total DESC',
            (user_id, f'{month:02d}', str(year))
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT category, SUM(amount) as total FROM expenses '
            'WHERE user_id = ? GROUP BY category ORDER BY total DESC',
            (user_id,)
        ).fetchall()
    conn.close()
    return rows


def get_monthly_totals(user_id):
    """Return month-wise income and expense totals for the last 6 months."""
    conn = get_db()
    expense_rows = conn.execute(
        'SELECT strftime("%Y-%m", date) as month, SUM(amount) as total '
        'FROM expenses WHERE user_id = ? '
        'GROUP BY month ORDER BY month DESC LIMIT 6',
        (user_id,)
    ).fetchall()

    income_rows = conn.execute(
        'SELECT strftime("%Y-%m", date) as month, SUM(amount) as total '
        'FROM income WHERE user_id = ? '
        'GROUP BY month ORDER BY month DESC LIMIT 6',
        (user_id,)
    ).fetchall()
    conn.close()
    return expense_rows, income_rows


def get_category_averages(user_id):
    """Return the average monthly spending per category across all months."""
    conn = get_db()
    rows = conn.execute(
        '''
        SELECT category,
               AVG(monthly_total) as avg_amount,
               COUNT(*) as num_months
        FROM (
            SELECT category,
                   strftime("%Y-%m", date) as month,
                   SUM(amount) as monthly_total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category, month
        )
        GROUP BY category
        ORDER BY avg_amount DESC
        ''',
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_category_monthly_spending(user_id, category):
    """Return month-by-month spending for a specific category."""
    conn = get_db()
    rows = conn.execute(
        'SELECT strftime("%Y-%m", date) as month, SUM(amount) as total '
        'FROM expenses WHERE user_id = ? AND category = ? '
        'GROUP BY month ORDER BY month DESC LIMIT 3',
        (user_id, category)
    ).fetchall()
    conn.close()
    return rows


# --- Savings goals helpers -------------------------------------------------

def add_savings_goal(user_id, goal_name, target_amount, deadline):
    conn = get_db()
    conn.execute(
        'INSERT INTO savings_goals (user_id, goal_name, target_amount, deadline) '
        'VALUES (?, ?, ?, ?)',
        (user_id, goal_name, target_amount, deadline)
    )
    conn.commit()
    conn.close()


def get_savings_goals(user_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def update_savings_goal_amount(goal_id, user_id, amount):
    conn = get_db()
    conn.execute(
        'UPDATE savings_goals SET current_amount = current_amount + ? '
        'WHERE id = ? AND user_id = ?',
        (amount, goal_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_savings_goal(goal_id, user_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM savings_goals WHERE id = ? AND user_id = ?',
        (goal_id, user_id)
    )
    conn.commit()
    conn.close()


# --- Delete income helper --------------------------------------------------

def delete_income(income_id, user_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM income WHERE id = ? AND user_id = ?',
        (income_id, user_id)
    )
    conn.commit()
    conn.close()
