import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="معمل برادات الماء", layout="wide")

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('factory.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS raw_materials (id INTEGER PRIMARY KEY, name TEXT, quantity REAL, unit_cost REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS finished_coolers (id INTEGER PRIMARY KEY, model_name TEXT, stock INTEGER, cost_price REAL, selling_price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, client_id INTEGER, type TEXT, amount REAL, details TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- القائمة الجانبية ---
st.sidebar.title("🧊 معمل برادات الماء")
menu = st.sidebar.radio("الانتقال إلى:", ["الرئيسية", "الوكلاء والديون", "المواد الخام (28 مادة)", "مخزن البرادات"])

conn = sqlite3.connect('factory.db')

# --- 1. الرئيسية ---
if menu == "الرئيسية":
    st.title("📊 لوحة تحكم المعمل")
    
    col1, col2, col3 = st.columns(3)
    
    coolers_count = pd.read_sql_query("SELECT SUM(stock) as total FROM finished_coolers", conn)['total'].fillna(0).iloc[0]
    total_debts = pd.read_sql_query("SELECT SUM(balance) as total FROM clients WHERE balance > 0", conn)['total'].fillna(0).iloc[0]
    mat_count = pd.read_sql_query("SELECT COUNT(*) as total FROM raw_materials", conn)['total'].iloc[0]
    
    col1.metric("إجمالي البرادات والمخزون", f"{int(coolers_count)} براد")
    col2.metric("إجمالي ديون الوكلاء (لصالحنا)", f"{total_debts:,.0f} د.ع")
    col3.metric("المواد الخام المسجلة", f"{mat_count} مادة")

# --- 2. الوكلاء والديون ---
elif menu == "الوكلاء والديون":
    st.title("👥 إدارة حسابات الوكلاء والديون")
    
    with st.expander("➕ إضافة وكيل جديد / دين سابق"):
        with st.form("add_client"):
            name = st.text_input("اسم الوكيل/الزبون")
            phone = st.text_input("رقم الهاتف")
            balance = st.number_input("الدين السابـق", value=0.0)
            submit = st.form_submit_button("حفظ الوكيل")
            if submit and name:
                c = conn.cursor()
                c.execute("INSERT INTO clients (name, phone, balance) VALUES (?, ?, ?)", (name, phone, balance))
                conn.commit()
                st.success("تمت إضافة الوكيل بنجاح!")
                st.rerun()

    df_clients = pd.read_sql_query("SELECT id as '#', name as 'الاسم', phone as 'الهاتف', balance as 'الدين/الرصيد الحالي' FROM clients", conn)
    st.dataframe(df_clients, use_container_width=True)

    st.subheader("📝 تسجيل معاملة جديدة (سند قبض / فاتورة مبيعات)")
    clients_list = pd.read_sql_query("SELECT id, name FROM clients", conn)
    if not clients_list.empty:
        selected_client_name = st.selectbox("اختر الوكيل", clients_list['name'])
        client_id = clients_list[clients_list['name'] == selected_client_name]['id'].values[0]
        
        col1, col2, col3 = st.columns(3)
        trans_type = col1.selectbox("نوع المعاملة", ["سند قبض (استلام مبلغ)", "فاتورة بيع (إضافة دين)"])
        amount = col2.number_input("المبلغ", min_value=0.0)
        details = col3.text_input("التفاصيل (مثلاً: دفعة نقداً / تسليم 10 برادات)")
        
        if st.button("حفظ وتحديث الرصيد"):
            c = conn.cursor()
            type_code = 'PAYMENT' if "سند قبض" in trans_type else 'INVOICE'
            if type_code == 'PAYMENT':
                c.execute("UPDATE clients SET balance = balance - ? WHERE id = ?", (amount, client_id))
            else:
                c.execute("UPDATE clients SET balance = balance + ? WHERE id = ?", (amount, client_id))
            
            c.execute("INSERT INTO transactions (client_id, type, amount, details) VALUES (?, ?, ?, ?)",
                      (client_id, type_code, amount, details))
            conn.commit()
            st.success("تم تسجيل المعاملة وتحديث حساب الوكيل!")
            st.rerun()

# --- 3. المواد الخام ---
elif menu == "المواد الخام (28 مادة)":
    st.title("📦 مخزن المواد الخام")
    
    with st.expander("➕ إضافة مادة خام جديد"):
        with st.form("add_mat"):
            name = st.text_input("اسم المادة (موتور، نحاس، صاج...)")
            qty = st.number_input("الكمية", min_value=0.0)
            cost = st.number_input("تكلفة الوحدة", min_value=0.0)
            if st.form_submit_button("إضافة للمخزن") and name:
                c = conn.cursor()
                c.execute("INSERT INTO raw_materials (name, quantity, unit_cost) VALUES (?, ?, ?)", (name, qty, cost))
                conn.commit()
                st.success("تم التحديث!")
                st.rerun()
                
    df_mat = pd.read_sql_query("SELECT id as '#', name as 'اسم المادة', quantity as 'الكمية', unit_cost as 'التكلفة' FROM raw_materials", conn)
    st.dataframe(df_mat, use_container_width=True)

# --- 4. مخزن البرادات ---
elif menu == "مخزن البرادات":
    st.title("🧊 مخزن برادات الماء التامة")
    
    with st.expander("➕ إدخال وجبة برادات مصنعة"):
        with st.form("add_cooler"):
            model = st.text_input("موديل البراد")
            stock = st.number_input("العدد المصنع", min_value=0)
            cost = st.number_input("تكلفة التصنيع للواحد", min_value=0.0)
            sell = st.number_input("سعر البيع للوكيل", min_value=0.0)
            if st.form_submit_button("حفظ بالمخزن") and model:
                c = conn.cursor()
                c.execute("INSERT INTO finished_coolers (model_name, stock, cost_price, selling_price) VALUES (?, ?, ?, ?)", (model, stock, cost, sell))
                conn.commit()
                st.success("تم الحفظ!")
                st.rerun()
                
    df_coolers = pd.read_sql_query("SELECT id as '#', model_name as 'الموديل', stock as 'العدد', cost_price as 'التكلفة', selling_price as 'سعر البيع' FROM finished_coolers", conn)
    st.dataframe(df_coolers, use_container_width=True)

conn.close()
