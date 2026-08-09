import sqlite3
import pandas as pd
import streamlit as st

# إعداد قاعدة البيانات في الذاكرة المؤقتة
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity REAL,
        unit TEXT
    )''')
    
    cursor.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        debt REAL DEFAULT 0
    )''')
    
    cursor.execute('''CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        type TEXT,
        amount REAL,
        details TEXT,
        date TEXT
    )''')
    
    # بيانات تجريبية أولية
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('صفيحة معدنية', 100, 'قطعة')")
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('ضاغط تبريد (كمبريسور)', 50, 'قطعة')")
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('خزان مياه داخلي', 60, 'قطعة')")
    cursor.execute("INSERT INTO products (name, quantity) VALUES ('براد ماء ستانلس 2 بزبور', 5)")
    cursor.execute("INSERT INTO agents (name, phone, debt) VALUES ('وكيل بغداد', '07700000000', 250000)")
    
    conn.commit()
    return conn

conn = get_connection()
cursor = conn.cursor()

st.title("🏭 نظام إدارة معمل برادات الماء")

# قسم الإنتاج والمخزون
st.header("⚙️ إدارة الإنتاج والمخزون")

if st.button("إنتاج براد ماء جديد", type="primary"):
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'صفيحة معدنية'")
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'ضاغط تبريد (كمبريسور)'")
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'خزان مياه داخلي'")
    cursor.execute("UPDATE products SET quantity = quantity + 1 WHERE name = 'براد ماء ستانلس 2 بزبور'")
    conn.commit()
    st.success("تم إنتاج البراد وخصم المواد الخام بنجاح!")
    st.rerun()

st.subheader("المواد الخام المتاحة:")
materials_df = pd.read_sql("SELECT name AS 'المادة', quantity AS 'الكمية', unit AS 'الوحدة' FROM materials", conn)
st.dataframe(materials_df, use_container_width=True)

st.subheader("البرادات الجاهزة في المخزن:")
products_df = pd.read_sql("SELECT name AS 'نوع البراد', quantity AS 'الكمية' FROM products", conn)
st.dataframe(products_df, use_container_width=True)

# قسم الوكلاء والديون
st.header("👥 حسابات الوكلاء والديون")
agents_df = pd.read_sql("SELECT * FROM agents", conn)

for index, row in agents_df.iterrows():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
    col1.write(row['name'])
    col2.write(row['phone'])
    col3.error(f"{row['debt']} د.ع")
    
    with col4:
        with st.form(key=f"form_{row['id']}"):
            t_type = st.selectbox("نوع الحركة", ["sale (بيع بالدين)", "payment (تسديد)"], key=f"type_{row['id']}")
            amount = st.number_input("المبلغ (د.ع)", min_value=0.0, step=1000.0, key=f"amt_{row['id']}")
            details = st.text_input("التفاصيل", key=f"det_{row['id']}")
            submit = st.form_submit_button("تسجيل")
            
            if submit:
                actual_type = 'sale' if 'sale' in t_type else 'payment'
                debt_change = amount if actual_type == 'sale' else -amount
                cursor.execute("UPDATE agents SET debt = debt + ? WHERE id = ?", (debt_change, row['id']))
                cursor.execute("INSERT INTO transactions (agent_id, type, amount, details) VALUES (?, ?, ?, ?)",
                               (row['id'], actual_type, amount, details))
                conn.commit()
                st.success("تم الحفظ بنجاح!")
                st.rerun()
