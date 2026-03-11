import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import base64

# -----------------------
# UI STYLE
# -----------------------

DATA_FILE = "data.json"

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"


# -----------------------
# GITHUB SYNC
# -----------------------

def upload_to_github(data):

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    content = base64.b64encode(
        json.dumps(data, indent=2).encode()
    ).decode()

    r = requests.get(url, headers=headers)

    sha = r.json()["sha"] if r.status_code == 200 else None

    payload = {
        "message": "update data.json",
        "content": content
    }

    if sha:
        payload["sha"] = sha

    requests.put(url, headers=headers, json=payload)


# -----------------------
# PAGE CONFIG
# -----------------------

st.set_page_config(page_title="Production & Inventory Manager", page_icon="🏭", layout="wide")

st.title("🏭 Production & Inventory Manager")
st.caption("Smart stock and production tracking for manufacturing")
st.divider()


# -----------------------
# DATA FUNCTIONS
# -----------------------

def load_data():

    if os.path.exists(DATA_FILE):

        with open(DATA_FILE, "r") as f:
            return json.load(f)

    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"

    r = requests.get(url)

    if r.status_code == 200:

        data = r.json()

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

        return data

    return {
        "parts": [],
        "products": {},
        "production_log": [],
        "inventory_log": []
    }


def save_data():

    data = {
        "parts": st.session_state.parts,
        "products": st.session_state.products,
        "production_log": st.session_state.production_log,
        "inventory_log": st.session_state.inventory_log
    }

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    upload_to_github(data)


# -----------------------
# LOAD DATA
# -----------------------

data = load_data()

if "parts" not in st.session_state:
    st.session_state.parts = data["parts"]

if "products" not in st.session_state:
    st.session_state.products = data["products"]

if "production_log" not in st.session_state:
    st.session_state.production_log = data["production_log"]

if "inventory_log" not in st.session_state:
    st.session_state.inventory_log = data.get("inventory_log", [])

if "temp_parts" not in st.session_state:
    st.session_state.temp_parts = []


# -----------------------
# DASHBOARD
# -----------------------

total_parts = len(st.session_state.parts)
total_products = len(st.session_state.products)
total_runs = len(st.session_state.production_log)

# -----------------------
# DASHBOARD PANELS
# -----------------------

st.subheader("📊 Dashboard")

col1, col2, col3 = st.columns(3)

col1.metric("Total Parts", total_parts)
col2.metric("Products", total_products)
col3.metric("Production Runs", total_runs)

st.divider()

# -----------------------
# TODAY PRODUCTION SUMMARY
# -----------------------

today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

today_runs = 0
today_units = 0
product_counts = {}

for run in st.session_state.production_log:

    if run["time"].startswith(today):

        today_runs += 1
        today_units += run["qty"]

    product = run["product"]

    product_counts[product] = product_counts.get(product, 0) + run["qty"]

most_product = max(product_counts, key=product_counts.get) if product_counts else "None"

col1, col2, col3 = st.columns(3)

col1.metric("Today's Production Runs", today_runs)
col2.metric("Units Produced Today", today_units)
col3.metric("Most Produced Product", most_product)

low_stock = sum(1 for p in st.session_state.parts if p["stock"] <= p["alert"])

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Parts", total_parts)
col2.metric("Products", total_products)
col3.metric("Low Stock Alerts", low_stock)
col4.metric("Production Runs", total_runs)

st.divider()


# -----------------------
# RESET
# -----------------------

if st.sidebar.button("Reset All Data"):

    st.session_state.parts = []
    st.session_state.products = {}
    st.session_state.production_log = []
    st.session_state.inventory_log = []
    st.session_state.temp_parts = []

    save_data()

    st.success("All data reset")

    st.rerun()


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
        "Inventory History",
        "Production History"
    ]
)

# clear temporary list when leaving page
if menu != "Add Parts":
    st.session_state.temp_parts = []


# -----------------------
# ADD PARTS
# -----------------------

