import streamlit as st
import pandas as pd
import sqlite3
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل والكمبيوتر
st.set_page_config(page_title="معمل الأسنان المحترف", layout="centered", page_icon="🦷")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('dental_lab_advanced_mobile.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء وتحديث الجداول المترابطة بدون أي تعقيدات مستخدمين
cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, phone TEXT
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, specialty TEXT, default_commission REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL,
        tech_name TEXT, tech_commission REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, amount_paid REAL
    )''')
conn.commit()

try:
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_name TEXT")
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_commission REAL DEFAULT 0.0")
    conn.commit()
except sqlite3.OperationalError:
    pass

st.title("🦷 نظام معمل الأسنان الذكي")
st.write("الإصدار المفتوح الشامل - مبيعات وعمولات وفواتير بالجنيه المصري")

# جلب قوائم البيانات لملء الخيارات المنسدلة تلقائياً
cursor.execute("SELECT name FROM doctors")
list_docs = [r for r in cursor.fetchall()]

cursor.execute("SELECT name, price FROM products")
dict_products = {r: r for r in cursor.fetchall()}

cursor.execute("SELECT name, default_commission FROM technicians")
dict_techs = {r: r for r in cursor.fetchall()}

# --- حساب وعرض الماليّات العامة للمعمل بالأعلى ---
total_sales, total_paid, total_tech_commissions = 0.0, 0.0, 0.0
try:
    cursor.execute("SELECT SUM(price) FROM cases")
    res_sales = cursor.fetchone()
    total_sales = float(res_sales) if res_sales and res_sales is not None else 0.0

    cursor.execute("SELECT SUM(amount_paid) FROM payments")
    res_paid = cursor.fetchone()
    total_paid = float(res_paid) if res_paid and res_paid is not None else 0.0

    cursor.execute("SELECT SUM(tech_commission) FROM cases")
    res_tech = cursor.fetchone()
    total_tech_commissions = float(res_tech) if res_tech and res_tech is not None else 0.0
except Exception:
    pass

remaining_debts = total_sales - total_paid

col1, col2, col3 = st.columns(3)
col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f} ج.م")
col2.metric("💳 ديون الأطباء", f"{remaining_debts:,.2f} ج.م")
col3.metric("🛠️ عمولات الفنيين", f"{total_tech_commissions:,.2f} ج.م")
st.markdown("---")

# تصميم القائمة العريضة كخيارات راديو واضحة جداً وكبيرة للتنقل الفوري
menu_options = ["cases", "doctors", "technicians", "prices", "payments", "reports"]

choice_display = {
    "cases": "📋 إدارة الحالات",
    "doctors": "👨‍⚕️ دليل الأطباء",
    "technicians": "🧑‍🏭 حسابات الفنيين",
    "prices": "⚙️ كتالوج الأسعار",
    "payments": "💸 تسجيل المقبوضات",
    "reports": "📊 التقارير والفواتير"
}

choice = st.radio("⬇️ اختر الشاشة المطلوبة لعرض خياراتها بالكامل:", menu_options, format_func=lambda x: choice_display[x], horizontal=True)
st.markdown("---")

if choice == "cases":
    st.subheader("تسجيل حالة جديدة وتحديد الفني")
    with st.form("case_form_free", clear_on_submit=True):
        selected_doc = st.selectbox("اختر الطبيب", list_docs if list_docs else ["لا يوجد أطباء مسجلين - اضغط على دليل الأطباء بالأعلى لإضافتهم"])
        patient = st.text_input("اسم المريض")
        selected_type = st.selectbox("نوع التركيبة", list(dict_products.keys()) if dict_products else ["لا يوجد تركيبات - اضغط على كتالوج الأسعار بالأعلى لإضافتها"])
        selected_tech = st.selectbox("الفني المسؤول عن الحالة", list(dict_techs.keys()) if dict_techs else ["لا يوجد فنيين - اضغط على حسابات الفنيين بالأعلى لإضافتهم"])
        
        suggested_price = dict_products.get(selected_type, 0.0)
        suggested_comm = dict_techs.get(selected_tech, 0.0)
        
        st.info(f"💵 السعر الافتراضي: {suggested_price:,.2f} ج.م | 🛠️ عمولة الفني: {suggested_comm:,.2f} ج.م")
        
        final_price = st.number_input("تأكيد السعر النهائي (ج.م)", min_value=0.0, value=suggested_price)
        final_comm = st.number_input("تأكيد عمولة الفني (ج.م)", min_value=0.0, value=suggested_comm)
        
        if st.form_submit_button("حفظ وتثبيت الحالة"):
            if not list_docs or not dict_products or not dict_techs:
                st.error("⚠️ خطأ: لا يمكنك الحفظ قبل إضافة طبيب، تركيبة، وفني واحد على الأقل من القوائم بالأعلى!")
            elif patient:
                cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                               (selected_doc, patient, selected_type, final_price, selected_tech, final_comm))
                conn.commit()
                st.success("✅ تم حفظ وفحص الطلب ماليًا بنجاح!")
                st.rerun()
            else:
                st.error("يرجى كتابة اسم المريض")

elif choice == "doctors":
    st.subheader("👨‍⚕️ دليل عيادات الأسنان والعملاء")
    with st.form("doc_form_free", clear_on_submit=True):
        new_doc = st.text_input("اسم الطبيب الجديد")
        phone_doc = st.text_input("رقم هاتف العيادة")
        if st.form_submit_button("إضافة الطبيب للنظام"):
            if new_doc:
                try:
                    cursor.execute("INSERT INTO doctors (name, phone) VALUES (?, ?)", (new_doc, phone_doc))
                    conn.commit()
                    st.success("🎉 تم تسجيل الطبيب بنجاح!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الطبيب مسجل مسبقاً!")
            else:
                st.error("برجاء إدخال اسم الطبيب أولاً!")
    df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)
    st.dataframe(df_docs, use_container_width=True)

elif choice == "technicians":
    st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")
    with st.form("tech_form_free", clear_on_submit=True):
        t_name = st.text_input("اسم الفني الجديد")
        t_spec = st.text_input("التخصص")
        t_comm = st.number_input("قيمة العموله الافتراضية لكل سن (ج.م)", min_value=0.0, step=10.0)
        if st.form_submit_button("تسجيل الفني بالمعمل"):
            if t_name:
                try:
                    cursor.execute("INSERT INTO technicians (name, specialty, default_commission) VALUES (?, ?, ?)", (t_name, t_spec, t_comm))
                    conn.commit()
                    st.success("🎉 تم تسجيل الفني بنجاح!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الفني مسجل مسبقاً!")
            else:
                st.error("يرجى كتابة اسم الفني")
    df_tech_report = pd.read_sql_query("SELECT tech_name as [اسم الفني], COUNT(id) as [عدد الحالات], SUM(tech_commission) as [إجمالي المستحقات (ج.م)] FROM cases WHERE tech_name IS NOT NULL GROUP BY tech_name", conn)
    st.dataframe(df_tech_report, use_container_width=True)

elif choice == "prices":
    st.subheader("⚙️ قائمة أسعار خدمات وتركيبات المعمل")
    with st.form("product_form_free", clear_on_submit=True):
        p_name = st.text_input("اسم التركيبة")
        p_price = st.number_input("السعر الافتراضي للسن (ج.م)", min_value=0.0, step=50.0)
        if st.form_submit_button("حفظ للكتالوج"):
            if p_name and p_price > 0:
                try:
                    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (p_name, p_price))
                    conn.commit()
                    st.success("✅ تم التحديث الافتراضي بقائمة الأسعار!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("مضافة بالفعل!")
    df_prods = pd.read_sql_query("SELECT name as [نوع التركيبة], price as [السعر الافتراضي (ج.م)] FROM products", conn)
    st.dataframe(df_prods, use_container_width=True)

elif choice == "payments":
    st.subheader("💸 استلام دفعات نقدية من الأطباء")
    if list_docs:
        with st.form("pay_form_free", clear_on_submit=True):
            pay_doc = st.selectbox("الطبيب المسدد", list_docs)
            amt = st.number_input("المبلغ المستلم (ج.م)", min_value=0.0, step=100.0)
            if st.form_submit_button("تسجيل السند وتحديث الخزنة"):
                if amt > 0:
                    cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amt))
                    conn.commit()
                    st.success("✅ تم تسجيل السند وتحديث كشف حساب العيادة!")
                    st.rerun()
    else:
        st.info("لم يتم تسجيل أي عيادات أو أطباء بعد لتسجيل مقبوضات ماليّة لهم.")

elif choice == "reports":
    st.subheader("📊 الفواتير وحالات المعمل وطباعة الـ PDF")
    cursor.execute("SELECT id, doctor_name, patient_name, case_type, price FROM cases ORDER BY id DESC")
    all_cases_data = cursor.fetchall()
    if all_cases_data:
        unique_docs_filter = ["الكل"] + list_docs
        selected_filter_doc = st.selectbox("🔍 تصفية الحالات باسم طبيب محدد:", unique_docs_filter)
        for case in all_cases_data:
            c_id, c_doc, c_pat, c_type, c_price = case
            if selected_filter_doc != "الكل" and c_doc != selected_filter_doc:
                continue
            col_info, col_btn = st.columns([3, 1])
            with col_info:
