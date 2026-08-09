import sqlite3
import pandas as pd
import streamlit as st

# إعداد قاعدة البيانات في الذاكرة المؤقتة مع جداول قابلة للتطوير
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
    cursor.executemany("INSERT INTO materials (name, quantity, unit) VALUES (?, ?, ?)", [
        ('صفيحة معدنية', 100, 'قطعة'),
        ('ضاغط تبريد (كمبريسور)', 50, 'قطعة'),
        ('خزان مياه داخلي', 60, 'قطعة')
    ])
    cursor.execute("INSERT INTO products (name, quantity) VALUES ('براد ماء ستانلس 2 بزبور', 5)")
    cursor.execute("INSERT INTO agents (name, phone, debt) VALUES ('وكيل بغداد', '07700000000', 250000)")
    
    conn.commit()
    return conn

conn = get_connection()
cursor = conn.cursor()

st.title("🏭 نظام إدارة معمل برادات الماء المتطور")

# ==================== قسم إدارة المواد الخام ====================
st.header("📦 إدارة المواد الخام والمخزن")

col1, col2 = st.columns(2)

with col1:
    st.subheader("➕ إضافة مادة خام جديدة")
    with st.form("add_material_form"):
        new_mat_name = st.text_input("اسم المادة الخام")
        new_mat_qty = st.number_input("الكمية الأولية", min_value=0.0, step=1.0)
        new_mat_unit = st.text_input("الوحدة (مثلاً: قطعة، متر، كغ)")
        submitted_mat = st.form_submit_button("إضافة المادة")
        
        if submitted_mat and new_mat_name:
            cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES (?, ?, ?)", 
                           (new_mat_name, new_mat_qty, new_mat_unit))
            conn.commit()
            st.success(f"تمت إضافة المادة ({new_mat_name}) بنجاح!")
            st.rerun()

with col2:
    st.subheader("🔄 تعديل أو إضافة كمية لمادة موجودة")
    materials_list = pd.read_sql("SELECT * FROM materials", conn)
    if not materials_list.empty:
        selected_mat_id = st.selectbox("اختر المادة للتعديل", materials_list['id'], format_func=lambda x: materials_list[materials_list['id'] == x]['name'].values[0])
        current_qty = materials_list[materials_list['id'] == selected_mat_id]['quantity'].values[0]
        
        st.write(f"الكمية الحالية: **{current_qty}**")
        added_qty = st.number_input("الكمية المراد إضافتها (أو خصمها بقيمة سالبة)", value=0.0, step=1.0)
        
        if st.button("تحديث كمية المادة"):
            cursor.execute("UPDATE materials SET quantity = quantity + ? WHERE id = ?", (added_qty, selected_mat_id))
            conn.commit()
            st.success("تم تحديث الكمية بنجاح!")
            st.rerun()

st.subheader("📋 قائمة المواد الخام الحالية:")
updated_materials_df = pd.read_sql("SELECT id AS 'المعرف', name AS 'المادة', quantity AS 'الكمية', unit AS 'الوحدة' FROM materials", conn)
st.dataframe(updated_materials_df, use_container_width=True)

# زر حذف مادة خام قديمة
with st.expander("🗑️ حذف مادة خام قديمة"):
    mat_to_delete = st.selectbox("اختر المادة المراد حذفها نهائياً", updated_materials_df['المعرف'], format_func=lambda x: updated_materials_df[updated_materials_df['المعرف'] == x]['المادة'].values[0])
    if st.button("حذف هذه المادة", type="secondary"):
        cursor.execute("DELETE FROM materials WHERE id = ?", (mat_to_delete,))
        conn.commit()
        st.warning("تم حذف المادة من المخزن!")
        st.rerun()


# ==================== قسم المنتجات والإنتاج ====================
st.header("⚙️ إدارة المنتجات وخط الإنتاج")

col_p1, col_p2 = st.columns(2)

with col_p1:
    st.subheader("➕ إضافة صنف براد جديد للمصنع")
    with st.form("add_product_form"):
        new_prod_name = st.text_input("اسم صنف البراد الجديد (مثلاً: براد ستانلس 4 بزبور)")
        initial_prod_qty = st.number_input("الكمية الأولية الجاهزة", min_value=0, step=1)
        submitted_prod = st.form_submit_button("إضافة الصنف")
        
        if submitted_prod and new_prod_name:
            cursor.execute("INSERT INTO products (name, quantity) VALUES (?, ?)", (new_prod_name, initial_prod_qty))
            conn.commit()
            st.success(f"تمت إضافة الصنف ({new_prod_name}) بنجاح!")
            st.rerun()

with col_p2:
    st.subheader("⚙️ عملية الإنتاج")
    products_list = pd.read_sql("SELECT * FROM products", conn)
    if not products_list.empty:
        selected_prod_to_produce = st.selectbox("اختر البراد المراد إنتاجه", products_list['id'], format_func=lambda x: products_list[products_list['id'] == x]['name'].values[0])
        
        if st.button("🚀 إنتاج وحدة واحدة وخصم المواد الأساسية تلقائياً", type="primary"):
            # كمثال افتراضي للخصم (يخصم وحدة واحدة من المواد الرئيسية المتاحة)
            cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name IN ('صفيحة معدنية', 'ضاغط تبريد (كمبريسور)', 'خزان مياه داخلي')")
            cursor.execute("UPDATE products SET quantity = quantity + 1 WHERE id = ?", (selected_prod_to_produce,))
            conn.commit()
            st.success("تم إنتاج البراد بنجاح وتم خصم المواد الخام المستهلكة!")
            st.rerun()

st.subheader("📦 البرادات الجاهزة في المخزن:")
products_df = pd.read_sql("SELECT id AS 'المعرف', name AS 'نوع البراد', quantity AS 'الكمية الجاهزة' FROM products", conn)
st.dataframe(products_df, use_container_width=True)


# ==================== قسم الوكلاء والديون ====================
st.header("👥 حسابات الوكلاء والديون")
agents_df = pd.read_sql("SELECT * FROM agents", conn)

for index, row in agents_df.iterrows():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
    col1.write(row['name'])
    col2.write(row['phone'])
    col3.error(f"{row['debt']} د.ع")
    
    with col4:
        with st.form(key=f"form_{row['id']}"):
            t_type = st.selectbox("الحركة", ["sale (بيع بالدين)", "payment (تسديد)"], key=f"type_{row['id']}")
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
