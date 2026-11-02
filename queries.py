"""Showcase queries: JOINs, subqueries and aggregates, plus a safe SELECT runner."""
import re

import pandas as pd

from db import get_conn

REVENUE = "oi.quantity * oi.unit_price"

QUERIES = {
    # ------------------------------------------------------------- JOINS
    "Joins": {
        "INNER JOIN - products with their category": (
            "Returns only rows that have a match in BOTH tables.",
            """SELECT p.product_id, p.name AS product, c.name AS category, p.price, p.stock
FROM products p
INNER JOIN categories c ON c.category_id = p.category_id
ORDER BY c.name, p.name;""",
        ),
        "LEFT JOIN - categories with product counts (keeps empty ones)": (
            "LEFT JOIN keeps every category, even those with no products (count = 0).",
            """SELECT c.name AS category, COUNT(p.product_id) AS products
FROM categories c
LEFT JOIN products p ON p.category_id = c.category_id
GROUP BY c.category_id
ORDER BY products DESC;""",
        ),
        "LEFT JOIN - customer spend (includes customers with no orders)": (
            "Chained LEFT JOINs; COALESCE turns NULL sums into 0. The status filter is in the ON clause so customers are not dropped.",
            """SELECT c.full_name, c.city,
       COUNT(DISTINCT o.order_id) AS orders,
       COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
FROM customers c
LEFT JOIN orders o       ON o.customer_id = c.customer_id AND o.status <> 'Cancelled'
LEFT JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY c.customer_id
ORDER BY total_spent DESC;""",
        ),
        "5-table JOIN - full order details": (
            "Walks the whole schema: orders -> customers, order_items -> products -> categories.",
            """SELECT o.order_id, o.order_date, c.full_name AS customer,
       p.name AS product, cat.name AS category,
       oi.quantity, oi.unit_price, oi.quantity * oi.unit_price AS line_total
FROM orders o
JOIN customers c    ON c.customer_id  = o.customer_id
JOIN order_items oi ON oi.order_id    = o.order_id
JOIN products p     ON p.product_id   = oi.product_id
JOIN categories cat ON cat.category_id = p.category_id
ORDER BY o.order_date DESC, o.order_id
LIMIT 50;""",
        ),
        "SELF JOIN - customer pairs from the same city": (
            "A table joined to itself. `a.customer_id < b.customer_id` avoids duplicates and self-pairs.",
            """SELECT a.city, a.full_name AS customer_a, b.full_name AS customer_b
FROM customers a
JOIN customers b ON a.city = b.city AND a.customer_id < b.customer_id
ORDER BY a.city;""",
        ),
    },
    # -------------------------------------------------------- SUBQUERIES
    "Subqueries": {
        "Scalar subquery - products priced above average": (
            "The inner query returns ONE value that the outer WHERE compares against.",
            """SELECT name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products)
ORDER BY price DESC;""",
        ),
        "IN subquery - customers who bought Electronics": (
            "The inner query returns a list of customer ids.",
            """SELECT full_name, city
FROM customers
WHERE customer_id IN (
    SELECT o.customer_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p     ON p.product_id = oi.product_id
    JOIN categories c   ON c.category_id = p.category_id
    WHERE c.name = 'Electronics'
)
ORDER BY full_name;""",
        ),
        "NOT EXISTS - customers who never ordered": (
            "EXISTS / NOT EXISTS only checks whether the inner query returns any row.",
            """SELECT c.customer_id, c.full_name, c.email
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
);""",
        ),
        "NOT IN - products never ordered": (
            "Anti-join using NOT IN. (Make sure the subquery column has no NULLs.)",
            """SELECT product_id, name, price
FROM products
WHERE product_id NOT IN (SELECT DISTINCT product_id FROM order_items);""",
        ),
        "Correlated subquery - priced above own category average": (
            "The inner query references the outer row (p.category_id), so it re-runs per product.",
            """SELECT p.name, p.price,
       (SELECT ROUND(AVG(p2.price), 2)
        FROM products p2
        WHERE p2.category_id = p.category_id) AS category_avg
FROM products p
WHERE p.price > (SELECT AVG(p2.price)
                 FROM products p2
                 WHERE p2.category_id = p.category_id)
ORDER BY p.price DESC;""",
        ),
        "Derived table (subquery in FROM) - top 5 customers": (
            "The subquery builds a temporary table `t` that is then joined.",
            f"""SELECT c.full_name, t.orders, ROUND(t.total_spent, 2) AS total_spent
FROM customers c
JOIN (
    SELECT o.customer_id,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM({REVENUE}) AS total_spent
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status <> 'Cancelled'
    GROUP BY o.customer_id
) t ON t.customer_id = c.customer_id
ORDER BY t.total_spent DESC
LIMIT 5;""",
        ),
        "Scalar subquery in SELECT - revenue share by category": (
            "A subquery in the SELECT list supplies the grand total used for the percentage.",
            f"""SELECT cat.name AS category,
       ROUND(SUM({REVENUE}), 2) AS revenue,
       ROUND(100.0 * SUM({REVENUE}) /
             (SELECT SUM({REVENUE})
              FROM order_items oi
              JOIN orders o ON o.order_id = oi.order_id
              WHERE o.status <> 'Cancelled'), 1) AS pct_of_total
FROM order_items oi
JOIN orders o       ON o.order_id = oi.order_id
JOIN products p     ON p.product_id = oi.product_id
JOIN categories cat ON cat.category_id = p.category_id
WHERE o.status <> 'Cancelled'
GROUP BY cat.category_id
ORDER BY revenue DESC;""",
        ),
    },
    # -------------------------------------------------------- AGGREGATES
    "Aggregates": {
        "GROUP BY + HAVING - cities with 2+ customers": (
            "HAVING filters groups after aggregation (WHERE filters rows before).",
            """SELECT city, COUNT(*) AS customers
FROM customers
GROUP BY city
HAVING COUNT(*) >= 2
ORDER BY customers DESC;""",
        ),
        "Monthly revenue": (
            "strftime groups ISO dates by month.",
            f"""SELECT strftime('%Y-%m', o.order_date) AS month,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM({REVENUE}), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status <> 'Cancelled'
GROUP BY month
ORDER BY month;""",
        ),
        "Window function - best seller per category (RANK)": (
            "RANK() OVER (PARTITION BY ...) ranks rows inside each category.",
            f"""SELECT category, product, units_sold, revenue
FROM (
    SELECT cat.name AS category, p.name AS product,
           SUM(oi.quantity) AS units_sold,
           ROUND(SUM({REVENUE}), 2) AS revenue,
           RANK() OVER (PARTITION BY cat.category_id
                        ORDER BY SUM({REVENUE}) DESC) AS rnk
    FROM order_items oi
    JOIN orders o       ON o.order_id = oi.order_id
    JOIN products p     ON p.product_id = oi.product_id
    JOIN categories cat ON cat.category_id = p.category_id
    WHERE o.status <> 'Cancelled'
    GROUP BY p.product_id
)
WHERE rnk = 1
ORDER BY revenue DESC;""",
        ),
        "VIEW - order totals (v_order_totals)": (
            "Queries a stored view that wraps a JOIN + GROUP BY.",
            """SELECT * FROM v_order_totals ORDER BY total DESC LIMIT 15;""",
        ),
    },
}


def run_query(sql: str) -> pd.DataFrame:
    """Run SQL on a READ-ONLY connection, so nothing can modify the database."""
    sql = sql.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT / WITH queries are allowed here.")
    if ";" in sql:
        raise ValueError("Please run one statement at a time.")
    conn = get_conn(readonly=True)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()
