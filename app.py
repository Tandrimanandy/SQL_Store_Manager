"""Streamlit frontend.  Run with:  streamlit run app.py"""
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

import db
import queries

st.set_page_config(page_title="SQL Store Manager", page_icon="🛒", layout="wide")
db.ensure_db()
sns.set_theme(style="whitegrid")

PAGES = ["📊 Dashboard", "🗂️ CRUD Manager", "🛍️ Place Order", "🔎 Query Lab", "🧱 Schema & Design"]
page = st.sidebar.radio("Navigate", PAGES)
st.sidebar.divider()
if st.sidebar.button("♻️ Reset database to sample data"):
    db.init_db()
    st.sidebar.success("Database reset.")
    st.rerun()


# ----------------------------------------------------------------- helpers
def lookup(table: str, label: str) -> dict:
    df = db.fetch_all(table)
    return dict(zip(df[db.TABLES[table]["pk"]], df[label]))


def render_field(col: str, spec: dict, key: str, default=None):
    t = spec["type"]
    if t == "text":
        return st.text_input(col, value="" if default is None else str(default), key=key)
    if t == "int":
        return int(st.number_input(col, min_value=0, step=1, value=int(default or 0), key=key))
    if t == "float":
        return float(st.number_input(col, min_value=0.0, step=10.0, value=float(default or 0.0), key=key))
    if t == "date":
        value = pd.to_datetime(default).date() if default else pd.Timestamp.today().date()
        return str(st.date_input(col, value=value, key=key))
    if t == "choice":
        opts = spec["options"]
        idx = opts.index(default) if default in opts else 0
        return st.selectbox(col, opts, index=idx, key=key)
    if t == "fk":
        mapping = lookup(spec["ref"], spec["label"])
        ids = list(mapping)
        idx = ids.index(default) if default in ids else 0
        return st.selectbox(col, ids, index=idx, format_func=lambda i: f"{mapping[i]} (#{i})", key=key)


def run_safely(action, success_msg: str):
    try:
        action()
        st.success(success_msg)
        return True
    except sqlite3.IntegrityError as e:
        st.error(f"Database constraint violated: {e}")
    except ValueError as e:
        st.error(str(e))
    return False


# --------------------------------------------------------------- Dashboard
if page == PAGES[0]:
    st.title("📊 Store Dashboard")
    kpi = db.read_sql(
        """SELECT (SELECT COUNT(*) FROM customers) AS customers,
                  (SELECT COUNT(*) FROM products)  AS products,
                  (SELECT COUNT(*) FROM orders)    AS orders,
                  (SELECT COALESCE(SUM(total),0) FROM v_order_totals
                   WHERE status <> 'Cancelled')    AS revenue"""
    ).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers", int(kpi["customers"]))
    c2.metric("Products", int(kpi["products"]))
    c3.metric("Orders", int(kpi["orders"]))
    c4.metric("Revenue (excl. cancelled)", f"₹{kpi['revenue']:,.0f}")

    left, right = st.columns(2)
    cat = queries.run_query(queries.QUERIES["Subqueries"]["Scalar subquery in SELECT - revenue share by category"][1])
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(data=cat, x="revenue", y="category", ax=ax)
    ax.set_title("Revenue by category")
    left.pyplot(fig)

    monthly = queries.run_query(queries.QUERIES["Aggregates"]["Monthly revenue"][1])
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.lineplot(data=monthly, x="month", y="revenue", marker="o", ax=ax)
    ax.set_title("Monthly revenue")
    ax.tick_params(axis="x", rotation=45)
    right.pyplot(fig)

    left, right = st.columns(2)
    status = db.read_sql("SELECT status, COUNT(*) AS orders FROM orders GROUP BY status")
    fig, ax = plt.subplots(figsize=(6, 3.5))
    sns.barplot(data=status, x="status", y="orders", ax=ax)
    ax.set_title("Orders by status")
    left.pyplot(fig)

    top = queries.run_query(queries.QUERIES["Subqueries"]["Derived table (subquery in FROM) - top 5 customers"][1])
    right.subheader("Top 5 customers")
    right.dataframe(top, use_container_width=True, hide_index=True)

# ------------------------------------------------------------- CRUD Manager
elif page == PAGES[1]:
    st.title("🗂️ CRUD Manager")
    table = st.selectbox("Table", list(db.TABLES))
    cfg = db.TABLES[table]
    pk = cfg["pk"]
    tab_c, tab_r, tab_u, tab_d = st.tabs(["➕ Create", "📖 Read", "✏️ Update", "🗑️ Delete"])

    with tab_c:
        with st.form(f"create_{table}"):
            values = {c: render_field(c, s, f"c_{table}_{c}") for c, s in cfg["columns"].items()}
            if st.form_submit_button("Insert row"):
                run_safely(lambda: db.insert_row(table, values), "Row inserted.")

    with tab_r:
        df = db.fetch_all(table)
        term = st.text_input("Search (any column contains…)", key=f"search_{table}")
        if term:
            mask = df.astype(str).apply(lambda col: col.str.contains(term, case=False)).any(axis=1)
            df = df[mask]
        st.caption(f"{len(df)} row(s)")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_u:
        df = db.fetch_all(table)
        if df.empty:
            st.info("No rows to update.")
        else:
            row_id = st.selectbox(f"Choose {pk}", df[pk].tolist(), key=f"u_pick_{table}")
            row = df[df[pk] == row_id].iloc[0]
            with st.form(f"update_{table}_{row_id}"):
                new = {c: render_field(c, s, f"u_{table}_{row_id}_{c}", row[c]) for c, s in cfg["columns"].items()}
                if st.form_submit_button("Save changes"):
                    run_safely(lambda: db.update_row(table, int(row_id), new), "Row updated.")

    with tab_d:
        df = db.fetch_all(table)
        if df.empty:
            st.info("No rows to delete.")
        else:
            row_id = st.selectbox(f"Choose {pk}", df[pk].tolist(), key=f"d_pick_{table}")
            st.dataframe(df[df[pk] == row_id], hide_index=True, use_container_width=True)
            st.warning("Deleting a parent row can be blocked by foreign keys (RESTRICT) or cascade to children.")
            if st.button("Delete this row", type="primary", key=f"d_btn_{table}"):
                if run_safely(lambda: db.delete_row(table, int(row_id)), "Row deleted."):
                    st.rerun()

