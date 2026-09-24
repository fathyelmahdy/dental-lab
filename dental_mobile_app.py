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

# إنشاء وتحديث الجداول المترابطة
cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, phone TEXT
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, general_price REAL DEFAULT 0.0
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctor_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, product_name TEXT, custom_price REAL,
        UNIQUE(doctor_name, product_name)
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

# ترقية تلقائية وذكية لقاعدة البيانات لمنع أخطاء الـ OperationalError
try:
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_name TEXT")
    cursor.execute("ALTER TABLE cases ADD COLUMN tech_commission REAL DEFAULT 0.0")
    conn.commit()
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE products ADD COLUMN general_price REAL DEFAULT 0.0")
    conn.commit()
except sqlite3.OperationalError:
    pass

st.title("🦷 معمل الأسنان الذكي")
st.write("الإصدار المفتوح الشامل - مبيعات وعمولات وفواتير بالجنيه المصري")

# جلب قوائم البيانات لملء الخيارات المنسدلة تلقائياً
cursor.execute("SELECT name FROM doctors")
list_docs = [r for r in cursor.fetchall()]

cursor.execute("SELECT name FROM products")
list_products = [r for r in cursor.fetchall()]

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

menu_options = ["cases", "doctors", "prices", "technicians", "payments", "reports"]

choice_display = {
    "cases": "📋 إدارة الحالات",
    "doctors": "👨‍⚕️ دليل الأطباء",
    "prices": "⚙️ كتالوج الأسعار والخصومات",
    "technicians": "🧑‍🏭 حسابات الفنيين",
    "payments": "💸 تسجيل المقبوضات",
    "reports": "📊 التقارير والفواتير"
}

choice = st.radio("⬇️ اختر الشاشة المطلوبة لعرض خياراتها بالكامل:", menu_options, format_func=lambda x: choice_display[x], horizontal=True)
st.markdown("---")

if choice == "cases":
    st.subheader("تسجيل حالة جديدة بالمعمل")
    with st.form("case_form_free", clear_on_submit=True):
        selected_doc = st.selectbox("اختر الطبيب", list_docs if list_docs else ["لا يوجد أطباء مسجلين - اضغط على دليل الأطباء بالأعلى لإضافتهم"])
        patient = st.text_input("اسم المريض")
        selected_type = st.selectbox("نوع التركيبة", list_products if list_products else ["لا يوجد تركيبات - اضغط على كتالوج الأسعار بالأعلى لإضافتها"])
        selected_tech = st.selectbox("الفني المسؤول عن الحالة", list(dict_techs.keys()) if dict_techs else ["لا يوجد فنيين - اضغط على حسابات الفنيين بالأعلى لإضافتهم"])
        
        if st.form_submit_button("حفظ وتثبيت الحالة"):
            if not list_docs or not list_products or not dict_techs:
                st.error("⚠️ خطأ: لا يمكنك الحفظ قبل تهيئة الأطباء والتركيبات والفنيين أولاً!")
            elif patient:
                cursor.execute("SELECT custom_price FROM doctor_prices WHERE doctor_name=? AND product_name=?", (selected_doc, selected_type))
                price_match = cursor.fetchone()
                
                if price_match and price_match is not None:
                    final_price = float(price_match)
                else:
                    cursor.execute("SELECT general_price FROM products WHERE name=?", (selected_type,))
                    general_match = cursor.fetchone()
                    final_price = float(general_match) if general_match and general_match is not None else 0.0
                
                suggested_comm = dict_techs.get(selected_tech, 0.0)
                
                cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                               (selected_doc, patient, selected_type, final_price, selected_tech, suggested_comm))
                conn.commit()
                st.success(f"✅ تم قيد الحالة بنجاح وبسعر: {final_price:,.2f} ج.م")
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

elif choice == "prices":
    st.subheader("⚙️ كتالوج الأسعار الكلية وتعديلات أسعار الأطباء")
    col_general, col_custom = st.columns(2)
    
    with col_general:
        st.markdown("### 💰 1. قائمة الأسعار الكلية (لكل الناس)")
        with st.form("general_price_form", clear_on_submit=True):
            p_name = st.text_input("اسم التركيبة (مثال: زيركون)")
            p_price = st.number_input("السعر العام الكلي لكل الناس (ج.م)", min_value=0.0, step=50.0)
            if st.form_submit_button("حفظ في الكتالوج الكلي"):
                if p_name and p_price > 0:
                    try:
                        cursor.execute("INSERT OR REPLACE INTO products (name, general_price) VALUES (?, ?)", (p_name, p_price))
                        conn.commit()
                        st.success("✅ تم حفظ التركيبة بالسعر العام!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("خطأ غير متوقع!")
        df_general = pd.read_sql_query("SELECT name as [نوع التركيبة], general_price as [السعر الكلي العام (ج.م)] FROM products", conn)
        st.dataframe(df_general, use_container_width=True)
    
    with col_custom:
        st.markdown("### 🔄 2. تعديل السعر لطبيب معين (اختياري)")
        if not list_docs or not list_products:
            st.warning("يرجى إضافة طبيب وتركيبة أولاً في الكتالوج الكلي لتتمكن من التعديل.")
        else:
            with st.form("assign_price_form", clear_on_submit=True):
                target_doc = st.selectbox("اختر الطبيب", list_docs)
                target_prod = st.selectbox("اختر التركيبة", list_products)
                custom_rate = st.number_input("السعر المعدل الخاص بهذا الطبيب (ج.م)", min_value=0.0, step=50.0)
                if st.form_submit_button("تطبيق السعر الخاص"):
                    if custom_rate > 0:
                        try:
                            cursor.execute("INSERT OR REPLACE INTO doctor_prices (doctor_name, product_name, custom_price) VALUES (?, ?, ?)",
                                           (target_doc, target_prod, custom_rate))
                            conn.commit()
                            st.success(f"🎉 تم تخصيص السعر المخصص بنجاح!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("خطأ في قيد السعر الخاص!")
        df_custom_rates = pd.read_sql_query("SELECT doctor_name as [الطبيب], product_name as [التركيبة], custom_price as [السعر المعدل (ج.م)] FROM doctor_prices", conn)
        st.dataframe(df_custom_rates, use_container_width=True)

elif choice == "technicians":
    st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")
    with st.form("tech_form_free", clear_on_submit=True):
        t_name = st.text_input("اسم الفني الجديد")
        t_spec = st.text_input("التخصص")
        t_comm = st.number_input("قيمة العموله الافتراضية لكل سن (ج.م)", min_value=0.0, step=10.0)
        
        # زر الحفظ يعمل الآن بكفاءة وبدون أي استدعاء معقد
