import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import requests
import base64

DATA_FILE = "data.json"

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"


def upload_to_github(data):

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    content = base64.b64encode(
        json.dumps(data, indent=2).encode()
    ).decode()

    # check if file exists
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        sha = r.json()["sha"]
    else:
        sha = None

    payload = {
        "message": "update data.json",
        "content": content,
        "sha": sha
    }

    requests.put(url, headers=headers, json=payload)

st.set_page_config(page_title="Production & Inventory Manager", layout="wide")

st.title("🏭 Production & Inventory Manager")

# -----------------------
# DATA FUNCTIONS
# -----------------------

def load_data():

    if os.path.exists(DATA_FILE):

        with open(DATA_FILE, "r") as f:
            return json.load(f)

    # try loading from github
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
        "production_log": []
    }


def save_data():

    data = {
        "parts": st.session_state.parts,
        "products": st.session_state.products,
        "production_log": st.session_state.production_log
    }

    # save locally
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # backup to github
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

# -----------------------
# DASHBOARD SUMMARY
# -----------------------

total_parts = len(st.session_state.parts)
total_products = len(st.session_state.products)
total_runs = len(st.session_state.production_log)

low_stock = 0
for part in st.session_state.parts:
    if part["stock"] <= part["alert"]:
        low_stock += 1

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Parts", total_parts)
col2.metric("Products", total_products)
col3.metric("Low Stock Alerts", low_stock)
col4.metric("Production Runs", total_runs)
st.divider()

# -----------------------
# PRODUCTION SUMMARY
# -----------------------

today = datetime.now().strftime("%Y-%m-%d")

today_runs = 0
today_units = 0

product_counts = {}

for run in st.session_state.production_log:

    if run["time"].startswith(today):

        today_runs += 1
        today_units += run["qty"]

    product = run["product"]

    if product not in product_counts:
        product_counts[product] = 0

    product_counts[product] += run["qty"]

most_product = "None"
most_count = 0

for p, q in product_counts.items():

    if q > most_count:
        most_product = p
        most_count = q


col1, col2, col3 = st.columns(3)

col1.metric("Today's Production Runs", today_runs)
col2.metric("Units Produced Today", today_units)
col3.metric("Most Produced Product", most_product)

# -----------------------
# RESET BUTTON
# -----------------------

if st.sidebar.button("Reset All Data"):

    st.session_state.parts = []
    st.session_state.products = {}
    st.session_state.production_log = []

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

            save_data()

            st.success("Part added")

    st.subheader("Current Parts")

    for i, part in enumerate(st.session_state.parts):

        col1, col2, col3, col4 = st.columns([3,2,2,1])

        col1.write(part["name"])
        col2.write(f"Stock: {part['stock']}")
        col3.write(f"Alert: {part['alert']}")

        if col4.button("Delete", key=f"del_part_{i}"):

            st.session_state.parts.pop(i)

            save_data()

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

            save_data()

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

            save_data()

        if product_name in st.session_state.products:

            st.subheader("Parts in Product")

            bom = st.session_state.products[product_name]

            for i, item in enumerate(bom):

                col1, col2, col3 = st.columns([3,2,1])

                col1.write(item["part"])
                col2.write(item["qty"])

                if col3.button("Remove", key=f"remove_{i}"):

                    st.session_state.products[product_name].pop(i)

                    save_data()

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

            production_record = {
                "product": product,
                "qty": qty,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "parts_used": []
            }

            # check stock
            for item in bom:

                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == item["part"]:

                        if p["stock"] < required:
                            st.error(f"Not enough {p['name']}")
                            st.stop()

            # deduct stock
            for item in bom:

                required = item["qty"] * qty

                for p in st.session_state.parts:

                    if p["name"] == item["part"]:

                        p["stock"] -= required

                        production_record["parts_used"].append({
                            "part": p["name"],
                            "qty": required
                        })

            st.session_state.production_log.append(production_record)

            save_data()

            st.success("Production completed")

    if st.button("Undo Last Production"):

        if len(st.session_state.production_log) == 0:

            st.warning("No production history")

        else:

            last = st.session_state.production_log.pop()

            for used in last["parts_used"]:

                for p in st.session_state.parts:

                    if p["name"] == used["part"]:
                        p["stock"] += used["qty"]

            save_data()

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

        search = st.text_input("Search Part")

        filtered_parts = [
            p for p in st.session_state.parts
            if search.lower() in p["name"].lower()
        ]
        
        df = pd.DataFrame(filtered_parts)

        df.index = df.index + 1

        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="Download Inventory Report (CSV)",
            data=csv,
            file_name="inventory_report.csv",
            mime="text/csv"
        )

        st.subheader("Low Stock Alerts")

        for part in st.session_state.parts:

            if part["stock"] <= part["alert"]:

                st.error(
                    f"⚠ {part['name']} LOW STOCK — Remaining: {part['stock']}"
                )

        st.subheader("Adjust Inventory")

        part_names = [p["name"] for p in st.session_state.parts]

        selected = st.selectbox("Select Part", part_names)

        new_stock = st.number_input("Set New Stock", min_value=0)

        if st.button("Update Inventory"):

            for p in st.session_state.parts:

                if p["name"] == selected:
                    p["stock"] = new_stock

            save_data()

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

        df.index = df.index + 1

        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="Download Production Report (CSV)",
            data=csv,
            file_name="production_report.csv",
            mime="text/csv"
        )
