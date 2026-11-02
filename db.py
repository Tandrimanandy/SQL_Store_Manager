"""Database layer: connection, schema/seed, and CRUD helpers (SQLite)."""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
DB_PATH = BASE / "store.db"
SCHEMA_PATH = BASE / "sql" / "schema.sql"

STATUSES = ["Pending", "Shipped", "Delivered", "Cancelled"]

# Whitelist describing every table the UI may edit. Table/column names are
# never taken from user input directly, which prevents SQL injection via names.
TABLES = {
    "categories": {
        "pk": "category_id",
        "columns": {"name": {"type": "text"}},
    },
    "customers": {
        "pk": "customer_id",
        "columns": {
            "full_name": {"type": "text"},
            "email": {"type": "text"},
            "city": {"type": "text"},
        },
    },
    "products": {
        "pk": "product_id",
        "columns": {
            "name": {"type": "text"},
            "category_id": {"type": "fk", "ref": "categories", "label": "name"},
            "price": {"type": "float"},
            "stock": {"type": "int"},
        },
    },
    "orders": {
        "pk": "order_id",
        "columns": {
            "customer_id": {"type": "fk", "ref": "customers", "label": "full_name"},
            "order_date": {"type": "date"},
            "status": {"type": "choice", "options": STATUSES},
        },
    },
}


