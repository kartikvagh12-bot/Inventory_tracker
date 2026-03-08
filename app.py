import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Production & Inventory Manager", layout="wide")

conn = sqlite3.connect("inventory.db", check_same_thread=False)
c = conn.cursor()

# TABLES
c.execute("""
CREATE TABLE IF NOT EXISTS parts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE,
stock INTEGER,
alert INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS bom(
product_id INTEGER,
part_id INTEGER,
quantity INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS production_history(
product_name TEXT,
quantity INTEGER,
date TEXT
)
""")

conn.commit()

st.title("Production & Inventory Manager")

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

# ---------------------
# ADD PARTS
# ---------------------

if menu == "Add Parts":

    st.header("Add New Part")

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock", min_value=0)
    alert = st.number_input("Low Stock Alert Level", min_value=0)

    if st.button("Add Part"):

        try:

            c.execute(
            "INSERT INTO parts(name,stock,alert) VALUES(?,?,?)",
            (name,stock,alert)
            )

            conn.commit()

            st.success("Part added")

            st.rerun()

        except:

            st.error("Part already exists")

    st.subheader("Current Parts")

    parts = pd.read_sql("SELECT name,stock,alert FROM parts", conn)

    st.dataframe(parts,use_container_width=True)


# ---------------------
# ADD STOCK
# ---------------------

if menu == "Add Stock":

    st.header("Add Inventory Stock")

    parts = pd.read_sql("SELECT * FROM parts", conn)

    if len(parts) == 0:

        st.warning("Add parts first")

    else:

        part_name = st.selectbox("Select Part", parts["name"])

        qty = st.number_input("Quantity to Add", min_value=1)

        if st.button("Update Stock"):

            part_id = parts[parts["name"] == part_name]["id"].values[0]

            c.execute(
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

    st.header("Create Product")

    product_name = st.text_input("Product Name")

    parts = pd.read_sql("SELECT * FROM parts", conn)

    if "bom_parts" not in st.session_state:
        st.session_state.bom_parts = []

    col1,col2 = st.columns(2)

    with col1:
        selected_part = st.selectbox("Select Part", parts["name"])

    with col2:
        quantity = st.number_input("Quantity Needed", min_value=1)

    if st.button("Add Part to Product"):

        part_id = parts[parts["name"] == selected_part]["id"].values[0]

        st.session_state.bom_parts.append({
        "Part":selected_part,
        "PartID":part_id,
        "Qty":quantity
        })

    st.subheader("Parts in Product")

    if st.session_state.bom_parts:
        st.table(st.session_state.bom_parts)

    if st.button("Save Product"):

        if product_name == "":
            st.error("Enter product name")

        else:

            try:

                c.execute(
                "INSERT INTO products(name) VALUES(?)",
                (product_name,)
                )

                conn.commit()

                product_id = c.lastrowid

                for item in st.session_state.bom_parts:

                    c.execute(
                    "INSERT INTO bom(product_id,part_id,quantity) VALUES(?,?,?)",
                    (product_id,item["PartID"],item["Qty"])
                    )

                conn.commit()

                st.session_state.bom_parts=[]

                st.success("Product created")

                st.rerun()

            except:

                st.error("Product already exists")


# ---------------------
# RECORD PRODUCTION
# ---------------------

if menu == "Record Production":

    st.header("Production Entry")

    products = pd.read_sql("SELECT * FROM products", conn)

    if len(products) == 0:

        st.warning("Create product first")

    else:

        product_name = st.selectbox("Select Product", products["name"])

        qty = st.number_input("Quantity Produced", min_value=1)

        if st.button("Run Production"):

            product_id = products[products["name"] == product_name]["id"].values[0]

            bom = pd.read_sql(
            f"SELECT * FROM bom WHERE product_id={product_id}",
            conn
            )

            for _,row in bom.iterrows():

                part_id = row["part_id"]

                required = row["quantity"] * qty

                current_stock = pd.read_sql(
                f"SELECT stock FROM parts WHERE id={part_id}",
                conn
                )["stock"].values[0]

                if current_stock < required:

                    st.error("Not enough stock to run production")

                    st.stop()

                c.execute(
                "UPDATE parts SET stock = stock - ? WHERE id=?",
                (required,part_id)
                )

            conn.commit()

            c.execute(
            "INSERT INTO production_history VALUES(?,?,?)",
            (product_name,qty,datetime.now().strftime("%Y-%m-%d %H:%M"))
            )

            conn.commit()

            st.success("Production completed and inventory updated")

            st.rerun()


# ---------------------
# INVENTORY DASHBOARD
# ---------------------

if menu == "Inventory Dashboard":

    st.header("Inventory Overview")

    parts = pd.read_sql(
    "SELECT name AS Part, stock AS Stock, alert AS Alert_Level FROM parts",
    conn
    )

    st.dataframe(parts,use_container_width=True)

    st.subheader("Low Stock Alerts")

    low = parts[parts["Stock"] <= parts["Alert_Level"]]

    if len(low)==0:

        st.success("All stock levels healthy")

    else:

        for _,row in low.iterrows():

            st.error(f"{row['Part']} LOW STOCK: {row['Stock']} remaining")


# ---------------------
# PRODUCTION HISTORY
# ---------------------

if menu == "Production History":

    st.header("Production History")

    history = pd.read_sql("SELECT * FROM production_history",conn)

    if len(history)==0:

        st.info("No production records yet")

    else:

        st.dataframe(history,use_container_width=True)
