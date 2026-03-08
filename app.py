import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Inventory Production Manager", layout="wide")

# DATABASE
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

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
id INTEGER PRIMARY KEY AUTOINCREMENT,
product_id INTEGER,
part_id INTEGER,
qty INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS production(
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
"Inventory Dashboard"
]
)

# -------------------------
# ADD PARTS
# -------------------------

if menu == "Add Parts":

    st.header("Add Part")

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

    parts = pd.read_sql("SELECT name,stock,alert FROM parts",conn)
    st.dataframe(parts,use_container_width=True)


# -------------------------
# ADD STOCK
# -------------------------

if menu == "Add Stock":

    st.header("Add Stock")

    parts = pd.read_sql("SELECT * FROM parts",conn)

    if len(parts) == 0:
        st.warning("Add parts first")

    else:

        part = st.selectbox("Part",parts["name"])
        qty = st.number_input("Quantity",min_value=1)

        if st.button("Update Stock"):

            part_id = parts.loc[parts["name"]==part,"id"].values[0]

            cursor.execute(
                "UPDATE parts SET stock = stock + ? WHERE id=?",
                (qty,part_id)
            )

            conn.commit()

            st.success("Stock updated")

    updated = pd.read_sql("SELECT name,stock FROM parts",conn)
    st.dataframe(updated,use_container_width=True)


# -------------------------
# CREATE PRODUCT
# -------------------------

if menu == "Create Product":

    st.header("Create Product")

    product_name = st.text_input("Product Name")

    parts = pd.read_sql("SELECT * FROM parts",conn)

    if "product_parts" not in st.session_state:
        st.session_state.product_parts = []

    part = st.selectbox("Part",parts["name"])
    qty = st.number_input("Quantity Needed",min_value=1)

    if st.button("Add Part"):

        part_id = parts.loc[parts["name"]==part,"id"].values[0]

        st.session_state.product_parts.append({
            "name":part,
            "id":part_id,
            "qty":qty
        })

    st.subheader("Parts in Product")

    for i,p in enumerate(st.session_state.product_parts):

        col1,col2,col3 = st.columns([4,2,1])

        col1.write(p["name"])
        col2.write(p["qty"])

        if col3.button("Remove",key=i):
            st.session_state.product_parts.pop(i)
            st.rerun()

    if st.button("Save Product"):

        if product_name == "":
            st.error("Enter product name")

        elif len(st.session_state.product_parts)==0:
            st.error("Add parts first")

        else:

            cursor.execute(
                "SELECT * FROM products WHERE name=?",
                (product_name,)
            )

            if cursor.fetchone():
                st.error("Product already exists")

            else:

                cursor.execute(
                    "INSERT INTO products(name) VALUES(?)",
                    (product_name,)
                )

                conn.commit()

                product_id = cursor.lastrowid

                for p in st.session_state.product_parts:

                    cursor.execute(
                        "INSERT INTO bom(product_id,part_id,qty) VALUES(?,?,?)",
                        (product_id,p["id"],p["qty"])
                    )

                conn.commit()

                st.session_state.product_parts=[]

                st.success("Product saved")


# -------------------------
# RECORD PRODUCTION
# -------------------------

if menu == "Record Production":

    st.header("Record Production")

    products = pd.read_sql("SELECT * FROM products",conn)

    if len(products)==0:

        st.warning("Create product first")

    else:

        product = st.selectbox("Product",products["name"])
        qty = st.number_input("Quantity Produced",min_value=1)

        if st.button("Run Production"):

            product_id = products.loc[
                products["name"]==product,"id"
            ].values[0]

            bom = pd.read_sql(
                "SELECT * FROM bom WHERE product_id=?",
                conn,
                params=(product_id,)
            )

            if len(bom)==0:
                st.error("No parts defined")
                st.stop()

            for _,row in bom.iterrows():

                required = row["qty"] * qty

                stock = pd.read_sql(
                    "SELECT stock FROM parts WHERE id=?",
                    conn,
                    params=(row["part_id"],)
                )["stock"].values[0]

                if stock < required:
                    st.error("Not enough inventory")
                    st.stop()

            for _,row in bom.iterrows():

                required = row["qty"] * qty

                cursor.execute(
                    "UPDATE parts SET stock = stock - ? WHERE id=?",
                    (required,row["part_id"])
                )

            conn.commit()

            cursor.execute(
                "INSERT INTO production(product,qty,time) VALUES(?,?,?)",
                (product,qty,datetime.now().strftime("%Y-%m-%d %H:%M"))
            )

            conn.commit()

            st.success("Production recorded")


# -------------------------
# INVENTORY DASHBOARD
# -------------------------

if menu == "Inventory Dashboard":

    st.header("Inventory")

    parts = pd.read_sql(
        "SELECT name AS Part, stock AS Stock, alert AS Alert_Level FROM parts",
        conn
    )

    st.dataframe(parts,use_container_width=True)

    st.subheader("Low Stock Alerts")

    low = parts[parts["Stock"] <= parts["Alert_Level"]]

    if len(low)==0:
        st.success("All inventory healthy")

    else:
        for _,r in low.iterrows():
            st.error(f"{r['Part']} LOW STOCK ({r['Stock']})")
