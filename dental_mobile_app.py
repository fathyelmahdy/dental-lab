import streamlit as st
import pandas as pd
import sqlite3
import io

st.set_page_config(page_title="معمل الأسنان", layout="centered")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('dental_lab_mobile.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, amount_paid REAL)")
conn.commit()

st.title("🦷 معمل الأسنان الذكي")

# جلب الإحصائيات
cursor.execute("SELECT SUM(price) FROM cases")
row_sales = cursor.fetchone()
total_sales = float(row_sales[0]) if row_sales and row_sales[0] is not None else 0.0

cursor.execute("SELECT SUM(amount_paid) FROM payments")
row_paid = cursor.fetchone()
total_paid = float(row_paid[0]) if row_paid and row_paid[0] is not None else 0.0

remaining = total_sales - total_paid

# عرض البيانات
col1, col2 = st.columns(2)
col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f}")
col2.metric("💳 ديون الأطباء", f"{remaining:,.2f}")

st.markdown("---")
menu = ["📋 تسجيل حالة", "💸 دفعة نقداً", "📊 التقارير والإكسيل"]
choice = st.selectbox("اختر العملية:", menu)

if choice == "📋 تسجيل حالة":
    st.subheader("إدخال حالة جديدة")
    with st.form("f1", clear_on_submit=True):
        doc = st.text_input("اسم الطبيب")
        pat = st.text_input("اسم المريض")
        ctype = st.selectbox("النوع", ["زيركون", "إيماكس", "بورسلين", "أكريل"])
        price = st.number_input("السعر", min_value=0.0, step=50.0)
        if st.form_submit_button("حفظ الحالة"):
            if doc and pat and price > 0:
                cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price) VALUES (?, ?, ?, ?)", (doc, pat, ctype, price))
                conn.commit()
                st.success("✅ تم الحفظ!")
                st.rerun()

elif choice == "💸 دفعة نقداً":
    st.subheader("تسجيل مبلغ مستلم")
    with st.form("f2", clear_on_submit=True):
        doc = st.text_input("اسم الطبيب")
        amt = st.number_input("المبلغ", min_value=0.0, step=100.0)
        if st.form_submit_button("حفظ السند"):
            if doc and amt > 0:
                cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (doc, amt))
                conn.commit()
                st.success("✅ تم إيداع المبلغ!")
                st.rerun()

elif choice == "📊 التقارير والإكسيل":
    st.subheader("الحالات المسجلة")
    df = pd.read_sql_query("SELECT id as [كود], doctor_name as [الطبيب], patient_name as [المريض], case_type as [النوع], price as [السعر] FROM cases ORDER BY id DESC", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df.to_excel(w, index=False)
        st.download_button(label="📥 تحميل ملف Excel", data=out.getvalue(), file_name='report.xlsx', mime='application/vnd.ms-excel')
    else:
        st.info("لا توجد بيانات حالياً.")

conn.close()
