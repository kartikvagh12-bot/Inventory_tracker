import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Manufacturing Inventory System", layout="wide")
st.title("Production & Inventory Manager")

# DATABASE
conn = sqlite3.connect("inventory.db", check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute("""
CREATE TABLE IF NOT EXISTS parts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
stock INTEGER,
alert INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS bom(
product_id INTEGER,
part_id INTEGER,
quantity INTEGER
)
""")

conn.commit()

st.title("Manufacturing Inventory Demo")

menu = st.sidebar.selectbox(
"Menu",
["Add Parts","Create Product","Record Production","Inventory Dashboard"]
)

# ADD PARTS
if menu == "Add Parts":

    st.header("Add New Part")

    name = st.text_input("Part Name")
    stock = st.number_input("Stock Quantity",0)
    alert = st.number_input("Low Stock Alert Level",0)

    if st.button("Add Part"):
        c.execute(
        "INSERT INTO parts(name,stock,alert) VALUES(?,?,?)",
        (name,stock,alert)
        )
        conn.commit()
        st.success("Part added")

    st.subheader("Existing Parts")
    parts = pd.read_sql("SELECT * FROM parts",conn)
    st.dataframe(parts)


# CREATE PRODUCT
if menu == "Create Product":

    st.header("Create Product")

    product_name = st.text_input("Product Name")

    parts = pd.read_sql("SELECT * FROM parts",conn)

    selected_part = st.selectbox("Select Part",parts["name"])
    quantity = st.number_input("Quantity Required",1)

    if st.button("Create Product"):
        c.execute(
        "INSERT INTO products(name) VALUES(?)",
        (product_name,)
        )
        conn.commit()

        product_id = c.lastrowid

        part_id = parts[parts["name"]==selected_part]["id"].values[0]

        c.execute(
        "INSERT INTO bom(product_id,part_id,quantity) VALUES(?,?,?)",
        (product_id,part_id,quantity)
        )

        conn.commit()
        st.success("Product created")


# RECORD PRODUCTION
if menu == "Record Production":

    st.header("Production Entry")

    products = pd.read_sql("SELECT * FROM products",conn)

    if len(products) == 0:
        st.warning("Create product first")

    else:

        product_name = st.selectbox("Select Product",products["name"])
        qty = st.number_input("Quantity Produced",1)

        if st.button("Update Inventory"):

            product_id = products[products["name"]==product_name]["id"].values[0]

            bom = pd.read_sql(
            f"SELECT * FROM bom WHERE product_id={product_id}",
            conn
            )

            for _,row in bom.iterrows():

                part_id = row["part_id"]
                required = row["quantity"] * qty

                c.execute(
                "UPDATE parts SET stock = stock - ? WHERE id=?",
                (required,part_id)
                )

            conn.commit()

            st.success("Inventory updated")


# DASHBOARD
if menu == "Inventory Dashboard":

    st.header("Inventory")

    parts = pd.read_sql("SELECT * FROM parts",conn)

    st.dataframe(parts)

    st.subheader("Low Stock Alerts")

    for _,row in parts.iterrows():

        if row["stock"] <= row["alert"]:
            st.error(
            f"{row['name']} LOW STOCK: {row['stock']} remaining"
            )
