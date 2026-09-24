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

# إنشاء وتحديث الجداول المترابطة لتشمل نظام الأسعار المخصصة للأطباء
cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, phone TEXT
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE
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

st.title("🦷 نظام معمل الأسنان الذكي")
st.write("إصدار الأسعار المخصصة لكل طبيب بالجنيه المصري")

# جلب قوائم البيانات لملء الخيارات المنسدلة
cursor.execute("SELECT name FROM doctors")
list_docs = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name FROM products")
list_products = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name, default_commission FROM technicians")
dict_techs = {r[0]: r[1] for r in cursor.fetchall()}

# --- حساب وعرض الماليّات العامة للمعمل بالأعلى ---
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

# تصميم القائمة العريضة كخيارات راديو واضحة للتنقل الفوري
menu_options = ["cases", "doctors", "prices", "technicians", "payments", "reports"]

choice_display = {
    "cases": "📋 إدارة الحالات",
    "doctors": "👨‍⚕️ دليل الأطباء",
    "prices": "⚙️ أسعار التركيبات المخصصة",
    "technicians": "🧑‍🏭 حسابات الفنيين",
    "payments": "💸 تسجيل المقبوضات",
    "reports": "📊 التقارير والفواتير"
}

choice = st.radio("⬇️ اختر الشاشة المطلوبة لعرض خياراتها بالكامل:", menu_options, format_func=lambda x: choice_display[x], horizontal=True)
st.markdown("---")

# 1. شاشة إدارة الحالات (تسجيل الحالات السريع)
if choice == "cases":
    st.subheader("تسجيل حالة جديدة (يتم احتساب السعر الخاص بالطبيب تلقائياً)")
    with st.form("case_form_free", clear_on_submit=True):
        selected_doc = st.selectbox("اختر الطبيب", list_docs if list_docs else ["لا يوجد أطباء مسجلين - اضغط على دليل الأطباء بالأعلى لإضافتهم"])
        patient = st.text_input("اسم المريض")
        selected_type = st.selectbox("نوع التركيبة", list_products if list_products else ["لا يوجد تركيبات - اضغط على أسعار التركيبات المخصصة بالأعلى لإضافتها"])
        selected_tech = st.selectbox("الفني المسؤول عن الحالة", list(dict_techs.keys()) if dict_techs else ["لا يوجد فنيين - اضغط على حسابات الفنيين بالأعلى لإضافتهم"])
        
        if st.form_submit_button("حفظ وتثبيت الحالة"):
            if not list_docs or not list_products or not dict_techs:
                st.error("⚠️ خطأ: لا يمكنك الحفظ قبل تهيئة الأطباء والتركيبات والفنيين أولاً!")
            elif patient:
                # جلب السعر المخصص لهذا الطبيب بالتحديد لهذه التركيبة
                cursor.execute("SELECT custom_price FROM doctor_prices WHERE doctor_name=? AND product_name=?", (selected_doc, selected_type))
                price_match = cursor.fetchone()
                
                if price_match:
                    final_price = float(price_match[0])
                    suggested_comm = dict_techs.get(selected_tech, 0.0)
                    
                    cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                                   (selected_doc, patient, selected_type, final_price, selected_tech, suggested_comm))
                    conn.commit()
                    st.success(f"✅ تم قيد الحالة بنجاح وبسعر مخصص للطبيب: {final_price:,.2f} ج.م")
                    st.rerun()
                else:
                    st.error(f"⚠️ خطأ: لم تقم بتحديد سعر لتركيبة ({selected_type}) لهذا الطبيب ({selected_doc}) بعد! برجاء الذهاب لتبويب 'أسعار التركيبات المخصصة' وتحديد سعره أولاً.")
            else:
                st.error("يرجى كتابة اسم المريض")

# 2. شاشة دليل الأطباء
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
                    st.success("🎉 تم تسجيل الطبيب بنجاح! اذهب الآن لتبويب الأسعار المخصصة لتحديد موازنتك معه.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الطبيب مسجل مسبقاً!")
            else:
                st.error("برجاء إدخال اسم الطبيب أولاً!")
    df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)
    st.dataframe(df_docs, use_container_width=True)

# 3. شاشة إدارة أسعار التركيبات وقوائم أسعار الأطباء الخاصة
elif choice == "prices":
    st.subheader("⚙️ إدارة أنواع التركيبات وتعيين أسعار خاصة لكل طبيب")
    
    col_prod, col_rate = st.columns(2)
    with col_prod:
        st.markdown("### 1. إضافة نوع تركيبة جديد للمعمل")
        with st.form("add_product_form", clear_on_submit=True):
            p_name = st.text_input("اسم التركيبة (مثال: زيركون ألماني، بورسلين)")
            if st.form_submit_button("إضافة الصنف للكتالوج"):
                if p_name:
                    try:
                        cursor.execute("INSERT INTO products (name) VALUES (?)", (p_name,))
                        conn.commit()
                        st.success("✅ تم إضافة نوع التركيبة بنجاح!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("هذه التركيبة مضافة بالفعل!")
    
    with col_rate:
        st.markdown("### 2. تخصيص سعر طبيب معين لتركيبة معينة")
        if not list_docs or not list_products:
            st.warning("يرجى إضافة طبيب ونوع تركيبة أولاً لتتمكن من تخصيص الأسعار.")
        else:
            with st.form("assign_price_form", clear_on_submit=True):
                target_doc = st.selectbox("اختر الطبيب", list_docs)
                target_prod = st.selectbox("اختر التركيبة", list_products)
                custom_rate = st.number_input("السعر الخاص المتفق عليه لهذا الطبيب (ج.م)", min_value=0.0, step=50.0)
                if st.form_submit_button("حفظ السعر الخاص بالطبيب"):
                    if custom_rate > 0:
                        cursor.execute("INSERT OR REPLACE INTO doctor_prices (doctor_name, product_name, custom_price) VALUES (?, ?, ?)",
                                       (target_doc, target_prod, custom_rate))
                        conn.commit()
                        st.success(f"🎉 تم قيد سعر {custom_rate:,.2f} ج.م لتركيبة {target_prod} للطبيب {target_doc}!")
                        st.rerun()

    st.markdown("### 📋 جدول الأسعار المخصصة المسجلة حالياً لكل طبيب:")
    df_custom_rates = pd.read_sql_query("SELECT doctor_name as [اسم الطبيب], product_name as [نوع التركيبة], custom_price as [السعر الخاص (ج.م)] FROM doctor_prices", conn)
    st.dataframe(df_custom_rates, use_container_width=True)

# 4. شاشة حسابات الفنيين
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