# ---------------------------------------------------------------- connection
def get_conn(readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this per connection
    return conn


def init_db(reset: bool = True) -> None:
    """Create the schema (dropping old tables) and load sample data."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        seed(conn)


def ensure_db() -> None:
    if not DB_PATH.exists():
        init_db()


# --------------------------------------------------------------------- seed
def seed(conn: sqlite3.Connection) -> None:
    rng = random.Random(42)

    categories = ["Electronics", "Books", "Home & Kitchen", "Sports", "Clothing", "Toys"]
    conn.executemany("INSERT INTO categories(name) VALUES (?)", [(c,) for c in categories])
    cat_id = {c: i + 1 for i, c in enumerate(categories)}

    customers = [
        ("Aarav Sharma", "aarav@example.com", "Kolkata"),
        ("Priya Das", "priya@example.com", "Kolkata"),
        ("Rohan Gupta", "rohan@example.com", "Delhi"),
        ("Sneha Roy", "sneha@example.com", "Mumbai"),
        ("Vikram Singh", "vikram@example.com", "Delhi"),
        ("Ananya Iyer", "ananya@example.com", "Chennai"),
        ("Karan Mehta", "karan@example.com", "Mumbai"),
        ("Isha Banerjee", "isha@example.com", "Kolkata"),
        ("Arjun Nair", "arjun@example.com", "Bengaluru"),
        ("Meera Joshi", "meera@example.com", "Pune"),
        ("Dev Patel", "dev@example.com", "Ahmedabad"),   # never orders
        ("Riya Sen", "riya@example.com", "Bengaluru"),   # never orders
    ]
    conn.executemany(
        "INSERT INTO customers(full_name,email,city,created_at) VALUES (?,?,?,?)",
        [(n, e, c, str(date(2026, 1, 1) + timedelta(days=rng.randint(0, 60)))) for n, e, c in customers],
    )

    products = [
        ("Wireless Earbuds", "Electronics", 2499), ("Smartphone", "Electronics", 18999),
        ("Bluetooth Speaker", "Electronics", 3299), ("Laptop Stand", "Electronics", 1199),
        ("SQL Made Easy", "Books", 499), ("Python Crash Course", "Books", 899),
        ("Data Science Handbook", "Books", 1299), ("Mixer Grinder", "Home & Kitchen", 3499),
        ("Non-stick Pan", "Home & Kitchen", 1099), ("Water Bottle", "Home & Kitchen", 399),
        ("Yoga Mat", "Sports", 799), ("Cricket Bat", "Sports", 2199),
        ("Running Shoes", "Sports", 3999), ("Cotton T-Shirt", "Clothing", 599),
        ("Denim Jacket", "Clothing", 2799), ("Wool Scarf", "Clothing", 749),
    ]
    conn.executemany(
        "INSERT INTO products(name,category_id,price,stock) VALUES (?,?,?,?)",
        [(n, cat_id[c], p, rng.randint(20, 120)) for n, c, p in products],
    )
    price = {i + 1: p for i, (_, _, p) in enumerate(products)}

    buyers = list(range(1, 11))  # customers 11 and 12 never order
    for _ in range(40):
        order_date = date(2026, 1, 10) + timedelta(days=rng.randint(0, 290))
        status = rng.choices(STATUSES, weights=[2, 3, 8, 1])[0]
        cur = conn.execute(
            "INSERT INTO orders(customer_id,order_date,status) VALUES (?,?,?)",
            (rng.choice(buyers), str(order_date), status),
        )
        for pid in rng.sample(range(1, len(products) + 1), rng.randint(1, 4)):
            conn.execute(
                "INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (?,?,?,?)",
                (cur.lastrowid, pid, rng.randint(1, 3), price[pid]),
            )
    conn.execute(
        "UPDATE products SET stock = MAX(0, stock - (SELECT COALESCE(SUM(quantity),0) "
        "FROM order_items oi WHERE oi.product_id = products.product_id))"
    )


# --------------------------------------------------------------------- CRUD
def _check(table: str, columns=None) -> dict:
    if table not in TABLES:
        raise ValueError(f"Unknown table: {table}")
    cfg = TABLES[table]
    for col in columns or []:
        if col not in cfg["columns"]:
            raise ValueError(f"Unknown column: {col}")
    return cfg


def read_sql(sql: str, params=()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def fetch_all(table: str) -> pd.DataFrame:                       # READ
    _check(table)
    return read_sql(f"SELECT * FROM {table}")


def insert_row(table: str, data: dict) -> int:                   # CREATE
    _check(table, data)
    cols = ", ".join(data)
    marks = ", ".join("?" for _ in data)
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()))
        return cur.lastrowid


def update_row(table: str, pk_value: int, data: dict) -> int:    # UPDATE
    cfg = _check(table, data)
    sets = ", ".join(f"{c} = ?" for c in data)
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE {table} SET {sets} WHERE {cfg['pk']} = ?", (*data.values(), pk_value)
        )
        return cur.rowcount


def delete_row(table: str, pk_value: int) -> int:                # DELETE
    cfg = _check(table)
    with get_conn() as conn:
        cur = conn.execute(f"DELETE FROM {table} WHERE {cfg['pk']} = ?", (pk_value,))
        return cur.rowcount


# ----------------------------------------------------- multi-table transaction
def create_order(customer_id: int, items: list[tuple[int, int]], order_date: str | None = None) -> int:
    """Create an order + its items and reduce stock, all in ONE transaction.

    If anything fails (e.g. not enough stock) everything is rolled back.
    """
    if not items:
        raise ValueError("An order needs at least one item.")
    conn = get_conn()
    try:
        with conn:  # commit on success, rollback on exception
            cur = conn.execute(
                "INSERT INTO orders(customer_id, order_date) VALUES (?, COALESCE(?, date('now')))",
                (customer_id, order_date),
            )
            order_id = cur.lastrowid
            for product_id, qty in items:
                row = conn.execute(
                    "SELECT name, price, stock FROM products WHERE product_id = ?", (product_id,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"Product {product_id} not found.")
                if row["stock"] < qty:
                    raise ValueError(f"Not enough stock for '{row['name']}' (have {row['stock']}).")
                conn.execute(
                    "INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (?,?,?,?)",
                    (order_id, product_id, qty, row["price"]),
                )
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE product_id = ?", (qty, product_id)
                )
        return order_id
    finally:
        conn.close()
