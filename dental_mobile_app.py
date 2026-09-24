import streamlit as st
import pandas as pd
import sqlite3
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل
st.set_page_config(page_title="معمل الأسنان المحترف", layout="centered", page_icon="🦷")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('dental_lab_advanced_mobile.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء وتحديث الجداول المترابطة
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT
    )''')
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

# الترقية التلقائية لحساب المدير الأول
cursor.execute("SELECT COUNT(*) FROM users")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', '1234', 'Admin')")
    conn.commit()

try:
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_name TEXT")
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_commission REAL DEFAULT 0.0")
    conn.commit()
except sqlite3.OperationalError:
    pass

# --- نظام تسجيل الدخول والصلاحيات ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = None

if not st.session_state['logged_in']:
    st.title("🔒 تسجيل الدخول - نظام المعمل")
    
    username_input = st.text_input("اسم المستخدم").strip()
    password_input = st.text_input("كلمة المرور", type="password").strip()
    
    if st.button("دخول للنظام"):
        cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username_input, password_input))
        user_match = cursor.fetchone()
        
        if user_match:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = user_match[0]
            st.session_state['username'] = username_input
            st.success("تم التحقق بنجاح! جاري تحميل النظام...")
            st.rerun()
        else:
            st.error("⚠️ اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.info("💡 حساب المدير الافتراضي الأول للدخول: اسم المستخدم: admin | الباسورد: 1234")
    st.stop()

# زر تسجيل الخروج والبيانات الجانبية
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = None
    st.rerun()

st.sidebar.markdown(f"**👤 المستخدم:** {st.session_state['username']}")
st.sidebar.markdown(f"**🛡️ الصلاحية:** {st.session_state['user_role']}")

st.title("🦷 نظام معمل الأسنان الذكي")

# جلب قوائم البيانات المشتركة للفورمات
cursor.execute("SELECT name FROM doctors")
list_docs = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name, price FROM products")
dict_products = {r[0]: r[1] for r in cursor.fetchall()}

cursor.execute("SELECT name, default_commission FROM technicians")
dict_techs = {r[0]: r[1] for r in cursor.fetchall()}

# --- تقسيم الصلاحيات والشاشات بناءً على صلاحية المستخدم المسجل ---
role = st.session_state['user_role']

if role in ["Admin", "Accountant"]:
    # حساب وعرض الماليات للمدير والمحاسب فقط
    total_sales, total_paid, total_tech_commissions = 0.0, 0.0, 0.0
    try:
        cursor.execute("SELECT SUM(price) FROM cases")
        res_sales = cursor.fetchone()
        total_sales = float(res_sales[0]) if res_sales[0] else 0.0

        cursor.execute("SELECT SUM(amount_paid) FROM payments")
        res_paid = cursor.fetchone()
        total_paid = float(res_paid[0]) if res_paid[0] else 0.0

        cursor.execute("SELECT SUM(tech_commission) FROM cases")
        res_tech = cursor.fetchone()
        total_tech_commissions = float(res_tech[0]) if res_tech[0] else 0.0
    except Exception:
        pass
    
    remaining_debts = total_sales - total_paid

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f} ج.م")
    col2.metric("💳 ديون الأطباء", f"{remaining_debts:,.2f} ج.م")
    col3.metric("🛠️ عمولات الفنيين", f"{total_tech_commissions:,.2f} ج.م")
    st.markdown("---")

    # بناء التبويبات حسب نوع الصلاحية
    tabs_list = ["📋 الحالات", "👨‍⚕️ الأطباء", "🧑‍🏭 الفنيين", "⚙️ الأسعار", "💸 المقبوضات", "📊 التقارير والفواتير"]
    if role == "Admin":
        tabs_list.append("🔐 إدارة المستخدمين")
        
    tabs = st.tabs(tabs_list)
    
    # تبويب الحالات
    with tabs[0]:
        st.subheader("تسجيل حالة جديدة وتحديد الفني")
        if not list_docs or not dict_products or not dict_techs:
            st.warning("⚠️ يرجى التأكد من تهيئة الأطباء، التركيبات، والفنيين أولاً من التبويبات الخاصة بهم.")
        else:
            with st.form("case_form_admin", clear_on_submit=True):
                selected_doc = st.selectbox("اختر الطبيب", list_docs)
                patient = st.text_input("اسم المريض")
                selected_type = st.selectbox("نوع التركيبة", list(dict_products.keys()))
                selected_tech = st.selectbox("الفني المسؤول عن الحالة", list(dict_techs.keys()))
                
                suggested_price = dict_products[selected_type]
                suggested_comm = dict_techs[selected_tech]
                st.info(f"💵 السعر الافتراضي: {suggested_price:,.2f} ج.م | 🛠️ عمولة الفني: {suggested_comm:,.2f} ج.م")
                
                final_price = st.number_input("تأكيد السعر النهائي (ج.م)", min_value=0.0, value=suggested_price)
                final_comm = st.number_input("تأكيد عمولة الفني (ج.م)", min_value=0.0, value=suggested_comm)
                
                if st.form_submit_button("حفظ وتثبيت الحالة"):
                    if patient:
                        cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                                       (selected_doc, patient, selected_type, final_price, selected_tech, final_comm))
                        conn.commit()
                        st.success("✅ تم حفظ وفحص الطلب ماليًا بنجاح!")
                        st.rerun()

    # تبويب الأطباء
    with tabs[1]:
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

    # تبويب الفنيين
    with tabs[2]:
        st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")
        with st.form("tech_form", clear_on_submit=True):
            t_name = st.text_input("اسم الفني الجديد")
            t_spec = st.text_input("التخصص")
            t_comm = st.number_input("قيمة العموله الافتراضية لكل سن (ج.م)", min_value=0.0, step=10.0)
            if st.form_submit_button("تسجيل الفني"):
                if t_name:
                    try:
                        cursor.execute("INSERT INTO technicians (name, specialty, default_commission) VALUES (?, ?, ?)", (t_name, t_spec, t_comm))
                        conn.commit()
                        st.success("🎉 تم تسجيل الفني بنجاح!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("هذا الفني مسجل مسبقاً!")
        df_tech_report = pd.read_sql_query('''
            SELECT tech_name as [اسم الفني], COUNT(id) as [عدد الحالات], SUM(tech_commission) as [إجمالي المستحقات (ج.م)] 
            FROM cases WHERE tech_name IS NOT NULL GROUP BY tech_name
        ''', conn)
        st.dataframe(df_tech_report, use_container_width=True)

    # تبويب الأسعار
    with tabs[3]:
        st.subheader("⚙️ قائمة أسعار خدمات المعمل")
        if role == "Admin":
            with st.form("product_form", clear_on_submit=True):
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
        else:
            st.warning("🔒 تصفح فقط: تعديل الكتالوج والأسعار متاح فقط لصلاحية مدير المعمل (Admin)."
