# Flask Expense Tracker

A production-ready personal finance management system built with Flask that helps track income, expenses, categories, and budgets with a clean, modern interface.

## Features

- **Add Income/Expense**: Record transactions with descriptions, amounts, categories, and dates
- **Categories**: Pre-configured income and expense categories (Salary, Rent, Groceries, etc.)
- **Monthly Report**: View detailed breakdown by category and transaction history
- **Budget Limit**: Set monthly spending limits and track progress
- **Data Persistence**: SQLite database with proper schema and constraints
- **Error Handling**: Comprehensive validation and error recovery
- **Logging**: All operations logged to `expense_tracker.log` for debugging
- **Responsive Design**: Mobile-friendly UI with intuitive navigation

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. **Clone or download the project**:
```bash
cd "expense tracker"
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or on macOS/Linux:
# source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Running the Application

1. **Start the server**:
```bash
python app.py
```

2. **Open your browser**:
Navigate to `http://localhost:8080/`

3. **Stop the server**:
Press `Ctrl+C` in the terminal

## Usage

### Adding a Transaction
1. Fill in the transaction form with:
   - **Description**: What the transaction is for
   - **Amount**: How much (in your currency)
   - **Type**: Income or Expense
   - **Category**: Optional, categorize your transaction
   - **Date**: When the transaction occurred
2. Click "Save Transaction"

### Setting a Budget
1. In the Budget Limit section, enter the maximum you want to spend for the month
2. Click "Update Budget"
3. The progress bar shows your spending vs. budget

### Viewing Reports
- **Monthly Report** shows:
  - Category breakdown with totals
  - All transactions for the month
  - Income and expense summaries
  - Net savings calculation

### Selecting a Month
Use the month dropdown in the header to view different months' data

### Deleting Transactions
Click the "Delete" button next to any transaction to remove it

## Database Schema

### Categories Table
- `id`: Primary key
- `name`: Category name (unique)
- `type`: 'Income' or 'Expense'

### Transactions Table
- `id`: Primary key
- `description`: Transaction description
- `amount`: Transaction amount (must be > 0)
- `type`: 'Income' or 'Expense'
- `category_id`: Reference to category (optional)
- `date`: Transaction date (YYYY-MM-DD)
- `created_at`: Creation timestamp

### Budgets Table
- `id`: Primary key
- `month_year`: Unique month identifier (YYYY-MM)
- `limit_amount`: Budget limit for the month

## Validation Rules

- **Amount**: Must be positive and less than 999,999,999
- **Description**: Required, max 255 characters
- **Date**: Must be in the selected month, cannot be in the future
- **Budget**: Must be positive

## Logging

All transactions and errors are logged to `expense_tracker.log` for debugging and audit purposes.

## Error Handling

- Input validation on all forms
- Database error recovery with user-friendly messages
- Flash notifications for success/error/warning messages
- Automatic error pages for common HTTP errors
- Comprehensive logging for troubleshooting

## File Structure

```
expense-tracker/
├── app.py                 # Flask application and routes
├── requirements.txt       # Python dependencies
├── expenses.db           # SQLite database (auto-created)
├── expense_tracker.log   # Application logs
├── templates/
│   ├── index.html        # Main dashboard
│   └── error.html        # Error page
└── static/
    └── style.css         # Styling
```

## Security Notes

- In production, change the `SECRET_KEY` environment variable
- Use a production WSGI server (e.g., Gunicorn) instead of Flask's development server
- Add user authentication for multi-user scenarios
- Use HTTPS in production
- Regularly backup the `expenses.db` file

## Troubleshooting

**Port 8080 is already in use?**
- Edit `app.py` and change the port number in `app.run()` call

**Database locked error?**
- Close any other connections to the database
- Delete `expenses.db` to reset (you'll lose data)

**Validation errors on form submission?**
- Check the flash messages for detailed error information
- Ensure amounts are positive numbers
- Ensure dates are in the correct month

## Future Enhancements

- User authentication and multi-user support
- Data export (CSV, PDF)
- Recurring transactions
- Advanced filtering and search
- Chart visualizations
- Mobile app

## License

This project is open source and available under the MIT License.
