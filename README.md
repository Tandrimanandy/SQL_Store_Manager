# SQL Store Manager

An online store database built to teach core SQL skills: database design, CRUD operations, joins, subqueries and aggregates. The project pairs a normalized SQLite database with a Python data-access layer and an interactive Streamlit web application.

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://www.python.org">
        <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge" alt="Python 3.10 or later">
      </a>
      <br>
      <sub>Core language</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://www.sqlite.org">
        <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge" alt="SQLite">
      </a>
      <br>
      <sub>Relational database engine</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://streamlit.io">
        <img src="https://img.shields.io/badge/Streamlit-Web_App-FF4B4B?style=for-the-badge" alt="Streamlit">
      </a>
      <br>
      <sub>Interactive web interface</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <a href="https://pandas.pydata.org">
        <img src="https://img.shields.io/badge/pandas-Data_Analysis-150458?style=for-the-badge" alt="pandas">
      </a>
      <br>
      <sub>Query results and data handling</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://matplotlib.org">
        <img src="https://img.shields.io/badge/matplotlib-Charts-11557C?style=for-the-badge" alt="matplotlib">
      </a>
      <br>
      <sub>Dashboard charts</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://seaborn.pydata.org">
        <img src="https://img.shields.io/badge/seaborn-Statistical_Plots-4C72B0?style=for-the-badge" alt="seaborn">
      </a>
      <br>
      <sub>Statistical visualization</sub>
    </td>
  </tr>
