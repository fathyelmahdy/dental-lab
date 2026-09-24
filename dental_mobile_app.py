import streamlit as st
import pandas as pd
import sqlite3
import io

# إعداد الصفحة لتناسب شاشة الآيفون والموبايل
st.set_page_config(page_title="معمل الأسنان المحترف", layout="centered", page_icon="🦷")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('dental_lab_advanced_mobile.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول الاحترافية المترابطة
cursor.execute('''
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, phone TEXT
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, price REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, patient_name TEXT, case_type TEXT, price REAL
    )''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT, amount_paid REAL
    )''')
conn.commit()

st.title("🦷 نظام معمل الأسنان المتكامل")
st.write("إصدار الموبايل والآيفون الاحترافي")

# حساب الإحصائيات المالية العامة
cursor.execute("SELECT SUM(price) FROM cases")
row_sales = cursor.fetchone()
total_sales = float(row_sales[0]) if row_sales and row_sales[0] is not None else 0.0

cursor.execute("SELECT SUM(amount_paid) FROM payments")
row_paid = cursor.fetchone()
total_paid = float(row_paid[0]) if row_paid and row_paid[0] is not None else 0.0

remaining = total_sales - total_paid

# عرض الماليّات بأعلى شاشة الموبايل
col1, col2 = st.columns(2)
col1.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f}")
col2.metric("💳 ديون الأطباء المعلقة", f"{remaining:,.2f}")

st.markdown("---")

# تصميم الأيقونات والتبويبات العصرية
tab_cases, tab_doctors, tab_products, tab_payments, tab_reports = st.tabs([
    "📋 الحالات", "👨‍⚕️ الأطباء", "⚙️ التركيبات والأسعار", "💸 المقبوضات", "📊 التقارير"
])

# 1. تبويب إدارة الحالات (الطلبات)
with tab_cases:
    st.subheader("تسجيل حالة جديدة بالمعمل")
    
    # جلب قائمة الأطباء والتركيبات المسجلة مسبقاً
    cursor.execute("SELECT name FROM doctors")
    list_docs = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("SELECT name, price FROM products")
    dict_products = {r[0]: r[1] for r in cursor.fetchall()}
    
    if not list_docs:
        st.warning("⚠️ يرجى إضافة طبيب واحد على الأقل من تبويب 'الأطباء' أولاً.")
    elif not dict_products:
        st.warning("⚠️ يرجى إضافة أنواع التركيبات وأسعارها من تبويب 'التركيبات' أولاً.")
    else:
        with st.form("case_form_new", clear_on_submit=True):
            selected_doc = st.selectbox("اختر الطبيب (العميل)", list_docs)
            patient = st.text_input("اسم المريض")
            selected_type = st.selectbox("نوع التركيبة", list(dict_products.keys()))
            
            # عرض السعر التلقائي المأخوذ من الكتالوج
            suggested_price = dict_products[selected_type]
            st.info(f"💵 السعر التلقائي المسجل لهذه التركيبة: {suggested_price:,.2f}")
            
            # إمكانية تعديل السعر لحالة معينة لو لزم الأمر (خصم أو زيادة لطبيب محدد)
            final_price = st.number_input("تأكيد السعر النهائي للحالة", min_value=0.0, value=suggested_price)
            
            if st.form_submit_button("حفظ الحالة وتثبيتها ماليًا"):
                if patient:
                    cursor.execute("INSERT INTO cases (doctor_name, patient_name, case_type, price) VALUES (?, ?, ?, ?)",
                                   (selected_doc, patient, selected_type, final_price))
                    conn.commit()
                    st.success(f"✅ تم قيد الفاتورة للطبيب {selected_doc} بنجاح!")
                    st.rerun()
                else:
                    st.error("يرجى كتابة اسم المريض")

# 2. تبويب إدارة العملاء (الأطباء)
with tab_doctors:
    st.subheader("👨‍⚕️ دليل أطباء وعيادات الأسنان")
    with st.form("doc_form", clear_on_submit=True):
        new_doc = st.text_input("اسم الطبيب / العيادة الجديد")
        phone_doc = st.text_input("رقم الهاتف للعيادة")
        if st.form_submit_button("إضافة الطبيب إلى النظام"):
            if new_doc:
                try:
                    cursor.execute("INSERT INTO doctors (name, phone) VALUES (?, ?)", (new_doc, phone_doc))
                    conn.commit()
                    st.success("🎉 تم تسجيل الطبيب بنجاح في قاعدة البيانات!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الطبيب مسجل مسبقاً!")

    # عرض جدول الأطباء الحاليين
    df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)
    st.dataframe(df_docs, use_container_width=True)

# 3. تبويب كتالوج التركيبات والأسعار
with tab_products:
    st.subheader("⚙️ قائمة أسعار خامات وتركيبات المعمل")
    with st.form("product_form", clear_on_submit=True):
        p_name = st.text_input("اسم التركيبة (مثال: زيركون ألماني، إيماكس قشور)")
        p_price = st.number_input("السعر الافتراضي للسن الواحد", min_value=0.0, step=50.0)
        if st.form_submit_button("حفظ وإضافة للكتالوج"):
            if p_name and p_price > 0:
                try:
                    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (p_name, p_price))
                    conn.commit()
                    st.success("✅ تم تحديث قائمة أسعار المعمل الافتراضية!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذه التركيبة مضافة بالفعل!")

    df_prods = pd.read_sql_query("SELECT name as [نوع التركيبة], price as [السعر الافتراضي] FROM products", conn)
    st.dataframe(df_prods, use_container_width=True)

# 4. تبويب تسجيل المقبوضات النقدية
with tab_payments:
    st.subheader("💸 استلام دفعات نقدية من الأطباء")
    if not list_docs:
        st.warning("يرجى إضافة أطباء أولاً لتسجيل المقبوضات.")
    else:
        with st.form("pay_form_new", clear_on_submit=True):
            pay_doc = st.selectbox("الطبيب المسدد", list_docs)
            amt = st.number_input("المبلغ المستلم كاش أو تحويل", min_value=0.0, step=100.0)
            if st.form_submit_button("تسجيل سند القبض"):
                if amt > 0:
                    cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amt))
                    conn.commit()
                    st.success("✅ تم قيد المبلغ وتحديث كشف حساب الطبيب!")
                    st.rerun()

# 5. تبويب كشوف الحسابات وتصدير الإكسيل
with tab_reports:
    st.subheader("📊 كشوف الحسابات المفصلة للمعمل")
    df_all_cases = pd.read_sql_query("SELECT id as [كود], doctor_name as [الطبيب], patient_name as [المريض], case_type as [النوع], price as [الحساب] FROM cases ORDER BY id DESC", conn)
    
    if not df_all_cases.empty:
        st.dataframe(df_all_cases, use_container_width=True)
        
        # تحويل التقارير لملف إكسيل قابل للتحميل على الآيفون
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df_all_cases.to_excel(w, index=False, sheet_name='حسابات المعمل اليومية')
        st.download_button(label="📥 تحميل سجل الحالات الشامل بصيغة Excel", data=out.getvalue(), file_name='dental_lab_full_report.xlsx', mime='application/vnd.ms-excel')
    else:
        st.info("لا توجد فواتير أو حالات مسجلة حتى الآن.")

conn.close()
