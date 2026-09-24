import streamlit as st
import pandas as pd
import sqlite3
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل والكمبيوتر
st.set_page_config(page_title="معمل الأسنان المحترف", layout="centered", page_icon="🦷")

# الاتصال بقاعدة البيانات بملف بكر ونظيف تماماً
conn = sqlite3.connect('dental_lab_final_system_2026.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء وتحديث الجداول المترابطة ببنية أساسية حرة
cursor.execute("CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, phone TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, general_price REAL DEFAULT 0.0)")
cursor.execute("CREATE TABLE IF NOT EXISTS doctor_prices (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, product_name TEXT, custom_price REAL, UNIQUE(doctor_name, product_name))")
cursor.execute("CREATE TABLE IF NOT EXISTS technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, specialty TEXT, default_commission REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL, tech_name TEXT, tech_commission REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_name TEXT, amount_paid REAL)")
conn.commit()

st.title("🦷 معمل الأسنان الذكي")
st.write("الإصدار الاحترافي المستقر الشامل - مبيعات وعمولات بالجنيه المصري")

# جلب قوائم البيانات لملء الخيارات المنسدلة تلقائياً بنصوص صريحة ومسطحة
cursor.execute("SELECT name FROM doctors")
list_docs = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name FROM products")
list_products = [r[0] for r in cursor.fetchall()]

cursor.execute("SELECT name FROM technicians")
list_techs_records = [r[0] for r in cursor.fetchall()]

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

# 1. شاشة إدارة الحالات
if choice == "cases":
    st.subheader("📋 تسجيل وتعديل حالات المعمل اليومية")
    st.markdown("### ➕ إضافة حالة جديدة")
    selected_doc = st.selectbox("اختر الطبيب", list_docs if list_docs else ["لا يوجد أطباء مسجلين"])
    patient = st.text_input("اسم المريض")
    selected_type = st.selectbox("نوع التركيبة", list_products if list_products else ["لا يوجد تركيبات"])
    selected_tech = st.selectbox("الفني المسؤول عن الحالة", list_techs_records if list_techs_records else ["لا يوجد فنيين"])
    
    if st.button("💾 حفظ وتثبيت الحالة بالمعمل"):
        if not list_docs or not list_products or not list_techs_records:
            st.error("⚠️ خطأ: لا يمكنك الحفظ قبل تهيئة الأطباء والتركيبات والفنيين أولاً!")
        elif patient:
            cursor.execute("SELECT custom_price FROM doctor_prices WHERE doctor_name=? AND product_name=?", (selected_doc, selected_type))
            price_match = cursor.fetchone()
            if price_match and price_match[0] is not None:
                final_price = float(price_match[0])
            else:
                cursor.execute("SELECT general_price FROM products WHERE name=?", (selected_type,))
                general_match = cursor.fetchone()
                final_price = float(general_match[0]) if general_match and general_match[0] is not None else 0.0
            
            cursor.execute("SELECT default_commission FROM technicians WHERE name=?", (selected_tech,))
            comm_match = cursor.fetchone()
            suggested_comm = float(comm_match[0]) if comm_match and comm_match[0] is not None else 0.0
            
            cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price, tech_name, tech_commission) VALUES (?, ?, ?, ?, ?, ?)",
                           (selected_doc, patient, selected_type, final_price, selected_tech, suggested_comm))
            conn.commit()
            st.success(f"✅ تم قيد الحالة بنجاح وبسعر: {final_price:,.2f} ج.م")
            st.rerun()
        else:
            st.error("يرجى كتابة اسم المريض")

# 2. شاشة دليل الأطباء
elif choice == "doctors":
    st.subheader("👨‍⚕️ إدارة دليل عيادات الأسنان والعملاء")
    new_doc = st.text_input("اسم الطبيب الجديد")
    phone_doc = st.text_input("رقم هاتف العيادة")
    if st.button("💾 إضافة الطبيب ونشره بالنظام"):
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

