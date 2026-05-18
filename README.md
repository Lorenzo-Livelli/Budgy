# Budgy

Budgy is a personal budgeting application built with **Streamlit**.
It provides a clean and interactive dashboard for managing transactions, tracking balances, and visualizing spending habits.

---

## Index

* [Features](#features)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Installation](#installation)
* [Configuration](#configuration)
* [Running the Application](#running-the-application)
* [Database Schema](#database-schema)
* [Usage](#usage)
* [License](#license)
* [Author](#author)

---

## Features

* Add income and expense transactions
* Interact easily with the transaction history directly from the sidebar:
   * Add transactions
   * Remove transactions
   * Order the transaction list
* Automatic classification of transactions as **Income** or **Expense**
* Interactive transaction table
* Sort transactions by:
  * Date
  * Amount
* Filter transactions to exclude incomes
* Cumulative balance tracking
* Interactive charts for balance history
* Expense breakdown by category
* Persistent data storage using SQLite
* Color-coded categories for improved readability

---

## Tech Stack

| Technology | Purpose                    |
| ---------- | -------------------------- |
| Python     | Core programming language  |
| Streamlit  | Web application framework  |
| SQLite     | Local database             |
| SQLAlchemy | Database interaction       |
| Pandas     | Data manipulation          |
| Plotly     | Interactive visualizations |

---

## Project Structure

```bash
.
├── main.py
├── init_db.py
├── utils.py
├── transactions.db
├── .streamlit/
│   └── secrets.toml
├── .gitignore
└── README.md
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/budgy.git
cd budgy
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS/Linux

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install streamlit pandas plotly sqlalchemy
```

---

## Configuration

Create the following file:

```bash
.streamlit/secrets.toml
```

Add the database connection configuration:

```toml
[connections.transactions_db]
url = "sqlite:///transactions.db"
```

---

## Running the Application

Launch the Streamlit app with:

```bash
streamlit run app.py
```

---

## Database

The application stores transactions in an SQLite database using the following schema:

```sql
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    Type TEXT NOT NULL,
    date DATE NOT NULL,
    ex_in TEXT NOT NULL,
    description TEXT
);
```
It's possible to generate the database in the main folder by running the init_db.py script

---

## Usage

### Adding Transactions

Use the sidebar form to:

* Enter an amount
* Select a transaction category
* Choose a date
* Add an optional description

Positive amounts are treated as income, while negative amounts are treated as expenses.

### Viewing Analytics

Budgy provides:

* A searchable and sortable transaction table
* A cumulative balance chart over time
* Expense distribution by category

### Removing Transactions

Transactions can be removed directly from the sidebar.

---

## License

This project is licensed under the MIT License.

---

## Author

Created by Lorenzo Livelli
