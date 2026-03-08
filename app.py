import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Inventory Production Manager", layout="wide")

# DATABASE CONNECTION
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

if st.sidebar.button("Reset Database"):
    cursor.execute("DROP TABLE IF EXISTS parts")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS bom")
    cursor.execute("DROP TABLE IF EXISTS production_history")
    conn.commit()
    st.success("Database reset. Refresh the page.")

# CREATE TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS parts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE,
stock INTEGER,
alert INTEGER
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS production_history(
product TEXT,
qty INTEGER,
time TEXT
)
""")

conn.commit()

st.title("🏭 Production & Inventory Manager")

menu = st.sidebar.radio(
"Navigation",
[
"Add Parts",
"Add Stock",
"Create Product",
"Record Production",
"Inventory Dashboard",
"Production History"
]
)

# -----------------------
# ADD PARTS
# -----------------------

if menu == "Add Parts":

    st.header("Add New Part")

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock", min_value=0)
    alert = st.number_input("Low Stock Alert", min_value=0)

    if st.button("Add Part"):

        if name == "":
            st.error("Enter part name")

        else:

            try:
                cursor.execute(
                    "INSERT INTO parts(name,stock,alert) VALUES(?,?,?)",
                    (name,stock,alert)
                )
                conn.commit()

                st.success("Part added")

            except:
                st.error("Part already exists")

    parts = pd.read_sql("SELECT name,stock,alert FROM parts", conn)
    st.dataframe(parts,use_container_width=True)

# -----------------------
# ADD STOCK
# -----------------------

if menu == "Add Stock":

    st.header("Add Stock")

    parts = pd.read_sql("SELECT * FROM parts", conn)

    if len(parts) == 0:
        st.warning("Add parts first")

    else:

        part = st.selectbox("Select Part", parts["name"])
        qty = st.number_input("Quantity to Add", min_value=1)

        if st.button("Add Stock"):

            part_id = parts.loc[parts["name"] == part,"id"].values[0]

            cursor.execute(
                "UPDATE parts SET stock = stock + ? WHERE id=?",
                (qty,part_id)
            )

            conn.commit()

            st.success("Stock updated")

    updated = pd.read_sql("SELECT name,stock FROM parts", conn)
    st.dataframe(updated,use_container_width=True)

# -----------------------
# CREATE PRODUCT
# -----------------------

if menu == "Create Product":

    st.header("Create Product")

    product_name = st.text_input("Product Name")

    parts = pd.read_sql("SELECT * FROM parts", conn)

    if "product_parts" not in st.session_state:
        st.session_state.product_parts = []

    col1, col2 = st.columns(2)

    with col1:
        part = st.selectbox("Select Part", parts["name"])

    with col2:
        qty = st.number_input("Quantity Required", min_value=1)

    if st.button("Add Part"):

        part_id = parts.loc[parts["name"] == part, "id"].values[0]

        st.session_state.product_parts.append(
            {"part": part, "part_id": part_id, "qty": qty}
        )

    st.subheader("Parts In Product")

    for i, item in enumerate(st.session_state.product_parts):

        col1, col2, col3 = st.columns([3,1,1])

        col1.write(item["part"])
        col2.write(item["qty"])

        if col3.button("Remove", key=i):
            st.session_state.product_parts.pop(i)
            st.rerun()

    if st.button("Save Product"):

        if product_name == "":
            st.error("Enter product name")

        elif len(st.session_state.product_parts) == 0:
            st.error("Add at least one part")

        else:

            cursor.execute(
                "SELECT * FROM products WHERE name=?",
                (product_name,)
            )

            existing = cursor.fetchone()

            if existing:
                st.error("Product already exists")

            else:

                cursor.execute(
                    "INSERT INTO products(name) VALUES(?)",
                    (product_name,)
                )

                conn.commit()

                product_id = cursor.lastrowid

                for item in st.session_state.product_parts:

                    cursor.execute(
                        "INSERT INTO bom(product_id,part_id,qty) VALUES(?,?,?)",
                        (product_id, item["part_id"], item["qty"])
                    )

                conn.commit()

                st.session_state.product_parts = []

                st.success("Product saved")

# -----------------------
# RECORD PRODUCTION
# -----------------------

if menu == "Record Production":

    st.header("Record Production")

    products = pd.read_sql("SELECT * FROM products", conn)

    if len(products) == 0:

        st.warning("Create product first")

    else:

        product = st.selectbox("Product", products["name"])
        qty = st.number_input("Quantity Produced", min_value=1)

        if st.button("Run Production"):

            product_id = products.loc[
                products["name"] == product, "id"
            ].values[0]

            bom = pd.read_sql(
                "SELECT part_id, qty FROM bom WHERE product_id=?",
                conn,
                params=(product_id,)
            )

            if len(bom) == 0:
                st.error("No parts defined for this product")
                st.stop()

            for _, row in bom.iterrows():

                required = int(row["qty"]) * qty

                stock = pd.read_sql(
                    "SELECT stock FROM parts WHERE id=?",
                    conn,
                    params=(row["part_id"],)
                )["stock"].values[0]

                if stock < required:

                    st.error("Not enough inventory to run production")
                    st.stop()

            for _, row in bom.iterrows():

                required = int(row["qty"]) * qty

                cursor.execute(
                    "UPDATE parts SET stock = stock - ? WHERE id=?",
                    (required, row["part_id"])
                )

            conn.commit()

            cursor.execute(
                "INSERT INTO production_history VALUES(?,?,?)",
                (product, qty, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )

            conn.commit()

            st.success("Production completed")

# -----------------------
# INVENTORY
# -----------------------

if menu == "Inventory Dashboard":

    st.header("Inventory")

    parts = pd.read_sql(
        "SELECT name AS Part, stock AS Stock, alert AS Alert_Level FROM parts",
        conn
    )

    st.dataframe(parts,use_container_width=True)

    st.subheader("Low Stock")

    low = parts[parts["Stock"] <= parts["Alert_Level"]]

    if len(low) == 0:
        st.success("All inventory levels OK")

    else:
        for _,row in low.iterrows():
            st.error(f"{row['Part']} LOW STOCK ({row['Stock']})")

# -----------------------
# PRODUCTION HISTORY
# -----------------------

if menu == "Production History":

    st.header("Production History")

    history = pd.read_sql("SELECT * FROM production_history", conn)

    if len(history) == 0:
        st.info("No production records yet")

    else:
        st.dataframe(history,use_container_width=True)