</table>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Database Design](#database-design)
- [Functions Reference](#functions-reference)
- [Getting Started](#getting-started)
- [Application Pages](#application-pages)
- [SQL Topics Covered](#sql-topics-covered)
- [Testing](#testing)
- [Security Design](#security-design)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Overview

SQL Store Manager models a small online store with categories, customers, products, orders and order items. It is designed as a hands-on learning resource: every SQL technique used in the project is implemented in code, explained in the interface, and verified by automated tests.

The project is organized in three layers. The schema defines the database structure, the data-access layer (`db.py`) handles connections and transactions, and the Streamlit application (`app.py`) presents the data to the user.

---

## Features

- Normalized five-table database in third normal form, with keys, constraints, indexes and a view
- Full CRUD (Create, Read, Update, Delete) management for four tables, with search
- Transactional order placement that reduces stock, or rolls back completely on error
- Dashboard with store KPIs, revenue by category, monthly revenue, order status and top customers
- Query Lab with 16 annotated showcase queries and a read-only custom SQL runner
- Schema and design page with an entity-relationship diagram and table inspection
- Deterministic sample data, so results are reproducible across resets
- Automated backend test suite

---

## Project Structure

```
sql-store-manager/
├── sql/
│   └── schema.sql           Tables, keys, constraints, indexes and the view
├── app.py                   Streamlit web application (five pages)
├── db.py                    Connection, seed data, CRUD helpers, transactional orders
├── queries.py               Showcase queries and the read-only SQL runner
├── test_backend.py          Automated backend tests
├── requirements.txt         Python dependencies
├── store.db                 SQLite database (created and seeded automatically)
└── README.md                Project documentation
```

---

## Database Design

The database contains five tables. Products belong to categories, customers place orders, and orders contain products through the `order_items` junction table.

| Table | Primary Key | Relationship | Key Constraints |
|---|---|---|---|
| `categories` | `category_id` | One category has many products | `name` is unique |
| `customers` | `customer_id` | One customer has many orders | `email` is unique and required |
| `products` | `product_id` | Belongs to one category | `price >= 0`, `stock >= 0` |
| `orders` | `order_id` | Belongs to one customer | `status` in Pending, Shipped, Delivered, Cancelled |
| `order_items` | `order_item_id` | Junction between orders and products | `quantity > 0`, `unit_price >= 0`, one product per order |

Design decisions:

- The unit price is copied into `order_items` at the time of purchase, so historical totals do not change when product prices change.
- Order totals are calculated by the `v_order_totals` view rather than stored, which prevents the totals from falling out of step with line items.
- Foreign keys use `RESTRICT` to block deletion of categories and products still in use, and `CASCADE` so that deleting an order removes its line items.
- Indexes exist on every foreign key and on `order_date`.

---

## Functions Reference

This section explains why the project is structured the way it is, what each module does, and which functions and libraries it uses.

### Why the Project Is Built This Way

- **Separation of concerns.** SQL schema, data access, query logic and the user interface live in separate files. Changing the interface does not require changes to the database code, and the database can be tested without starting the web application.
- **A single data-access layer.** Every write goes through functions in `db.py`. This keeps validation, parameter handling and transactions in one place, so they cannot be bypassed by the interface.
- **Plain SQL for learning.** Queries are written as readable SQL strings rather than generated by an ORM, so the statements shown to the learner are the statements that actually run.
- **Lightweight tooling.** SQLite needs no server, so the project starts with a single command and the database is a single file.

### What Each Module Does

| Module | What It Does | Why It Exists |
|---|---|---|
| `sql/schema.sql` | Drops and recreates all tables, constraints, indexes and the view | Keeps the database structure in plain SQL that can be read and run by hand |
| `db.py` | Opens connections, seeds sample data, performs CRUD and creates orders | Central place for database access and transactions |
| `queries.py` | Stores the 16 showcase queries and runs read-only SQL | Separates teaching queries from the interface and protects the database from writes |
| `app.py` | Builds the five-page Streamlit interface | Presents data, forms and charts without containing SQL logic |
| `test_backend.py` | Runs six automated tests against the backend | Confirms that constraints, transactions and read-only access behave as designed |

### Functions in db.py

| Function | Purpose | Why It Is Used |
|---|---|---|
| `get_conn(readonly=False)` | Opens a SQLite connection, returns rows as `sqlite3.Row`, and enables foreign keys | Every connection needs foreign key enforcement switched on, which SQLite leaves off by default. The read-only option opens the file with `mode=ro`. |
| `init_db(reset=True)` | Runs `schema.sql` and loads the sample data | Creates a clean database on first launch and whenever the reset button is pressed |
| `ensure_db()` | Creates and seeds the database only if `store.db` does not exist | Lets the application start without a separate setup step |
| `seed(conn)` | Inserts categories, customers, products, orders and order items | Produces realistic and reproducible sample data using a fixed random seed of 42 |
| `_check(table, columns=None)` | Validates that a table and its columns appear in the `TABLES` whitelist | Prevents user input from being used as a table or column name, which blocks SQL injection through identifiers |
| `read_sql(sql, params=())` | Runs a SELECT statement and returns a pandas DataFrame | Gives the dashboard and tables a convenient tabular result |
| `fetch_all(table)` | Returns every row of a whitelisted table | Used by the Read tab, the Update and Delete selectors, and the foreign key dropdowns |
| `insert_row(table, data)` | Inserts one row (CREATE) and returns its new id | Implements the Create operation with parameterized values |
| `update_row(table, pk_value, data)` | Updates the given columns of one row (UPDATE) and returns the number of rows changed | Implements the Update operation |
| `delete_row(table, pk_value)` | Deletes one row (DELETE) and returns the number of rows removed | Implements the Delete operation, where foreign key rules decide whether it is allowed |
| `create_order(customer_id, items, order_date=None)` | Inserts an order and its items, reduces stock, and commits all changes together, or rolls back on error | Keeps an order consistent: either every part is saved or none is |

### Functions in queries.py

| Name | Purpose | Why It Is Used |
|---|---|---|
| `QUERIES` | A dictionary of 16 showcase queries grouped into Joins, Subqueries and Aggregates. Each entry holds a description and the SQL text. | Drives the Query Lab page and the Dashboard charts from one source |
| `run_query(sql)` | Validates a SELECT or WITH statement, rejects multiple statements, and runs it on a read-only connection | Lets learners run SQL safely, with no possibility of changing the data |

### Functions in app.py

| Function | Purpose | Why It Is Used |
|---|---|---|
| `lookup(table, label)` | Builds a dictionary from a table's primary key to a display label | Fills the foreign key dropdowns with readable names, such as a category name, instead of raw ids |
| `render_field(col, spec, key, default=None)` | Draws the right input widget for a column based on its type: text, integer, decimal, date, choice or foreign key | Lets one generic form work for all four tables, driven by the `TABLES` definition |
| `run_safely(action, success_msg)` | Runs a database action, shows a success message, and shows a readable error for constraint or validation failures | Turns database errors into clear messages instead of crashing the page |

The Streamlit functions used in `app.py` include `st.set_page_config`, `st.sidebar.radio`, `st.columns`, `st.metric`, `st.tabs`, `st.form`, `st.dataframe`, `st.pyplot`, `st.graphviz_chart` and `st.rerun`.

### Tests in test_backend.py

| Function | Purpose |
|---|---|
| `setup_module(_=None)` | Resets the database before the tests run |
| `test_all_showcase_queries_run()` | Runs every showcase query to confirm it executes |
| `test_crud_roundtrip()` | Checks insert, update and delete on the categories table |
| `test_constraints()` | Checks that a CHECK violation and a RESTRICT foreign key violation are rejected |
| `test_order_transaction_rollback()` | Checks that a failed order leaves no partial data |
| `test_create_order_reduces_stock()` | Checks that a valid order reduces product stock by the quantity sold |
| `test_readonly_runner_blocks_writes()` | Checks that the query runner refuses DELETE and multi-statement SQL |

### Libraries Used

| Library | Role in the Project |
|---|---|
| `sqlite3` (standard library) | Connects to the SQLite database and executes SQL |
| `pandas` | Converts query results into DataFrames for display and charts |
| `streamlit` | Builds the web interface |
| `matplotlib` and `seaborn` | Draw the dashboard charts |
| `pathlib`, `random`, `datetime` (standard library) | Locate files, generate reproducible sample data, and create dates |

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip

### Installation

1. Clone the repository and move into the project folder.

   ```bash
   git clone <repository-url>
   cd sql-store-manager
   ```

2. Install the dependencies.

   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Start the Streamlit server from the project folder:

```bash
streamlit run app.py
```

The application opens in the browser at `http://localhost:8501`. If `store.db` does not exist, it is created and filled with sample data on first launch. The sidebar button **Reset database to sample data** restores the original state at any time.

### Running the Tests

```bash
python test_backend.py
```

The tests can also be run with pytest.

---

## Application Pages

| Page | Description |
|---|---|
| Dashboard | Store KPIs, revenue by category, monthly revenue, orders by status and the top five customers |
| CRUD Manager | Create, read (with search), update and delete rows in categories, customers, products and orders |
| Place an Order | Select a customer and products; the order, its items and the stock reduction are saved in one transaction |
| Query Lab | Browse each showcase query with its explanation, SQL and live results, or write a custom read-only SELECT |
| Schema & Design | Entity-relationship diagram, design decisions, table inspection and the full schema file |

---

## SQL Topics Covered

| Topic | Where It Appears | Examples |
|---|---|---|
| Database design | `sql/schema.sql`, Schema & Design page | 3NF tables, junction table, view, indexes, constraints |
| CRUD | CRUD Manager, Place an Order | Insert, select, update and delete on four tables |
| Joins | Query Lab | INNER, LEFT, five-table and self joins |
| Subqueries | Query Lab | Scalar, IN, NOT IN, EXISTS, correlated, derived table, SELECT subquery |
| Aggregates | Query Lab, Dashboard | GROUP BY, HAVING, RANK window function, view query |
| Transactions | Place an Order | Commit on success, full rollback on error |

The 16 showcase queries are grouped as follows: 5 joins, 7 subqueries and 4 aggregate queries.

---

## Testing

The backend is covered by six automated tests in `test_backend.py`:

| Test | Verifies |
|---|---|
| `test_all_showcase_queries_run` | All showcase queries execute without error |
| `test_crud_roundtrip` | A category can be inserted, updated and deleted |
| `test_constraints` | A negative price is rejected, and a category with products cannot be deleted |
| `test_order_transaction_rollback` | An order with an item that exceeds stock is rolled back in full |
| `test_create_order_reduces_stock` | Placing an order reduces stock by the quantity sold |
| `test_readonly_runner_blocks_writes` | DELETE and multi-statement SQL are refused by the query runner |

Note that the test suite resets `store.db` before it runs. Run the tests on a copy of the project if you need to keep the current sample data.

---

## Security Design

- Table and column names are checked against a whitelist (`TABLES` in `db.py`) before they are used in SQL, so user input never controls identifiers.
- All values are passed as parameters, which protects against SQL injection.
- The Query Lab opens the database in read-only mode and accepts only a single SELECT or WITH statement.
- Foreign key enforcement is switched on for every connection, because SQLite does not enforce foreign keys by default.

---

## Known Limitations

- Changing an order's status to Cancelled excludes it from reports but does not return its stock to the products table. Deleting an order also does not restore stock.
- Prices and amounts use the REAL type. Integer storage in paise would avoid rounding errors in money calculations.
- The dashboard Orders card counts all orders, including cancelled ones, while the revenue card excludes them.
- The test suite writes to the same `store.db` file used by the application.
- `requirements.txt` does not pin package versions.
- The `reset` parameter of `init_db` is accepted but not used.

---

## Roadmap

- Restore stock when an order is cancelled, with a test to confirm it
- Store monetary values as integers in paise
- Use a separate database file for the test suite
- Add a suppliers table linked to products
- Add a reviews table linked to products and customers
- Add CSV export buttons to the Query Lab and CRUD pages

---

## Author

**Tandrima Nandy**, Batch 3
