from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import logging
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DB_PATH = 'expenses.db'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('expense_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    ('Salary', 'Income'),
    ('Bonus', 'Income'),
    ('Freelance', 'Income'),
    ('Groceries', 'Expense'),
    ('Rent', 'Expense'),
    ('Utilities', 'Expense'),
    ('Transport', 'Expense'),
    ('Entertainment', 'Expense'),
    ('Health', 'Expense'),
    ('Education', 'Expense')
]


def get_db_connection():
    """Get a database connection with proper error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise


def init_db():
    """Initialize database with error handling"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('Income', 'Expense'))
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
                category_id INTEGER,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT NOT NULL UNIQUE,
                limit_amount REAL NOT NULL CHECK(limit_amount > 0)
            )
        ''')

        # Insert default categories
        for name, category_type in DEFAULT_CATEGORIES:
            try:
                c.execute(
                    'INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)',
                    (name, category_type)
                )
            except sqlite3.Error:
                pass

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


def validate_amount(amount):
    """Validate transaction amount"""
    try:
        amount = float(amount)
        if amount <= 0:
            return None, "Amount must be greater than 0"
        if amount > 999999999:
            return None, "Amount too large"
        return amount, None
    except (ValueError, TypeError):
        return None, "Invalid amount format"


def validate_description(description):
    """Validate transaction description"""
    if not description or not isinstance(description, str):
        return None, "Description is required"
    
    description = description.strip()
    if len(description) == 0:
        return None, "Description cannot be empty"
    if len(description) > 255:
        return None, "Description too long (max 255 characters)"
    
    return description, None


def validate_date(date_str, month_key):
    """Validate transaction date"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_key = date_obj.strftime('%Y-%m')
        
        if date_key != month_key:
            return None, f"Date must be in {month_key}"
        
        if date_obj > datetime.now():
            return None, "Date cannot be in the future"
        
        return date_str, None
    except (ValueError, TypeError):
        return None, "Invalid date format"


def handle_db_error(f):
    """Decorator for handling database errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Database error in {f.__name__}: {e}")
            flash("A database error occurred. Please try again.", "danger")
            return redirect(url_for('home'))
    return decorated_function


def get_month_key(month):
    """Parse and validate month format"""
    try:
        return datetime.strptime(month, '%Y-%m').strftime('%Y-%m')
    except (ValueError, TypeError):
        return datetime.now().strftime('%Y-%m')


def fetch_month_options(conn):
    """Get all available months from transactions"""
    try:
        c = conn.cursor()
        c.execute(
            "SELECT DISTINCT substr(date, 1, 7) AS month_year FROM transactions "
            "ORDER BY month_year DESC LIMIT 24"
        )
        rows = c.fetchall()
        months = [row['month_year'] for row in rows]
        
        # Always include current month
        current_month = datetime.now().strftime('%Y-%m')
        if current_month not in months:
            months.insert(0, current_month)
        
        return months[:12] if months else [current_month]
    except sqlite3.Error as e:
        logger.error(f"Error fetching months: {e}")
        return [datetime.now().strftime('%Y-%m')]


def fetch_summary(conn, month_key):
    """Fetch financial summary for a month"""
    try:
        c = conn.cursor()

        c.execute(
            "SELECT IFNULL(SUM(amount), 0) AS income FROM transactions "
            "WHERE type = 'Income' AND substr(date, 1, 7) = ?",
            (month_key,)
        )
        income = c.fetchone()['income']

        c.execute(
            "SELECT IFNULL(SUM(amount), 0) AS expense FROM transactions "
            "WHERE type = 'Expense' AND substr(date, 1, 7) = ?",
            (month_key,)
        )
        expense = c.fetchone()['expense']

        c.execute(
            '''
            SELECT categories.name AS category,
                   categories.type AS type,
                   IFNULL(SUM(transactions.amount), 0) AS total
            FROM categories
            LEFT JOIN transactions ON transactions.category_id = categories.id
                AND substr(transactions.date, 1, 7) = ?
            GROUP BY categories.id
            ORDER BY categories.type DESC, total DESC
            ''',
            (month_key,)
        )
        category_breakdown = [dict(row) for row in c.fetchall() if row['total'] > 0]

        c.execute(
            "SELECT limit_amount FROM budgets WHERE month_year = ?",
            (month_key,)
        )
        budget_row = c.fetchone()
        budget_limit = budget_row['limit_amount'] if budget_row else 0

        net = income - expense
        remaining_budget = max(budget_limit - expense, 0) if budget_limit else 0
        budget_progress = min(int((expense / budget_limit) * 100), 100) if budget_limit else 0

        return {
            'income': round(income, 2),
            'expense': round(expense, 2),
            'net': round(net, 2),
            'budget_limit': round(budget_limit, 2),
            'remaining_budget': round(remaining_budget, 2),
            'budget_progress': budget_progress,
            'category_breakdown': category_breakdown
        }
    except sqlite3.Error as e:
        logger.error(f"Error fetching summary: {e}")
        return {
            'income': 0,
            'expense': 0,
            'net': 0,
            'budget_limit': 0,
            'remaining_budget': 0,
            'budget_progress': 0,
            'category_breakdown': []
        }


def fetch_transactions(conn, month_key):
    """Fetch transactions for a month"""
    try:
        c = conn.cursor()
        c.execute(
            '''
            SELECT transactions.id,
                   transactions.description,
                   transactions.amount,
                   transactions.type,
                   transactions.date,
                   categories.name AS category
            FROM transactions
            LEFT JOIN categories ON categories.id = transactions.category_id
            WHERE substr(transactions.date, 1, 7) = ?
            ORDER BY transactions.date DESC, transactions.created_at DESC
            ''',
            (month_key,)
        )
        return [dict(row) for row in c.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching transactions: {e}")
        return []


@app.route('/', methods=['GET', 'POST'])
@handle_db_error
def home():
    """Main dashboard route"""
    try:
        init_db()

        selected_month = get_month_key(request.args.get('month'))
        conn = get_db_connection()

        if request.method == 'POST':
            form_type = request.form.get('action')

            if form_type == 'transaction':
                # Validate inputs
                description, desc_error = validate_description(request.form.get('description', ''))
                if desc_error:
                    flash(desc_error, 'warning')
                    conn.close()
                    return redirect(url_for('home', month=selected_month))

                amount, amt_error = validate_amount(request.form.get('amount', 0))
                if amt_error:
                    flash(amt_error, 'warning')
                    conn.close()
                    return redirect(url_for('home', month=selected_month))

                transaction_type = request.form.get('transaction_type', 'Expense')
                if transaction_type not in ['Income', 'Expense']:
                    flash('Invalid transaction type', 'warning')
                    conn.close()
                    return redirect(url_for('home', month=selected_month))

                category_id = request.form.get('category_id') or None
                date_str = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
                
                date_val, date_error = validate_date(date_str, selected_month)
                if date_error:
                    flash(date_error, 'warning')
                    conn.close()
                    return redirect(url_for('home', month=selected_month))

                # Insert transaction
                try:
                    c = conn.cursor()
                    c.execute(
                        '''
                        INSERT INTO transactions (description, amount, type, category_id, date)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (description, amount, transaction_type, category_id, date_val)
                    )
                    conn.commit()
                    flash(f'{transaction_type} of Rs. {amount} added successfully', 'success')
                    logger.info(f"Transaction added: {description} - {amount}")
                except sqlite3.Error as e:
                    logger.error(f"Error inserting transaction: {e}")
                    flash('Failed to save transaction. Please try again.', 'danger')

            elif form_type == 'budget':
                try:
                    limit_amount = float(request.form.get('limit_amount', 0))
                    if limit_amount <= 0:
                        flash('Budget limit must be greater than 0', 'warning')
                    elif limit_amount > 999999999:
                        flash('Budget limit too large', 'warning')
                    else:
                        month_year = get_month_key(request.form.get('budget_month'))
                        c = conn.cursor()
                        c.execute(
                            '''
                            INSERT INTO budgets (month_year, limit_amount)
                            VALUES (?, ?)
                            ON CONFLICT(month_year) DO UPDATE SET limit_amount = excluded.limit_amount
                            ''',
                            (month_year, limit_amount)
                        )
                        conn.commit()
                        flash(f'Budget updated to Rs. {limit_amount}', 'success')
                        logger.info(f"Budget set for {month_year}: {limit_amount}")
                except ValueError:
                    flash('Invalid budget amount', 'warning')
                except sqlite3.Error as e:
                    logger.error(f"Error setting budget: {e}")
                    flash('Failed to save budget. Please try again.', 'danger')

            conn.close()
            return redirect(url_for('home', month=selected_month))

        # Fetch data for rendering
        categories = conn.execute("SELECT id, name, type FROM categories ORDER BY type DESC, name").fetchall()
        months = fetch_month_options(conn)
        summary = fetch_summary(conn, selected_month)
        transactions = fetch_transactions(conn, selected_month)
        conn.close()

        return render_template(
            'index.html',
            selected_month=selected_month,
            months=months,
            categories=categories,
            summary=summary,
            transactions=transactions
        )
    except Exception as e:
        logger.error(f"Unexpected error in home route: {e}")
        flash('An unexpected error occurred. Please try again.', 'danger')
        return render_template('error.html', error="An unexpected error occurred"), 500


@app.route('/delete/<int:transaction_id>', methods=['POST'])
@handle_db_error
def delete(transaction_id):
    """Delete a transaction"""
    try:
        if not isinstance(transaction_id, int) or transaction_id <= 0:
            flash('Invalid transaction ID', 'warning')
            return redirect(request.referrer or url_for('home'))

        conn = get_db_connection()
        
        # Check if transaction exists
        c = conn.cursor()
        c.execute('SELECT id FROM transactions WHERE id = ?', (transaction_id,))
        if not c.fetchone():
            flash('Transaction not found', 'warning')
            conn.close()
            return redirect(request.referrer or url_for('home'))

        # Delete transaction
        conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        conn.commit()
        conn.close()
        
        flash('Transaction deleted successfully', 'success')
        logger.info(f"Transaction deleted: ID {transaction_id}")
        return redirect(request.referrer or url_for('home'))
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}")
        flash('Failed to delete transaction. Please try again.', 'danger')
        return redirect(request.referrer or url_for('home'))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return render_template('error.html', error="Server error. Please try again later."), 500


if __name__ == '__main__':
    try:
        init_db()
        logger.info("Starting Expense Tracker application")
        app.run(host='localhost', port=8080, debug=False)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