if menu == "Add Parts":

    st.header("Add Part")

    name = st.text_input("Part Name")
    stock = st.number_input("Initial Stock", min_value=0)
    alert = st.number_input("Low Stock Alert Level", min_value=0)

    if st.button("Add Part", type="primary"):

        if name == "":
            st.error("Enter part name")

        elif any(p["name"] == name for p in st.session_state.parts):
            st.error("Part already exists")

        else:

            new_part = {
                "name": name,
                "stock": stock,
                "alert": alert
            }

            st.session_state.parts.append(new_part)
            st.session_state.inventory_log.append({
                "Time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p"),
                "Part": name,
                "Previous Stock": 0,
                "Change": stock,
                "New Stock": stock,
                "Reason": "Part Created"
            })
            st.session_state.temp_parts.append(new_part)

            save_data()

            st.success("Part added")

            st.rerun()

    st.divider()
    st.subheader("Recently Added")

    for i, part in reversed(list(enumerate(st.session_state.temp_parts))):

        col1, col2, col3, col4 = st.columns([4,2,2,1])

        col1.write(part["name"])
        col2.write(f"Stock: {part['stock']}")
        col3.write(f"Alert: {part['alert']}")

        if col4.button("❌", key=f"temp_delete_{i}"):

            # check if part is used in any product
            used_in = []
        
            for product, bom in st.session_state.products.items():
                for item in bom:
                    if item["part"] == part["name"]:
                        used_in.append(product)
        
            if used_in:
        
                product_list = ", ".join(used_in)
        
                st.error(
                    f'Cannot delete "{part["name"]}" — used in product(s): {product_list}'
                )
        
            else:
        
                st.session_state.parts.remove(part)
                st.session_state.temp_parts.pop(i)
        
                save_data()
        
                st.rerun()


# -----------------------
# ADD STOCK
# -----------------------

if menu == "Add Stock":

    st.header("Add Stock")

    if not st.session_state.parts:
        st.warning("Add parts first")

    else:

        part_names = [p["name"] for p in st.session_state.parts]

        selected = st.selectbox("Part", part_names)

        qty = st.number_input("Quantity to Add", min_value=1)

        if st.button("Add Stock"):

            for p in st.session_state.parts:

                if p["name"] == selected:

                    previous = p["stock"]

                    p["stock"] += qty

                    st.session_state.inventory_log.append({
                        "Time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p"),
                        "Part": selected,
                        "Previous Stock": previous,
                        "Change": qty,
                        "New Stock": p["stock"],
                        "Reason": "Stock Added"
                    })

            save_data()

            st.success("Stock updated")


# -----------------------
# CREATE PRODUCT
# -----------------------

if menu == "Create Product":

    st.header("Create / Edit Product")

    if len(st.session_state.parts) == 0:
        st.warning("Add parts first")

    else:

        # -----------------------
        # SELECT OR CREATE PRODUCT
        # -----------------------

        product_list = list(st.session_state.products.keys())

        selected_product = st.selectbox(
            "Select Existing Product (or create new)",
            ["Create New Product"] + product_list
        )

        if selected_product == "Create New Product":

            product_name = st.text_input("New Product Name")

        else:

            product_name = selected_product

            st.info(f"Editing product: {product_name}")

        # -----------------------
        # ADD PART TO PRODUCT
        # -----------------------

        part_names = [p["name"] for p in st.session_state.parts]

        part = st.selectbox("Part", part_names)

        qty = st.number_input("Quantity Needed", min_value=1)

        if st.button("Add Part to Product"):

            if product_name.strip() == "":
                st.error("Enter product name")
                st.stop()

            if product_name not in st.session_state.products:
                st.session_state.products[product_name] = []
            elif product_name in st.session_state.products and selected_product == "Create New Product":
                st.error("Product already exists")
                st.stop()

            # Prevent duplicate parts
            for item in st.session_state.products[product_name]:
                if item["part"] == part:
                    st.error("Part already exists in this product")
                    st.stop()

            st.session_state.products[product_name].append({
                "part": part,
                "qty": qty
            })

            save_data()

            st.success("Part added to product")

            st.rerun()

        # -----------------------
        # SHOW PRODUCT BOM
        # -----------------------

        if product_name in st.session_state.products:

            st.divider()
            st.subheader("Parts in Product")

            bom = st.session_state.products[product_name]

            if len(bom) == 0:
                st.info("No parts added yet")

            else:

                for i, item in enumerate(bom):

                    col1, col2, col3 = st.columns([4,2,1])

                    col1.write(item["part"])
                    col2.write(f"Qty: {item['qty']}")

                    if col3.button("❌", key=f"remove_bom_{product_name}_{i}"):

                        st.session_state.products[product_name].pop(i)

                        save_data()

                        st.success("Part removed")

                        st.rerun()


# -----------------------
# RUN PRODUCTION
# -----------------------

