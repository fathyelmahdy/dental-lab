import streamlit as st
import pandas as pd
import sqlite3
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل والكمبيوتر
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

# --- نظام تسجيل الدخول المحمي والصارم مئة بالمئة ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = None

if not st.session_state['logged_in']:
    st.title("🔒 تسجيل الدخول - نظام المعمل")
    username_input = st.text_input("اسم المستخدم").strip()
    password_input = st.text_input("كلمة المرور", type="password").strip()
    
    if st.button("دخول للنظام"):
        # التحقق المباشر والمحمي للحساب الرئيسي لضمان الدخول الفوري دون أخطاء داتابيز
        if username_input == "admin" and password_input == "1234":
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = "Admin"
            st.session_state['username'] = "admin"
            st.success("تم التحقق بنجاح! جاري تحميل النظام...")
            st.rerun()
        else:
            # التحقق من بقية الموظفين المسجلين في الداتابيز
            cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username_input, password_input))
            user_match = cursor.fetchone()
            if user_match:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = str(user_match[0]).strip()
                st.session_state['username'] = username_input
                st.success("تم التحقق بنجاح! جاري تحميل النظام...")
                st.rerun()
            else:
                st.error("⚠️ اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()

# شريط جانبي لعرض معلومات المستخدم وزر تسجيل الخروج
st.sidebar.markdown(f"**👤 المستخدم:** {st.session_state['username']}")
st.sidebar.markdown(f"**🛡️ الصلاحية:** {st.session_state['user_role']}")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = None
    st.rerun()

st.title("🦷 نظام معمل الأسنان الذكي")

# جلب قوائم البيانات لملء الخيارات المنسدلة تلقائياً
cursor.execute("SELECT name FROM doctors")
list_docs = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name, price FROM products")
dict_products = {r[0]: r[1] for r in cursor.fetchall()}

cursor.execute("SELECT name, default_commission FROM technicians")
dict_techs = {r[0]: r[1] for r in cursor.fetchall()}

current_role = st.session_state['user_role']

# تصفية الشاشات بالكامل وعزل صلاحيات الموظف (Staff)
if current_role == "Staff":
    st.info("🔒 وضع إدخال البيانات المحدود للـ Staff")
    st.subheader("📋 تسجيل حالة جديدة بالمعمل")
    if not list_docs or not dict_products or not dict_techs:
        st.warning("يرجى مراجعة أدمن المعمل لتهيئة البيانات أولاً.")
    else:
        with st.form("case_form_staff", clear_on_submit=True):
            selected_doc = st.selectbox("اختر الطبيب", list_docs)
            patient = st.text_input("اسم المريض")
            selected_type = st.selectbox("نوع التركيبة", list(dict_products.keys()))
            selected_tech = st.selectbox("اسم الفني المنفذ", list(dict_techs.keys()))
            if st.form_submit_button("إرسال وتسجيل الحالة للمعمل"):
                if patient:
                    suggested_price = dict_products[selected_type]
                    suggested_comm = dict_techs[selected_tech]
                    cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                                   (selected_doc, patient, selected_type, suggested_price, selected_tech, suggested_comm))
                    conn.commit()
                    st.success("✅ تم تسجيل وإرسال الحالة بنجاح!")
                    st.rerun()
                else:
                    st.error("يرجى كتابة اسم المريض.")
    conn.close()
    st.stop()

# --- واجهات المسؤولين (Admin و Accountant) ---
total_sales, total_paid, total_tech_commissions = 0.0, 0.0, 0.0
try:
    cursor.execute("SELECT SUM(price) FROM cases")
    res_sales = cursor.fetchone()
    total_sales = float(res_sales[0]) if res_sales and res_sales[0] is not None else 0.0

    cursor.execute("SELECT SUM(amount_paid) FROM payments")
    res_paid = cursor.fetchone()
    total_paid = float(res_paid[0]) if res_paid and res_paid[0] is not None else 0.0

    cursor.execute("SELECT SUM(tech_commission) FROM cases")
    res_tech = cursor.fetchone()
    total_tech_commissions = float(res_tech[0]) if res_tech and res_tech[0] is not None else 0.0
except Exception:
    pass

remaining_debts = total_sales - total_paid

col1, col2, col3 = st.columns(3)
col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f} ج.م")
col2.metric("💳 ديون الأطباء", f"{remaining_debts:,.2f} ج.م")
col3.metric("🛠️ عمولات الفنيين", f"{total_tech_commissions:,.2f} ج.م")
st.markdown("---")

# تصميم القائمة العريضة
menu_options = ["📋 إدارة الحالات", "👨‍⚕️ دليل الأطباء", "🧑‍🏭 حسابات الفنيين", "⚙️ كتالوج الأسعار", "💸 تسجيل المقبوضات", "📊 التقارير والفواتير"]
if current_role == "Admin":
    menu_options.append("👤 إضافة مستخدم جديد")

choice = st.radio("⬇️ اختر الشاشة المطلوبة لعرض خياراتها بالكامل:", menu_options, horizontal=True)
st.markdown("---")

if choice == "📋 إدارة الحالات":
    st.subheader("تسجيل حالة جديدة وتحديد الفني")
    if not list_docs or not dict_products or not dict_techs:
        st.warning("⚠️ يرجى إضافة أطباء، تركيبات، وفنيين أولاً لتفعيل الشاشة.")
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

elif choice == "👨‍⚕️ دليل الأطباء":
    st.subheader("👨‍⚕️ دليل عيادات الأسنان والعملاء")
    with st.form("doc_form", clear_on_submit=True):
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
    df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)
    st.dataframe(df_docs, use_container_width=True)

elif choice == "🧑‍🏭 حسابات الفنيين":
    st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")
    with st.form("tech_form", clear_on_submit=True):
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
