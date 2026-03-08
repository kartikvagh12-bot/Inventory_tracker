import streamlit as st
import pandas as pd

st.set_page_config(page_title="Production & Inventory Manager", layout="wide")

st.title("🏭 Production & Inventory Manager")

# -----------------------
# SESSION STORAGE
# -----------------------

if "parts" not in st.session_state:
    st.session_state.parts = []

if "products" not in st.session_state:
    st.session_state.products = {}

if "production_log" not in st.session_state:
    st.session_state.production_log = []

# -----------------------
# MENU
# -----------------------

menu = st.sidebar.radio(
    "Menu",
    [
        "Add Parts",
        "Add Stock",
        "Create Product",
        "Run Production",
        "Inventory",
        "Production History"
    ]
)

# -----------------------
# ADD PARTS
# -----------------------

if menu == "Add Parts":

    st.header("Add Part")

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock", min_value=0)
    alert = st.number_input("Low Stock Alert Level", min_value=0)

    if st.button("Add Part"):

        if name == "":
            st.error("Enter part name")

        else:

            for p in st.session_state.parts:
                if p["name"] == name:
                    st.error("Part already exists")
                    st.stop()

            st.session_state.parts.append({
                "name": name,
                "stock": stock,
                "alert": alert
            })

            st.success("Part added")

    st.subheader("Current Parts")

    for i, part in enumerate(st.session_state.parts):

        col1, col2, col3, col4 = st.columns([3,2,2,1])

        col1.write(part["name"])
        col2.write(f"Stock: {part['stock']}")
        col3.write(f"Alert: {part['alert']}")

        if col4.button("Delete", key=f"del_part_{i}"):

            st.session_state.parts.pop(i)
            st.rerun()

# -----------------------
# ADD STOCK
# -----------------------

if menu == "Add Stock":

    st.header("Add Stock")

    if len(st.session_state.parts) == 0:
        st.warning("Add parts first")

    else:

        part_names = [p["name"] for p in st.session_state.parts]

        selected = st.selectbox("Part", part_names)

        qty = st.number_input("Quantity to Add", min_value=1)

        if st.button("Add Stock"):

            for p in st.session_state.parts:
                if p["name"] == selected:
                    p["stock"] += qty

            st.success("Stock updated")

# -----------------------
# CREATE PRODUCT
# -----------------------

if menu == "Create Product":

    st.header("Create Product")

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

            bom = st.session_state.products[product_name]

            for i, item in enumerate(bom):

                col1, col2, col3 = st.columns([3,2,1])

                col1.write(item["part"])
                col2.write(item["qty"])

                if col3.button("Remove", key=f"remove_{i}"):

                    st.session_state.products[product_name].pop(i)
                    st.rerun()

# -----------------------
# RUN PRODUCTION
# -----------------------

if menu == "Run Production":

    st.header("Run Production")

    if len(st.session_state.products) == 0:
        st.warning("Create product first")

    else:

        product = st.selectbox(
            "Product",
            list(st.session_state.products.keys())
        )

        qty = st.number_input("Quantity Produced", min_value=1)

        if st.button("Run Production"):

            bom = st.session_state.products[product]

            from datetime import datetime

            production_record = {
                "product": product,
                "qty": qty,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "parts_used": []
            }

            # Check stock
            for item in bom:

                part_name = item["part"]
                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == part_name:

                        if p["stock"] < required:

                            st.error(f"Not enough {part_name}")
                            st.stop()

            # Deduct stock
            for item in bom:

                part_name = item["part"]
                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == part_name:

                        p["stock"] -= required

                        production_record["parts_used"].append({
                            "part": part_name,
                            "qty": required
                        })

            st.session_state.production_log.append(production_record)

            st.success("Production completed")

    # UNDO
    if st.button("Undo Last Production"):

        if len(st.session_state.production_log) == 0:

            st.warning("No production history")

        else:

            last = st.session_state.production_log.pop()

            for used in last["parts_used"]:

                for p in st.session_state.parts:

                    if p["name"] == used["part"]:
                        p["stock"] += used["qty"]

            st.success("Last production reversed")

# -----------------------
# INVENTORY
# -----------------------

if menu == "Inventory":

    st.header("Inventory Dashboard")

    if len(st.session_state.parts) == 0:

        st.info("No parts added")

    else:

        df = pd.DataFrame(st.session_state.parts)

        st.dataframe(df, use_container_width=True)

        st.subheader("Low Stock Alerts")

        for part in st.session_state.parts:

            if part["stock"] <= part["alert"]:

                st.error(
                    f"⚠ {part['name']} LOW STOCK — Remaining: {part['stock']}"
                )

        # Manual inventory adjustment

        st.subheader("Adjust Inventory")

        part_names = [p["name"] for p in st.session_state.parts]

        selected = st.selectbox("Select Part", part_names)

        new_stock = st.number_input("Set New Stock", min_value=0)

        if st.button("Update Inventory"):

            for p in st.session_state.parts:

                if p["name"] == selected:
                    p["stock"] = new_stock

            st.success("Inventory updated")

# -----------------------
# PRODUCTION HISTORY
# -----------------------

if menu == "Production History":

    st.header("Production History")

    if len(st.session_state.production_log) == 0:

        st.info("No production recorded yet")

    else:

        history = []

        for item in st.session_state.production_log:

            history.append({
                "Product": item["product"],
                "Quantity": item["qty"],
                "Time": item["time"]
            })

        df = pd.DataFrame(history)

        st.dataframe(df, use_container_width=True)