if menu == "Run Production":

    st.header("Run Production")

    if not st.session_state.products:
        st.warning("Create product first")

    else:

        product = st.selectbox("Product", list(st.session_state.products.keys()))

        qty = st.number_input("Quantity Produced", min_value=1)

        if st.button("Run Production"):

            bom = st.session_state.products[product]

            production_record = {
                "product": product,
                "qty": qty,
                "time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p"),
                "parts_used": []
            }

            shortages = []

            for item in bom:

                required = item["qty"] * qty

                part = next(p for p in st.session_state.parts if p["name"] == item["part"])

                if part["stock"] < required:
                    shortages.append(f"{item['part']} (need {required}, have {part['stock']})")

            if shortages:

                st.error("Insufficient stock:")

                for s in shortages:
                    st.write("•", s)

                st.stop()

            for item in bom:

                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == item["part"]:

                        previous = p["stock"]

                        p["stock"] -= required

                        production_record["parts_used"].append({
                            "part": p["name"],
                            "qty": required
                        })

                        st.session_state.inventory_log.append({
                            "Time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p"),
                            "Part": p["name"],
                            "Previous Stock": previous,
                            "Change": -required,
                            "New Stock": p["stock"],
                            "Reason": f"Production: {product}"
                        })

            st.session_state.production_log.append(production_record)

            save_data()

            st.success("Production completed")


# -----------------------
# INVENTORY
# -----------------------

if menu == "Inventory":

    st.header("Inventory Dashboard")

    df = pd.DataFrame(st.session_state.parts).sort_values("name")

    df.index += 1

    st.dataframe(df, use_container_width=True)

        # LOW STOCK ALERTS
    st.subheader("Low Stock Alerts")

    low_found = False
    
    for part in st.session_state.parts:
    
        if part["stock"] <= part["alert"]:
    
            used_in = []
    
            for product, bom in st.session_state.products.items():
                for item in bom:
                    if item["part"] == part["name"]:
                        used_in.append(product)
    
            product_list = ", ".join(used_in) if used_in else "No products"
    
            st.error(
                f"⚠ {part['name']} LOW STOCK — Remaining: {part['stock']} | Used in: {product_list}"
            )
    
            low_found = True
     
    if not low_found:
        st.success("All inventory levels are healthy")

    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="Download Inventory Report (CSV)",
        data=csv,
        file_name="inventory_report.csv",
        mime="text/csv"
    )

    st.subheader("Adjust Inventory")

    part_names = [p["name"] for p in st.session_state.parts]

    selected = st.selectbox("Select Part", part_names)

    new_stock = st.number_input("Set New Stock", min_value=0)

    if st.button("Update Inventory"):

        for p in st.session_state.parts:
    
            if p["name"] == selected:
    
                previous_stock = p["stock"]
                
                if new_stock == previous_stock:
                    st.warning("Stock already at this level")
                    st.stop()
    
                change = new_stock - previous_stock
    
                p["stock"] = new_stock
    
                st.session_state.inventory_log.append({
                    "Time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p"),
                    "Part": p["name"],
                    "Previous Stock": previous_stock,
                    "Change": change,
                    "New Stock": new_stock,
                    "Reason": "Manual Adjustment"
                })
    
        save_data()
    
        st.success("Inventory updated")
    
        st.rerun()


# -----------------------
# INVENTORY HISTORY
# -----------------------

if menu == "Inventory History":

    st.header("Inventory History")

    if not st.session_state.inventory_log:
        st.info("No inventory changes recorded yet")

    else:

        df = pd.DataFrame(st.session_state.inventory_log).sort_values("Time", ascending=False)

        df.index += 1

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="Download Inventory History (CSV)",
            data=csv,
            file_name="inventory_history.csv",
            mime="text/csv"
        )


# -----------------------
# PRODUCTION HISTORY
# -----------------------

if menu == "Production History":

    st.header("Production History")

    if not st.session_state.production_log:
        st.info("No production recorded yet")

    else:

        history = []

        for item in st.session_state.production_log:
        
            parts_used = ", ".join(
                [f"{p['part']} ({p['qty']})" for p in item.get("parts_used", [])]
            )
        
            history.append({
                "Product": item["product"],
                "Quantity": item["qty"],
                "Materials Used": parts_used,
                "Time": item["time"]
            })
        
        df = pd.DataFrame(history).sort_values("Time", ascending=False)

        df.index += 1

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="Download Production Report (CSV)",
            data=csv,
            file_name="production_report.csv",
            mime="text/csv"
        )


# -----------------------
# FOOTER
# -----------------------

st.sidebar.markdown("---")
st.sidebar.caption("Production & Inventory Manager")
st.sidebar.caption("© 2026 Kartik Vagh")
