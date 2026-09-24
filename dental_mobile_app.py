import streamlit as st
import pandas as pd
import sqlite3
import io

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل
st.set_page_config(page_title="معمل الأسنان المحترف", layout="centered", page_icon="🦷")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('dental_lab_advanced_mobile.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء وتحديث الجداول المترابطة
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
        doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, amount_paid REAL
    )''')
conn.commit()

# ترقية تلقائية للجدول القديم لمنع خطأ الـ OperationalError
try:
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_name TEXT")
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_commission REAL DEFAULT 0.0")
    conn.commit()
except sqlite3.OperationalError:
    # الأعمدة موجودة بالفعل، لا تفعل شيئاً
    pass

st.title("🦷 نظام معمل الأسنان المتكامل")
st.write("إصدار المليّات وعمولات الفنيين")

# حساب الإحصائيات المالية العامة للمعمل بشكل آمن
total_sales = 0.0
total_paid = 0.0
total_tech_commissions = 0.0

try:
    cursor.execute("SELECT SUM(price) FROM cases")
    row_sales = cursor.fetchone()
    if row_sales and row_sales[0] is not None:
        total_sales = float(row_sales[0])

    cursor.execute("SELECT SUM(amount_paid) FROM payments")
    row_paid = cursor.fetchone()
    if row_paid and row_paid[0] is not None:
        total_paid = float(row_paid[0])

    cursor.execute("SELECT SUM(tech_commission) FROM cases")
    row_tech = cursor.fetchone()
    if row_tech and row_tech[0] is not None:
        total_tech_commissions = float(row_tech[0])
except Exception:
    pass

remaining_debts = total_sales - total_paid

# عرض ماليّات المعمل بأعلى شاشة الموبايل
col1, col2, col3 = st.columns(3)
col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f}")
col2.metric("💳 ديون الأطباء", f"{remaining_debts:,.2f}")
col3.metric("🛠️ عمولات الفنيين", f"{total_tech_commissions:,.2f}")

st.markdown("---")

# تصميم الأيقونات والتبويبات العصرية الشاملة
tab_cases, tab_doctors, tab_technicians, tab_products, tab_payments, tab_reports = st.tabs([
    "📋 الحالات", "👨‍⚕️ الأطباء", "🧑‍🏭 الفنيين", "⚙️ الأسعار", "💸 المقبوضات", "📊 التقارير"
])

# جلب قوائم البيانات المشتركة
cursor.execute("SELECT name FROM doctors")
list_docs = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name, price FROM products")
dict_products = {r[0]: r[1] for r in cursor.fetchall()}

cursor.execute("SELECT name, default_commission FROM technicians")
dict_techs = {r[0]: r[1] for r in cursor.fetchall()}

# 1. تبويب إدارة الحالات (الطلبات)
with tab_cases:
    st.subheader("تسجيل حالة جديدة وتحديد الفني")
    if not list_docs:
        st.warning("⚠️ يرجى إضافة طبيب أولاً من تبويب 'الأطباء'.")
    elif not dict_products:
        st.warning("⚠️ يرجى إضافة أنواع تركيبات وأسعارها من تبويب 'الأسعار'.")
    elif not dict_techs:
        st.warning("⚠️ يرجى إضافة فني واحد على الأقل من تبويب 'الفنيين'.")
    else:
        with st.form("case_form_new_v2", clear_on_submit=True):
            selected_doc = st.selectbox("اختر الطبيب", list_docs)
            patient = st.text_input("اسم المريض")
            selected_type = st.selectbox("نوع التركيبة", list(dict_products.keys()))
            selected_tech = st.selectbox("الفني المسؤول عن الحالة", list(dict_techs.keys()))
            
            # حسابات تلقائية
            suggested_price = dict_products[selected_type]
            suggested_comm = dict_techs[selected_tech]
            
            st.info(f"💵 السعر التلقائي: {suggested_price:,.2f} | 🛠️ عمولة الفني الافتراضية: {suggested_comm:,.2f}")
            
            final_price = st.number_input("تأكيد السعر النهائي للحالة", min_value=0.0, value=suggested_price)
            final_comm = st.number_input("تأكيد عمولة الفني لهذه الحالة", min_value=0.0, value=suggested_comm)
            
            if st.form_submit_button("حفظ الحالة وتثبيتها ماليًا"):
                if patient:
                    cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                                   (selected_doc, patient, selected_type, final_price, selected_tech, final_comm))
                    conn.commit()
                    st.success(f"✅ تم حفظ الحالة وإدراج عمولة الفني {selected_tech}!")
                    st.rerun()
                else:
                    st.error("يرجى كتابة اسم المريض")

# 2. تبويب إدارة العملاء (الأطباء)
with tab_doctors:
    st.subheader("👨‍⚕️ دليل عيادات الأسنان")
    with st.form("doc_form", clear_on_submit=True):
        new_doc = st.text_input("اسم الطبيب الجديد")
        phone_doc = st.text_input("رقم هاتف العيادة")
        if st.form_submit_button("إضافة الطبيب"):
            if new_doc:
                try:
                    cursor.execute("INSERT INTO doctors (name, phone) VALUES (?, ?)", (new_doc, phone_doc))
                    conn.commit()
                    st.success("🎉 تم تسجيل الطبيب بنجاح!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الطبيب مسجل مسبقاً!")
    df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)
    st.dataframe(df_docs, use_container_width=True)

# 3. تبويب إدارة الفنيين والعمولات
with tab_technicians:
    st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")
    with st.form("tech_form", clear_on_submit=True):
        t_name = st.text_input("اسم الفني الجديد")
        t_spec = st.text_input("التخصص (مثال: زيركون، بورسلين)")
        t_comm = st.number_input("قيمة العموله الافتراضية لكل سن (ريال/جنيه)", min_value=0.0, step=10.0)
        if st.form_submit_button("تسجيل الفني"):
            if t_name:
                try:
                    cursor.execute("INSERT INTO technicians (name, specialty, default_commission) VALUES (?, ?, ?)", (t_name, t_spec, t_comm))
                    conn.commit()
                    st.success(f"🎉 تم تسجيل الفني {t_name} في المعمل!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الفني مسجل مسبقاً!")
                    
    # عرض إجمالي مستحقات كل فني بناء على إنتاجه
    st.markdown("### 📊 مستحقات الفنيين الحالية:")
    df_tech_report = pd.read_sql_query('''
        SELECT tech_name as [اسم الفني], 
               COUNT(id) as [عدد الحالات المنجزة], 
               SUM(tech_commission) as [إجمالي المستحقات] 
        FROM cases WHERE tech_name IS NOT NULL GROUP BY tech_name
    ''', conn)
    st.dataframe(df_tech_report, use_container_width=True)

# 4. تبويب كتالوج التركيبات والأسعار
with tab_products:
    st.subheader("⚙️ قائمة أسعار خدمات المعمل")
    with st.form("product_form", clear_on_submit=True):
        p_name = st.text_input("اسم التركيبة")
        p_price = st.number_input("السعر الافتراضي للسن", min_value=0.0, step=50.0)
        if st.form_submit_button("حفظ للكتالوج"):
            if p_name and p_price > 0:
                try:
                    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (p_name, p_price))
                    conn.commit()
                    st.success("✅ تم التحديث الافتراضي!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("مضافة بالفعل!")
    df_prods = pd.read_sql_query("SELECT name as [نوع التركيبة], price as [السعر الافتراضي] FROM products", conn)
    st.dataframe(df_prods, use_container_width=True)

# 5. تبويب تسجيل المقبوضات النقدية
with tab_payments:
    st.subheader("💸 استلام دفعات نقدية من الأطباء")
    if list_docs:
        with st.form("pay_form_new", clear_on_submit=True):
            pay_doc = st.selectbox("الطبيب المسدد", list_docs)
            amt = st.number_input("المبلغ المستلم", min_value=0.0, step=100.0)
            if st.form_submit_button("تسجيل السند"):
                if amt > 0:
                    cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amt))
                    conn.commit()
                    st.success("✅ تم تحديث كشف حساب الطبيب وموازنة الخزنة!")
                    st.rerun()

# 6. تبويب التقارير وتنزيل ملفات الإكسيل
with tab_reports:
    st.subheader("📊 الفواتير وحالات المعمل الشاملة")
    df_all_cases = pd.read_sql_query('''
        SELECT id as [كود], doctor_name as [الطبيب], patient_name as [المريض], 
               case_type as [التركيبة], price as [الحساب التابع للعيادة], 
               tech_name as [الفني المسؤول], tech_commission as [عمولة الفني] 
        FROM cases ORDER BY id DESC
    ''', conn)
    
    if not df_all_cases.empty:
        st.dataframe(df_all_cases, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df_all_cases.to_excel(w, index=False, sheet_name='تقرير المعمل العام')
        st.download_button(label="📥 تحميل التقرير المالي الاحترافي بكافة التفاصيل لـ Excel", data=out.getvalue(), file_name='dental_lab_comprehensive_report.xlsx', mime='application/vnd.ms-excel')
    else:
        st.info("لا توجد فواتير أو حالات مسجلة حتى الآن.")

conn.close()
