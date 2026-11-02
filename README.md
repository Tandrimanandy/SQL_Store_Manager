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