# 3. شاشة كتالوج الأسعار والخصومات
elif choice == "prices":
    st.subheader("⚙️ كتالوج الأسعار الكلية وتعديلات أسعار الأطباء")
    col_general, col_custom = st.columns(2)
    
    with col_general:
        st.markdown("### 💰 1. قائمة الأسعار الكلية (لكل الناس)")
        p_name = st.text_input("اسم التركيبة (مثال: زيركون)")
        p_price = st.number_input("السعر العام الكلي لكل الناس (ج.م)", min_value=0.0, step=50.0)
        if st.button("💾 حفظ في الكتالوج الكلي"):
            if p_name and p_price > 0:
                cursor.execute("INSERT OR REPLACE INTO products (name, general_price) VALUES (?, ?)", (p_name, p_price))
                conn.commit()
                st.success("✅ تم تحديث السعر العام!")
                st.rerun()
    
    with col_custom:
        st.markdown("### 🔄 2. تعديل السعر لطبيب معين (اختياري)")
        target_doc = st.selectbox("اختر الطبيب", list_docs if list_docs else ["لا يوجد أطباء"])
        target_prod = st.selectbox("اختر التركيبة", list_products if list_products else ["لا يوجد تركيبات"])
        custom_rate = st.number_input("السعر المعدل الخاص بهذا الطبيب (ج.م)", min_value=0.0, step=50.0)
        
        if st.button("💾 تطبيق السعر الخاص"):
            cursor.execute("INSERT OR REPLACE INTO doctor_prices (doctor_name, product_name, custom_price) VALUES (?, ?, ?)", (target_doc, target_prod, custom_rate))
            conn.commit()
            st.success("🎉 تم تخصيص السعر المخصص بنجاح!")
            st.rerun()

# 4. شاشة حسابات الفنيين الصافية والحرّة والمضمونة الظهور بنسبة 1000%
elif choice == "technicians":
    st.subheader("🧑‍🏭 إدارة الفنيين وتعديل موازنتهم")
    st.markdown("### ➕ تسجيل فني جديد")
    t_name_input = st.text_input("اسم الفني الجديد")
    t_spec_input = st.text_input("التخصص (مثال: بورسلين)")
    t_comm_input = st.number_input("قيمة العموله الافتراضية للفني لكل سن (ج.م)", min_value=0.0, step=10.0)
    
    if st.button("💾 تسجيل وحفظ الفني بالمعمل"):
        if t_name_input:
            try:
                cursor.execute("INSERT INTO technicians (name, specialty, default_commission) VALUES (?, ?, ?)", (t_name_input, t_spec_input, t_comm_input))
                conn.commit()
                st.success(f"🎉 تم حفظ بيانات الفني {t_name_input} بنجاح!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("⚠️ هذا الفني مسجل مسبقاً في الدفاتر!")
        else:
            st.error("⚠️ يرجى كتابة اسم الفني أولاً")

# 5. شاشة تسجيل المقبوضات
elif choice == "payments":
    st.subheader("💸 استلام وتعديل دفعات الأطباء النقدية")
    pay_doc = st.selectbox("اختر الطبيب المسدد", list_docs) if list_docs else st.text_input("اكتب اسم الطبيب المسدد يدوياً")
    amt = st.number_input("المبلغ المستلم نقداً أو تحويل (ج.م)", min_value=0.0, step=100.0)
    if st.button("💾 تسجيل السند وتحديث الخزنة"):
        if pay_doc and amt > 0:
            cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amt))
            conn.commit()
            st.success(f"✅ تم تسجيل دفعة بقيمة {amt:,.2f} ج.م للطبيب {pay_doc} بنجاح!")
            st.rerun()
        else:
            st.error("يرجى التأكد من كتابة اسم الطبيب وإدخال مبلغ أكبر من صفر.")

# 6. شاشة التقارير وتنزيل فواتير الـ PDF
elif choice == "reports":
    st.subheader("📊 الفواتير وحالات المعمل الشاملة وطباعة الـ PDF")
    cursor.execute("SELECT id, doctor_name, patient_name, case_type, price FROM cases ORDER BY id DESC")
    all_cases_data = cursor.fetchall()
    if all_cases_data:
        unique_docs_filter = ["الكل"] + list_docs
        selected_filter_doc = st.selectbox("🔍 تصفية الحالات باسم طبيب محدد:", unique_docs_filter)
        for case in all_cases_data:
            c_id, c_doc, c_pat, c_type, c_price = case
