import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

# --- DATABASE SETUP ---


def init_db():
    conn = sqlite3.connect('solar_repair_web.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, model TEXT, 
                  condition TEXT, parts TEXT, cost TEXT, date TEXT)''')
    conn.commit()
    return conn


conn = init_db()

# --- ARABIC HELPER ---


def fix_ar(text):
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

# --- PDF GENERATOR ---


def generate_pdf(data, is_ar):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Try to load a font that supports Arabic
    # Note: For web hosting, you should upload 'arial.ttf' to your GitHub folder
    try:
        pdfmetrics.registerFont(TTFont('ArabicFont', 'arial.ttf'))
        c.setFont("ArabicFont", 14)
    except:
        c.setFont("Helvetica", 12)

    title = "إيصال إصلاح" if is_ar else "Repair Receipt"
    c.drawCentredString(300, 750, fix_ar(title))

    y = 700
    headers = ["ID", "Date", "Customer", "Model", "Condition", "Parts", "Cost"]
    for i, h in enumerate(headers):
        line = f"{h}: {data[i]}"
        c.drawString(100, y, fix_ar(line))
        y -= 30

    c.save()
    buffer.seek(0)
    return buffer


# --- STREAMLIT UI ---
st.set_page_config(page_title="Solar Repair Web", layout="wide")

# Sidebar
st.sidebar.title("🛠️ Repair Manager")
lang = st.sidebar.radio("Language / اللغة", ["English", "العربية"])
is_ar = lang == "العربية"

t = {
    "title": "مدير إصلاح عواكس الطاقة" if is_ar else "Solar Inverter Repair Manager",
    "m1": "١. إدارة العملاء" if is_ar else "1. Customer Management",
    "m2": "٢. تفاصيل الإصلاح" if is_ar else "2. Repair Details",
    "m3": "٣. سجل الإصلاحات" if is_ar else "3. Repair History",
    "name": "اسم العميل:" if is_ar else "Customer Name:",
    "model": "الموديل:" if is_ar else "Model:",
    "cost": "التكلفة:" if is_ar else "Cost:",
    "save": "حفظ البيانات" if is_ar else "Save Repair",
    "search": "بحث..." if is_ar else "Search...",
}

st.title(t["title"])

# --- CUSTOMER SECTION ---
with st.expander(t["m1"]):
    c_col1, c_col2 = st.columns([3, 1])
    new_c = c_col1.text_input(t["name"], key="new_cust")
    if c_col2.button("Add / إضافة") and new_c:
        try:
            conn.execute("INSERT INTO customers (name) VALUES (?)", (new_c,))
            conn.commit()
            st.success("Done!")
        except:
            st.warning("Exists!")

# Get customers for dropdown
cust_list = [r[0] for r in conn.execute(
    "SELECT name FROM customers ORDER BY name ASC").fetchall()]

# --- REPAIR SECTION ---
st.header(t["m2"])
with st.form("repair_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    c_select = col1.selectbox(t["name"], [""] + cust_list)
    r_model = col1.text_input(t["model"])
    r_cond = col2.text_input("Condition / الحالة")
    r_parts = col2.text_input("Parts / القطع")

    col3, col4 = st.columns(2)
    r_cost = col3.text_input(t["cost"])
    r_curr = col4.selectbox("Currency", ["$", "LBP"])

    if st.form_submit_button(t["save"]):
        if c_select and r_model:
            date_str = datetime.now().strftime("%Y-%m-%d")
            full_cost = f"{r_cost} {r_curr}"
            conn.execute("INSERT INTO repairs (customer, model, condition, parts, cost, date) VALUES (?,?,?,?,?,?)",
                         (c_select, r_model, r_cond, r_parts, full_cost, date_str))
            conn.commit()
            st.success("Saved Successfully!")
        else:
            st.error("Missing Data!")

# --- HISTORY & SEARCH ---
st.header(t["m3"])
search = st.text_input(t["search"])

# Load Data
df = pd.read_sql_query("SELECT * FROM repairs ORDER BY id DESC", conn)
if search:
    df = df[df['customer'].str.contains(
        search, case=False) | df['model'].str.contains(search, case=False)]

# Display Table
st.dataframe(df, use_container_width=True)

# Selection for PDF Export
if not df.empty:
    st.subheader("📄 Generate Receipt")
    selected_id = st.selectbox("Select ID to print", df['id'].tolist())
    if st.button("Prepare PDF"):
        row = df[df['id'] == selected_id].iloc[0].tolist()
        pdf_file = generate_pdf(row, is_ar)
        st.download_button(
            label="⬇️ Download PDF Receipt",
            data=pdf_file,
            file_name=f"Receipt_{selected_id}.pdf",
            mime="application/pdf"
        )
