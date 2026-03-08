import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Inventory Manager", layout="wide")

conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

# TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS parts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE,
stock INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS bom(
product_id INTEGER,
part_id INTEGER,
qty INTEGER
)
""")

conn.commit()

st.title("Inventory Production Manager")

menu = st.sidebar.radio(
"Menu",
[
"Add Part",
"Add Stock",
"Create Product",
"Run Production",
"Inventory"
]
)

# ---------------------
# ADD PART
# ---------------------

if menu == "Add Part":

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock",min_value=0)

    if st.button("Add"):

        cursor.execute(
        "INSERT OR IGNORE INTO parts(name,stock) VALUES(?,?)",
        (name,stock)
        )

        conn.commit()

        st.success("Part saved")

        st.rerun()

# ---------------------
# ADD STOCK
# ---------------------

if menu == "Add Stock":

    parts = pd.read_sql("SELECT * FROM parts",conn)

    part = st.selectbox("Part",parts["name"])

    qty = st.number_input("Quantity",min_value=1)

    if st.button("Update"):

        part_id = parts.loc[parts["name"]==part,"id"].values[0]

        cursor.execute(
        "UPDATE parts SET stock = stock + ? WHERE id=?",
        (qty,part_id)
        )

        conn.commit()

        st.success("Stock updated")

        st.rerun()

# ---------------------
# CREATE PRODUCT
# ---------------------

if menu == "Create Product":

    product = st.text_input("Product Name")

    parts = pd.read_sql("SELECT * FROM parts",conn)

    part = st.selectbox("Part",parts["name"])

    qty = st.number_input("Quantity Needed",min_value=1)

    if st.button("Save Product"):

        cursor.execute(
        "INSERT OR IGNORE INTO products(name) VALUES(?)",
        (product,)
        )

        conn.commit()

        product_id = pd.read_sql(
        "SELECT id FROM products WHERE name=?",
        conn,
        params=(product,)
        )["id"].values[0]

        part_id = parts.loc[parts["name"]==part,"id"].values[0]

        cursor.execute(
        "INSERT INTO bom(product_id,part_id,qty) VALUES(?,?,?)",
        (product_id,part_id,qty)
        )

        conn.commit()

        st.success("Product part added")

# ---------------------
# RUN PRODUCTION
# ---------------------

if menu == "Run Production":

    products = pd.read_sql("SELECT * FROM products",conn)

    product = st.selectbox("Product",products["name"])

    qty = st.number_input("Quantity Produced",min_value=1)

    if st.button("Run"):

        product_id = products.loc[
        products["name"]==product,"id"
        ].values[0]

        bom = pd.read_sql(
        "SELECT * FROM bom WHERE product_id=?",
        conn,
        params=(product_id,)
        )

        if len(bom)==0:

            st.error("No parts defined for this product")

        else:

            for _,row in bom.iterrows():

                required = row["qty"] * qty

                cursor.execute(
                "UPDATE parts SET stock = stock - ? WHERE id=?",
                (required,row["part_id"])
                )

            conn.commit()

            st.success("Production completed")

            st.rerun()

# ---------------------
# INVENTORY
# ---------------------

if menu == "Inventory":

    parts = pd.read_sql(
    "SELECT name AS Part, stock AS Stock FROM parts",
    conn
    )

    st.dataframe(parts,use_container_width=True)
