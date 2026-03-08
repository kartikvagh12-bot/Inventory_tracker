import streamlit as st
import pandas as pd

st.set_page_config(page_title="Inventory Production Manager", layout="wide")

st.title("🏭 Production & Inventory Manager")

# ---------------------------
# SESSION STORAGE
# ---------------------------

if "parts" not in st.session_state:
    st.session_state.parts = []

if "products" not in st.session_state:
    st.session_state.products = {}

# ---------------------------
# MENU
# ---------------------------

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

# ---------------------------
# ADD PART
# ---------------------------

if menu == "Add Part":

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock", min_value=0)

    if st.button("Add Part"):

        st.session_state.parts.append({
            "name": name,
            "stock": stock
        })

        st.success("Part added")

# ---------------------------
# ADD STOCK
# ---------------------------

if menu == "Add Stock":

    if len(st.session_state.parts) == 0:

        st.warning("Add parts first")

    else:

        part_names = [p["name"] for p in st.session_state.parts]

        selected = st.selectbox("Part", part_names)

        qty = st.number_input("Quantity to Add", min_value=1)

        if st.button("Update Stock"):

            for p in st.session_state.parts:

                if p["name"] == selected:
                    p["stock"] += qty

            st.success("Stock updated")

# ---------------------------
# CREATE PRODUCT
# ---------------------------

if menu == "Create Product":

    product_name = st.text_input("Product Name")

    if len(st.session_state.parts) == 0:

        st.warning("Add parts first")

    else:

        part_names = [p["name"] for p in st.session_state.parts]

        part = st.selectbox("Part", part_names)

        qty = st.number_input("Quantity Needed", min_value=1)

        if st.button("Add Part to Product"):

            if product_name not in st.session_state.products:
                st.session_state.products[product_name] = []

            st.session_state.products[product_name].append({
                "part": part,
                "qty": qty
            })

        if product_name in st.session_state.products:

            st.subheader("Parts in Product")

            st.table(st.session_state.products[product_name])

# ---------------------------
# RUN PRODUCTION
# ---------------------------

if menu == "Run Production":

    if len(st.session_state.products) == 0:

        st.warning("Create a product first")

    else:

        product = st.selectbox(
            "Product",
            list(st.session_state.products.keys())
        )

        qty = st.number_input("Quantity Produced", min_value=1)

        if st.button("Run Production"):

            bom = st.session_state.products[product]

            for item in bom:

                part_name = item["part"]
                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == part_name:

                        if p["stock"] < required:

                            st.error(
                                f"Not enough {part_name}"
                            )
                            st.stop()

            for item in bom:

                part_name = item["part"]
                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == part_name:
                        p["stock"] -= required

            st.success("Production completed")

# ---------------------------
# INVENTORY
# ---------------------------

if menu == "Inventory":

    if len(st.session_state.parts) == 0:

        st.info("No parts added")

    else:

        df = pd.DataFrame(st.session_state.parts)

        st.dataframe(df, use_container_width=True)
