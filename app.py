import sqlite3
import pandas as pd
import streamlit as st

# إعداد قاعدة البيانات في الذاكرة المؤقتة مع جداول الوصفات
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المواد الخام
    cursor.execute('''CREATE TABLE materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity REAL,
        unit TEXT
    )''')
    
    # جدول المنتجات (البرادات)
    cursor.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity INTEGER
    )''')
    
    # جدول ربط البراد بالمواد الخام المطلوبة (الوصفة/المقادير)
    cursor.execute('''CREATE TABLE product_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        material_id INTEGER,
        required_quantity REAL
    )''')
    
    # جدول الوكلاء والديون
    cursor.execute('''CREATE TABLE agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        debt REAL DEFAULT 0
    )''')
    
    # جدول الحركات المالية
    cursor.execute('''CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        type TEXT,
        amount REAL,
        details TEXT,
        date TEXT
    )''')
    
    # بيانات تجريبية أولية لبعض المواد
    cursor.executemany("INSERT INTO materials (name, quantity, unit) VALUES (?, ?, ?)", [
        ('صفيحة معدنية', 200, 'قطعة'),
        ('ضاغط تبريد (كمبريسور)', 100, 'قطعة'),
        ('خزان مياه داخلي', 100, 'قطعة'),
        ('أنبوب نحاس', 500, 'متر')
    ])
    
    cursor.execute("INSERT INTO products (name, quantity) VALUES ('براد ماء ستانلس قياسي', 5)")
    
    # ربط البراد الافتراضي ببعض المواد (كمثال، يمكنك إضافة حتى 28 مادة لكل براد)
    cursor.execute("INSERT INTO product_materials (product_id, material_id, required_quantity) VALUES (1, 1, 1)") # 1 صفيحة
    cursor.execute("INSERT INTO product_materials (product_id, material_id, required_quantity) VALUES (1, 2, 1)") # 1 كمبريسور
    cursor.execute("INSERT INTO product_materials (product_id, material_id, required_quantity) VALUES (1, 3, 1)") # 1 خزان
    cursor.execute("INSERT INTO product_materials (product_id, material_id, required_quantity) VALUES (1, 4, 3)") # 3 أمتار نحاس

    cursor.execute("INSERT INTO agents (name, phone, debt) VALUES ('وكيل بغداد', '07700000000', 250000)")
    
    conn.commit()
    return conn

conn = get_connection()
cursor = conn.cursor()

st.title("🏭 نظام إدارة معمل برادات الماء المتقدم")

# ==================== قسم إدارة المواد الخام ====================
st.header("📦 إدارة المواد الخام والمخزن")

col1, col2 = st.columns(2)

with col1:
    st.subheader("➕ إضافة مادة خام جديدة")
    with st.form("add_material_form"):
        new_mat_name = st.text_input("اسم المادة الخام")
        new_mat_qty = st.number_input("الكمية الأولية", min_value=0.0, step=1.0)
        new_mat_unit = st.text_input("الوحدة (قطعة، متر، كغ...)")
        submitted_mat = st.form_submit_button("إضافة المادة")
        
        if submitted_mat and new_mat_name:
            cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES (?, ?, ?)", 
                           (new_mat_name, new_mat_qty, new_mat_unit))
            conn.commit()
            st.success(f"تمت إضافة المادة ({new_mat_name}) بنجاح!")
            st.rerun()

with col2:
    st.subheader("🔄 تعديل كمية مادة موجودة")
    materials_list = pd.read_sql("SELECT * FROM materials", conn)
    if not materials_list.empty:
        selected_mat_id = st.selectbox("اختر المادة", materials_list['id'], format_func=lambda x: materials_list[materials_list['id'] == x]['name'].values[0])
        current_qty = materials_list[materials_list['id'] == selected_mat_id]['quantity'].values[0]
        
        st.write(f"الكمية الحالية: **{current_qty}**")
        added_qty = st.number_input("الكمية المراد إضافتها (أو خصمها بقيمة سالبة)", value=0.0, step=1.0)
        
        if st.button("تحديث الكمية"):
            cursor.execute("UPDATE materials SET quantity = quantity + ? WHERE id = ?", (added_qty, selected_mat_id))
            conn.commit()
            st.success("تم التحديث بنجاح!")
            st.rerun()

st.subheader("📋 قائمة المواد الخام:")
updated_materials_df = pd.read_sql("SELECT id AS 'المعرف', name AS 'المادة', quantity AS 'الكمية', unit AS 'الوحدة' FROM materials", conn)
st.dataframe(updated_materials_df, use_container_width=True)


# ==================== إدارة المنتجات وربط المواد (حتى 28 مادة) ====================
st.header("⚙️ إدارة أصناف البرادات ومقادير التصنيع")

col_p1, col_p2 = st.columns(2)

with col_p1:
    st.subheader("➕ إضافة صنف براد جديد")
    with st.form("add_product_form"):
        new_prod_name = st.text_input("اسم صنف البراد الجديد")
        initial_prod_qty = st.number_input("الكمية الأولية الجاهزة", min_value=0, step=1)
        submitted_prod = st.form_submit_button("إضافة الصنف")
        
        if submitted_prod and new_prod_name:
            cursor.execute("INSERT INTO products (name, quantity) VALUES (?, ?)", (new_prod_name, initial_prod_qty))
            conn.commit()
            st.success(f"تمت إضافة الصنف ({new_prod_name}) بنجاح!")
            st.rerun()

with col_p2:
    st.subheader("🔗 ربط المواد الخام بالبراد (المقادير)")
    products_list = pd.read_sql("SELECT * FROM products", conn)
    if not products_list.empty and not materials_list.empty:
        target_prod_id = st.selectbox("اختر البراد لتحديد مواده", products_list['id'], format_func=lambda x: products_list[products_list['id'] == x]['name'].values[0], key="p_recipe")
        target_mat_id = st.selectbox("اختر المادة الخام المطلوبة لهذا البراد", materials_list['id'], format_func=lambda x: materials_list[materials_list['id'] == x]['name'].values[0], key="m_recipe")
        req_qty = st.number_input("الكمية المطلوبة من هذه المادة للبراد الواحد", min_value=0.01, step=1.0, value=1.0)
        
        if st.button("حفظ هذه المادة في وصفة البراد"):
            # التحقق إذا كانت مضافة مسبقاً لتحديثها أو إضافتها جديدة
            cursor.execute("INSERT OR REPLACE INTO product_materials (product_id, material_id, required_quantity) VALUES (?, ?, ?)", 
                           (target_prod_id, target_mat_id, req_qty))
            conn.commit()
            st.success("تم ربط المادة بالبراد بنجاح! (كرر هذه الخطوة لإضافة حتى 28 مادة للبراد الواحد)")
            st.rerun()

# عرض مكونات البراد المحدد
st.subheader("📜 تفاصيل المواد المطلوبة لكل براد:")
if not products_list.empty:
    selected_view_prod = st.selectbox("اختر براد لعرض مواده الخام", products_list['id'], format_func=lambda x: products_list[products_list['id'] == x]['name'].values[0], key="view_recipe")
    recipe_df = pd.read_sql(f"""
        SELECT m.name AS 'المادة الخام', pm.required_quantity AS 'الكمية المطلوبة للبراد الواحد', m.unit AS 'الوحدة' 
        FROM product_materials pm 
        JOIN materials m ON pm.material_id = m.id 
        WHERE pm.product_id = {selected_view_prod}
    """, conn)
    st.dataframe(recipe_df, use_container_width=True)


# ==================== زر الإنتاج الذكي ====================
st.header("🚀 خط الإنتاج الذكي")
if not products_list.empty:
    prod_to_produce = st.selectbox("اختر البراد المراد إنتاجه الآن", products_list['id'], format_func=lambda x: products_list[products_list['id'] == x]['name'].values[0], key="produce_box")
    prod_count_to_make = st.number_input("عدد القطع المراد إنتاجها", min_value=1, step=1, value=1)
    
    if st.button("⚙️ تنفيذ الإنتاج وخصم المواد الخام تلقائياً", type="primary"):
        # جلب المواد المطلوبة لهذا البراد
        cursor.execute("SELECT material_id, required_quantity FROM product_materials WHERE product_id = ?", (prod_to_produce,))
        required_materials = cursor.fetchall()
        
        if not required_materials:
            st.error("⚠️ هذا البراد ليس له مواد خام مربوطة به! قم بربط المواد أولاً من قسم 'ربط المواد الخام بالبراد'.")
        else:
            # التحقق من توفر الكميات أولاً
            can_produce = True
            error_msg = ""
            for mat_id, req_q in required_materials:
                total_needed = req_q * prod_count_to_make
                cursor.execute("SELECT name, quantity FROM materials WHERE id = ?", (mat_id,))
                mat_data = cursor.fetchone()
                if mat_data[1] < total_needed:
                    can_produce = False
                    error_msg = f"❌ المخزن غير كافٍ للمادة: ({mat_data[0]}). المتاح: {mat_data[1]}، والمطلوب: {total_needed}"
                    break
            
            if not can_produce:
                st.error(error_msg)
            else:
                # خصم المواد من المخزن
                for mat_id, req_q in required_materials:
                    total_needed = req_q * prod_count_to_make
                    cursor.execute("UPDATE materials SET quantity = quantity - ? WHERE id = ?", (total_needed, mat_id))
                
                # زيادة عدد البرادات الجاهزة
                cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (prod_count_to_make, prod_to_produce))
                conn.commit()
                st.success(f"🎉 تم إنتاج ({prod_count_to_make}) براد بنجاح، وخصم المواد الخام المقررة تلقائياً من المخزن!")
                st.rerun()

st.subheader("📦 المخزن الحالي للبرادات الجاهزة:")
products_df_final = pd.read_sql("SELECT id AS 'المعرف', name AS 'نوع البراد', quantity AS 'الكمية الجاهزة' FROM products", conn)
st.dataframe(products_df_final, use_container_width=True)


# ==================== قسم الوكلاء والديون ====================
st.header("👥 حسابات الوكلاء والديون")
agents_df = pd.read_sql("SELECT * FROM agents", conn)

for index, row in agents_df.iterrows():
    col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 2, 3])
    col_a1.write(row['name'])
    col_a2.write(row['phone'])
    col_a3.error(f"{row['debt']} د.ع")
    
    with col_a4:
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
