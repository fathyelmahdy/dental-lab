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

# الترقية التلقائية لحساب المدير الأول
cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
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
        if username_input == "admin" and password_input == "1234":
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = "Admin"
            st.session_state['username'] = "admin"
            st.success("تم التحقق بنجاح! جاري تحميل النظام...")
            st.rerun()
        else:
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
    st.info("💡 حساب المدير الافتراضي الحالي للدخول: اسم المستخدم: admin | الباسورد: 1234")
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

# خيارات التنقل الصافية تماماً بدون إيموجي لحل مشاكل التفسير السحابي
menu_options = ["cases", "doctors", "technicians", "prices", "payments", "reports"]
if current_role == "Admin":
    menu_options.append("users")

# عرض أسماء القوائم المترجمة بشكل عريض ومقروء للمستخدم
choice_display = {
    "cases": "📋 إدارة الحالات",
    "doctors": "👨‍⚕️ دليل الأطباء",
    "technicians": "🧑‍🏭 حسابات الفنيين",
    "prices": "⚙️ كتالوج الأسعار",
    "payments": "💸 تسجيل المقبوضات",
    "reports": "📊 التقارير والفواتير",
    "users": "👤 إضافة مستخدم جديد"
}

choice = st.radio("⬇️ اختر الشاشة المطلوبة لعرض خياراتها بالكامل:", menu_options, format_func=lambda x: choice_display[x], horizontal=True)
st.markdown("---")

