import streamlit as st
import sqlite3
import pandas as pd
import io

st.set_page_config(page_title="معمل الأسنان الذكي", layout="centered", page_icon="🦷")

def get_db_connection():
     try:
        import pysqlite3 as sqlite3
    except ImportError:
        import sqlite3
    
    conn = sqlite3.connect('dental_lab_mobile.db', check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()
conn.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL
    )''')
conn.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, amount_paid REAL
    )''')
conn.commit()
conn.close()

st.markdown("""
    <style>
    body { text-align: right; direction: rtl; }
    div.stButton > button:first-child { background-color: #27ae60; color:white; width: 100%; border-radius: 8px; font-weight: bold; }
    div.stDownloadButton > button:first-child { background-color: #2980b9; color:white; width: 100%; border-radius: 8px; font-weight: bold; }
    .stRadio > div { flex-direction: row-reverse; justify-content: center; }
    </style>
""", unsafe_allowed_html=True)

st.title("🦷 معمل الأسنان الذكي")
st.write("نظام الحسابات السريع للموبايل")

conn = get_db_connection()
total_sales = conn.execute("SELECT COALESCE(SUM(price), 0) as total FROM cases").fetchone()['total']
total_paid = conn.execute("SELECT COALESCE(SUM(amount_paid), 0) as total FROM payments").fetchone()['total']
conn.close()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="💰 إجمالي المبيعات", value=f"{total_sales:,.2f}")
with col2:
    st.metric(label="💳 ديون معلقة للأطباء", value=f"{(total_sales - total_paid):,.2f}")

st.markdown("---")

menu = ["📋 تسجيل حالة", "💸 دفعة نقداً", "📊 التقارير والإكسيل"]
choice = st.radio("اختر العملية المطلوبة:", menu)

if choice == "📋 تسجيل حالة":
    st.subheader("إدخال بيانات حالة جديدة")
    with st.form("case_form", clear_on_submit=True):
        doc_name = st.text_input("اسم الطبيب / العيادة")
        patient_name = st.text_input("اسم المريض")
        case_type = st.selectbox("نوع التركيبة", ["زيركون (Zircon)", "إيماكس (E-max)", "بورسلين", "أكريل"])
        price = st.number_input("السعر المتفق عليه", min_value=0.0, step=50.0)
        submit = st.form_submit_button("حفظ وتثبيت الحالة ماليًا")
        
        if submit:
            if doc_name and patient_name and price > 0:
                conn = get_db_connection()
                conn.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price) VALUES (?, ?, ?, ?)",
                             (doc_name, patient_name, case_type, price))
                conn.commit()
                conn.close()
                st.success("✅ تم حفظ الحالة بالفاتورة بنجاح!")
                st.rerun()
            else:
                st.error("⚠️ يرجى ملء كافة البيانات وتحديد السعر!")

elif choice == "💸 دفعة نقداً":
    st.subheader("سند قبض نقدي / تحويل من عيادة")
    with st.form("payment_form", clear_on_submit=True):
        pay_doc = st.text_input("اسم الطبيب المسدد")
        amount = st.number_input("المبلغ المستلم", min_value=0.0, step=100.0)
        submit_pay = st.form_submit_button("تسجيل السند وتحديث الحساب")
        
        if submit_pay:
            if pay_doc and amount > 0:
                conn = get_db_connection()
                conn.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amount))
                conn.commit()
                conn.close()
                st.success("✅ تم إيداع المبلغ وتحديث مديونية الطبيب!")
                st.rerun()
            else:
                st.error("⚠️ يرجى إدخال اسم الطبيب والمبلغ بشكل صحيح!")

elif choice == "📊 التقارير والإكسيل":
    st.subheader("جدول الحالات المسجلة")
    conn = get_db_connection()
    df_cases = pd.read_sql_query("SELECT id as [كود], doctor_name as [الطبيب], patient_name as [المريض], case_type as [النوع], price as [السعر] FROM cases ORDER BY id DESC", conn)
    conn.close()
    
    if not df_cases.empty:
        st.dataframe(df_cases, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_cases.to_excel(writer, index=False, sheet_name='حسابات المعمل')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 تحميل كشف الحساب بصيغة Excel",
            data=excel_data,
            file_name='dental_lab_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
