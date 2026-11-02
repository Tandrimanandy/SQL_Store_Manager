"""Run with:  python test_backend.py   (or pytest)"""
import sqlite3

import db
import queries


def setup_module(_=None):
    db.init_db()


def test_all_showcase_queries_run():
    for group in queries.QUERIES.values():
        for title, (_, sql) in group.items():
            df = queries.run_query(sql)
            assert df is not None, title


def test_crud_roundtrip():
    new_id = db.insert_row("categories", {"name": "Garden"})
    assert db.update_row("categories", new_id, {"name": "Garden & Outdoor"}) == 1
    names = db.fetch_all("categories")["name"].tolist()
    assert "Garden & Outdoor" in names
    assert db.delete_row("categories", new_id) == 1


def test_constraints():
    try:
        db.insert_row("products", {"name": "Bad", "category_id": 1, "price": -5, "stock": 1})
        assert False, "CHECK should fail"
    except sqlite3.IntegrityError:
        pass
    try:
        db.delete_row("categories", 1)  # has products -> RESTRICT
        assert False, "FK RESTRICT should fail"
    except sqlite3.IntegrityError:
        pass


def test_order_transaction_rollback():
    before = len(db.fetch_all("orders"))
    try:
        db.create_order(1, [(1, 1), (2, 10_000)])  # second item exceeds stock
        assert False
    except ValueError:
        pass
    assert len(db.fetch_all("orders")) == before  # nothing was saved


def test_create_order_reduces_stock():
    stock = db.read_sql("SELECT stock FROM products WHERE product_id=1")["stock"][0]
    db.create_order(1, [(1, 2)])
    assert db.read_sql("SELECT stock FROM products WHERE product_id=1")["stock"][0] == stock - 2


def test_readonly_runner_blocks_writes():
    for bad in ("DELETE FROM customers", "SELECT 1; DROP TABLE customers"):
        try:
            queries.run_query(bad)
            assert False
        except ValueError:
            pass


if __name__ == "__main__":
    setup_module()
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