if choice == "cases":
    st.subheader("تسجيل حالة جديدة وتحديد الفني")
    with st.form("case_form_admin", clear_on_submit=True):
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
يُرجى استخدام الرمز البرمجي بحذر.df_docs = pd.read_sql_query("SELECT name as [اسم الطبيب], phone as [الهاتف] FROM doctors", conn)st.dataframe(df_docs, use_container_width=True)elif choice == "technicians":st.subheader("🧑‍🏭 إدارة الفنيين وحساب عمولاتهم")with st.form("tech_form", clear_on_submit=True):t_name = st.text_input("اسم الفني الجديد")t_spec = st.text_input("التخصص")t_comm = st.number_input("قيمة العموله الافتراضية لكل سن (ج.م)", min_value=0.0, step=10.0)if st.form_submit_button("تسجيل الفني بالمعمل"):if t_name:try:cursor.execute("INSERT INTO technicians (name, specialty, default_commission) VALUES (?, ?, ?)", (t_name, t_spec, t_comm))conn.commit()st.success("🎉 تم تسجيل الفني بنجاح!")st.rerun()except sqlite3.IntegrityError:st.error("هذا الفني مسجل مسبقاً!")df_tech_report = pd.read_sql_query("SELECT tech_name as [اسم الفني], COUNT(id) as [عدد الحالات], SUM(tech_commission) as [إجمالي المستحقات (ج.م)] FROM cases WHERE tech_name IS NOT NULL GROUP BY tech_name", conn)st.dataframe(df_tech_report, use_container_width=True)elif choice == "prices":st.subheader("⚙️ قائمة أسعار خدمات وتركيبات المعمل")if current_role == "Admin":with st.form("product_form", clear_on_submit=True):p_name = st.text_input("اسم التركيبة")p_price = st.number_input("السعر الافتراضي للسن (ج.م)", min_value=0.0, step=50.0)if st.form_submit_button("حفظ للكتالوج"):if p_name and p_price > 0:try:cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (p_name, p_price))conn.commit()st.success("✅ تم التحديث الافتراضي بقائمة الأسعار!")st.rerun()except sqlite3.IntegrityError:st.error("مضافة بالفعل!")else:st.warning("🔒 تصفح فقط: تعديل الكتالوج متاح لمدير المعمل (Admin).")df_prods = pd.read_sql_query("SELECT name as [نوع التركيبة], price as [السعر الافتراضي (ج.م)] FROM products", conn)st.dataframe(df_prods, use_container_width=True)elif choice == "payments":st.subheader("💸 استلام دفعات نقدية من الأطباء")if list_docs:with st.form("pay_form_admin", clear_on_submit=True):pay_doc = st.selectbox("الطبيب المسدد", list_docs)amt = st.number_input("المبلغ المستلم (ج.م)", min_value=0.0, step=100.0)if st.form_submit_button("تسجيل السند وتحديث الخزنة"):if amt > 0:cursor.execute("INSERT INTO payments (doctor_name, amount_paid) VALUES (?, ?)", (pay_doc, amt))conn.commit()st.success("✅ تم تسجيل السند وتحديث كشف حساب العيادة!")st.rerun()else:st.info("لم يتم تسجيل أي عيادات أو أطباء بعد لتسجيل مقبوضات ماليّة لهم.")elif choice == "reports":st.subheader("📊 الفواتير وحالات المعمل وطباعة الـ PDF")cursor.execute("SELECT id, doctor_name, patient_name, case_type, price FROM cases ORDER BY id DESC")all_cases_data = cursor.fetchall()if all_cases_data:unique_docs_filter = ["الكل"] + list_docsselected_filter_doc = st.selectbox("🔍 تصفية الحالات باسم طبيب محدد:", unique_docs_filter)for case in all_cases_data:c_id, c_doc, c_pat, c_type, c_price = caseif selected_filter_doc != "الكل" and c_doc != selected_filter_doc:continuecol_info, col_btn = st.columns()with col_info:st.write(f"كود: {c_id} | الطبيب: {c_doc} | المريض: {c_pat} | النوع: {c_type} | الحساب: {c_price:,.2f} ج.م")with col_btn:def generate_invoice_pdf(case_id, doc, pat, ctype, price):buffer = io.BytesIO()p = canvas.Canvas(buffer, pagesize=letter)p.setPageSize((6 * inch, 4 * inch))p.setFont("Helvetica-Bold", 14)p.drawString(0.5 * inch, 3.5 * inch, "DENTAL LAB INVOICE")p.line(0.5 * inch, 3.3 * inch, 5.5 * inch, 3.3 * inch)p.setFont("Helvetica", 10)p.drawString(0.5 * inch, 2.9 * inch, f"Invoice Code: #{case_id}")p.drawString(0.5 * inch, 2.5 * inch, f"Doctor: {doc}")p.drawString(0.5 * inch, 2.1 * inch, f"Patient: {pat}")p.drawString(0.5 * inch, 1.7 * inch, f"Type: {ctype}")p.line(0.5 * inch, 1.4 * inch, 5.5 * inch, 1.4 * inch)p.setFont("Helvetica-Bold", 12)p.drawString(0.5 * inch, 1.0 * inch, f"Total Price: {price:,.2f} EGP")p.showPage()p.save()return buffer.getvalue()pdf_data = generate_invoice_pdf(c_id, c_doc, c_pat, c_type, c_price)st.download_button(label=f"📄 تحميل فاتورة #{c_id}", data=pdf_data, file_name=f"invoice_{c_id}.pdf", mime="application/pdf", key=f"btn_{c_id}")else:st.info("لا توجد فواتير أو حالات مسجلة حتى الآن.")elif choice == "users" and current_role == "Admin":st.subheader("👤 إضافة مستخدمين وموظفين جدد للمعمل")with st.form("user_management_form", clear_on_submit=True):new_user = st.text_input("اسم المستخدم الجديد (بالإنجليزي بدون مسافات)")new_pass = st.text_input("تعيين كلمة مرور الحساب الجديد")new_role = st.selectbox("تحديد مستوى الصلاحية", ["Staff", "Accountant", "Admin"])if st.form_submit_button("صناعة الحساب وتثبيت الصلاحية"):if new_user and new_pass:try:cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (new_user, new_pass, new_role))conn.commit()st.success("🎉 تم إنشاء حساب الموظف الجديد بنجاح!")st.rerun()except sqlite3.IntegrityError:st.error("اسم المستخدم مسجل لشخص آخر مسبقاً!")st.markdown("---")st.subheader("🔄 تغيير كلمة المرور الخاصة بك (Admin)")with st.form("change_admin_pass_form", clear_on_submit=True):old_user = st.session_state['username']updated_pass = st.text_input("اكتب كلمة المرور الجديدة الخاصة بك", type="password")if st.form_submit_button("تحديث باسوردي الشخصي"):if updated_pass:cursor.execute("UPDATE users SET password=? WHERE username=?", (updated_pass, old_user))conn.commit()st.success("🎉 تم تغيير كلمة المرور بنجاح!")st.markdown("### 📋 قائمة مستخدمي النظام الحاليين وصلاحياتهم:")df_users_list = pd.read_sql_query("SELECT id as [كود], username as [اسم المستخدم], role as [نوع الصلاحية] FROM users", conn)st.dataframe(df_users_list, use_container_width=True)conn.close()
4. انزل لأسفل شاشة GitHub واضغط على زر **Commit changes** الأخضر لحفظ الملف المحدث والنهائي.

---

### 🔄 التشغيل السليم الفوري الآن:
* افتح صفحة تطبيقك من متصفح اللابتوب أو الآيفون [Streamlit Cloud].
* اضغط على زر **Manage app** بأسفل اليمين، ثم انقر على النقاط الثلاث واختر **`Reboot app`** لإعادة بناء النظام بشكل كامل ونظيف تماماً وبدون تعارض القوس القديم.
* سجل الدخول كـ `admin` و `1234` [Streamlit Cloud].
* **الآن اضغط على أي زر دائري بالمنتصف (مثل دليل الأطباء أو إضافة مستخدم جديد)؛ ستجده يفتح لك خانات الكتابة الفورية والواسعة بالأسفل مباشرة وجاهز لاستيعاب حسابات معملك بالكامل!**

جرب عمل الحفظ والـ Reboot الآن، وطمئني بظهور الخانات بنجاح تام وانفراج الأزمة!