# -------------------------------------------------------------- Place Order
elif page == PAGES[2]:
    st.title("🛍️ Place an Order")
    st.caption("Inserts into `orders` + `order_items` and reduces `products.stock` in a single transaction.")
    customers = lookup("customers", "full_name")
    products = db.read_sql("SELECT product_id, name, price, stock FROM products ORDER BY name")

    cust = st.selectbox("Customer", list(customers), format_func=lambda i: customers[i])
    chosen = st.multiselect(
        "Products",
        products["product_id"].tolist(),
        format_func=lambda i: "{} - ₹{:,.0f} ({} in stock)".format(
            *products.loc[products.product_id == i, ["name", "price", "stock"]].iloc[0]
        ),
    )
    items = []
    for pid in chosen:
        name = products.loc[products.product_id == pid, "name"].iloc[0]
        qty = st.number_input(f"Quantity - {name}", min_value=1, value=1, step=1, key=f"qty_{pid}")
        items.append((int(pid), int(qty)))

    if st.button("Place order", type="primary", disabled=not items):
        if run_safely(lambda: db.create_order(int(cust), items), "Order placed!"):
            st.balloons()

    st.subheader("Recent orders")
    st.dataframe(
        db.read_sql(
            """SELECT t.order_id, c.full_name AS customer, t.order_date, t.status, ROUND(t.total, 2) AS total
               FROM v_order_totals t JOIN customers c ON c.customer_id = t.customer_id
               ORDER BY t.order_id DESC LIMIT 10"""
        ),
        use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------- Query Lab
elif page == PAGES[3]:
    st.title("🔎 Query Lab")
    st.caption("Study each query, run it, and tweak it in the Custom SQL tab.")
    tabs = st.tabs(list(queries.QUERIES) + ["✍️ Custom SQL"])
    for tab, (group, items) in zip(tabs, queries.QUERIES.items()):
        with tab:
            title = st.selectbox("Pick a query", list(items), key=f"q_{group}")
            desc, sql = items[title]
            st.info(desc)
            st.code(sql, language="sql")
            st.dataframe(queries.run_query(sql), use_container_width=True, hide_index=True)
    with tabs[-1]:
        st.write("Write your own `SELECT` (runs on a read-only connection, so it can't change data).")
        sql = st.text_area("SQL", "SELECT * FROM products LIMIT 5;", height=160)
        if st.button("Run", type="primary"):
            try:
                result = queries.run_query(sql)
                st.caption(f"{len(result)} row(s)")
                st.dataframe(result, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

# ----------------------------------------------------------- Schema & Design
else:
    st.title("🧱 Schema & Database Design")
    st.graphviz_chart(
        """
        digraph ER {
          rankdir=LR; node [shape=record, fontsize=11];
          categories  [label="{categories|PK category_id\\lname\\l}"];
          products    [label="{products|PK product_id\\lFK category_id\\lname\\lprice\\lstock\\l}"];
          customers   [label="{customers|PK customer_id\\lfull_name\\lemail (unique)\\lcity\\lcreated_at\\l}"];
          orders      [label="{orders|PK order_id\\lFK customer_id\\lorder_date\\lstatus\\l}"];
          order_items [label="{order_items|PK order_item_id\\lFK order_id\\lFK product_id\\lquantity\\lunit_price\\l}"];
          categories -> products    [label="1 : N"];
          customers  -> orders      [label="1 : N"];
          orders     -> order_items [label="1 : N"];
          products   -> order_items [label="1 : N"];
        }
        """
    )
    st.markdown(
        """
**Design decisions**
- **3NF:** every non-key column depends only on its table's key. Category names live once in `categories`, not repeated per product.
- **Many-to-many** between orders and products is resolved with the `order_items` junction table.
- **`unit_price` is copied** into `order_items` so old orders keep their original price when a product's price changes.
- **Order totals are a view** (`v_order_totals`), not a stored column, so they can never go out of sync.
- **Constraints:** `NOT NULL`, `UNIQUE(email)`, `CHECK(price >= 0)`, `CHECK(quantity > 0)`, status `CHECK` list, and foreign keys with `RESTRICT` / `CASCADE`.
- **Indexes** on every foreign key and on `order_date`.
        """
    )
    with db.get_conn() as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for n in names:
            with st.expander(f"Table: {n}"):
                st.dataframe(pd.read_sql_query(f"PRAGMA table_info({n})", conn), hide_index=True, use_container_width=True)
    with st.expander("Full schema.sql"):
        st.code(db.SCHEMA_PATH.read_text(), language="sql")
