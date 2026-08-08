import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="معمل برادات الماء", layout="wide")

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('factory.db')
    c = conn.cursor()
    # 1. المواد الخام
    c.execute('''CREATE TABLE IF NOT EXISTS raw_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, 
                    quantity REAL, 
                    unit_cost REAL)''')
    
    # 2. البرادات الجاهزة
    c.execute('''CREATE TABLE IF NOT EXISTS finished_coolers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    model_name TEXT UNIQUE, 
                    stock INTEGER DEFAULT 0, 
                    selling_price REAL DEFAULT 0)''')
    
    # 3. وصفة التصنيع (ربط البراد بالمواد الخام)
    c.execute('''CREATE TABLE IF NOT EXISTS recipe (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER,
                    material_id INTEGER,
                    required_qty REAL,
                    FOREIGN KEY(model_id) REFERENCES finished_coolers(id),
                    FOREIGN KEY(material_id) REFERENCES raw_materials(id))''')

    # 4. الوكلاء والديون
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, 
                    phone TEXT, 
                    balance REAL DEFAULT 0)''')
    
    # 5. المعاملات والوصولات
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    client_id INTEGER, 
                    type TEXT, 
                    amount REAL, 
                    details TEXT, 
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- القائمة الجانبية ---
st.sidebar.title("🧊 معمل برادات الماء")
menu = st.sidebar.radio("الانتقال إلى:", [
    "الرئيسية", 
    "المواد الخام (28 مادة)", 
    "تعريف خلطة البراد (BOM)", 
    "⚙️ خط التصنيع والإنتاج", 
    "مخزن البرادات", 
    "الوكلاء والديون"
])

conn = sqlite3.connect('factory.db')

# --- 1. الرئيسية ---
if menu == "الرئيسية":
    st.title("📊 لوحة تحكم المعمل")
    col1, col2, col3 = st.columns(3)
    
    coolers_count = pd.read_sql_query("SELECT SUM(stock) as total FROM finished_coolers", conn)['total'].fillna(0).iloc[0]
    total_debts = pd.read_sql_query("SELECT SUM(balance) as total FROM clients WHERE balance > 0", conn)['total'].fillna(0).iloc[0]
    mat_count = pd.read_sql_query("SELECT COUNT(*) as total FROM raw_materials", conn)['total'].iloc[0]
    
    col1.metric("إجمالي البرادات بالإنتاج/المخزن", f"{int(coolers_count)} براد")
    col2.metric("إجمالي ديون الوكلاء (لصالحنا)", f"{total_debts:,.0f} د.ع")
    col3.metric("المواد الخام المسجلة", f"{mat_count} مادة")

# --- 2. المواد الخام ---
elif menu == "المواد الخام (28 مادة)":
    st.title("📦 مخزن المواد الخام")
    
    with st.expander("➕ إضافة مادة خام جديدة"):
        with st.form("add_mat"):
            name = st.text_input("اسم المادة (موتور، نحاس، صاج...)")
            qty = st.number_input("الكمية المتاحة حالياً", min_value=0.0)
            cost = st.number_input("تكلفة الوحدة", min_value=0.0)
            if st.form_submit_button("إضافة للمخزن") and name:
                c = conn.cursor()
                c.execute("INSERT INTO raw_materials (name, quantity, unit_cost) VALUES (?, ?, ?)", (name, qty, cost))
                conn.commit()
                st.success("تم التحديث!")
                st.rerun()
                
    df_mat = pd.read_sql_query("SELECT id as '#', name as 'اسم المادة', quantity as 'الكمية المتوفرة', unit_cost as 'التكلفة' FROM raw_materials", conn)
    st.dataframe(df_mat, use_container_width=True)

# --- 3. تعريف وصفة البراد ---
elif menu == "تعريف خلطة البراد (BOM)":
    st.title("🛠️ ربط البراد بالمواد الخام (الوصفة)")
    st.info("هنا تحدد المواد الـ 28 أو جزء منها والكمية التي يستعملها البراد الواحد.")
    
    # إضافة موديل جديد
    with st.expander("➕ إضافة موديل براد جديد"):
        with st.form("add_model"):
            m_name = st.text_input("اسم موديل البراد (مثال: براد 3 عيون)")
            m_price = st.number_input("سعر البيع الافتراضي للوكيل", min_value=0.0)
            if st.form_submit_button("حفظ الموديل") and m_name:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO finished_coolers (model_name, selling_price) VALUES (?, ?)", (m_name, m_price))
                    conn.commit()
                    st.success("تمت إضافة الموديل!")
                    st.rerun()
                except:
                    st.error("الموديل موجود مسبقاً!")

    # تحديد المكونات
    models = pd.read_sql_query("SELECT * FROM finished_coolers", conn)
    materials = pd.read_sql_query("SELECT * FROM raw_materials", conn)

    if not models.empty and not materials.empty:
        st.subheader("إضافة مادة خام إلى موديل براد")
        col1, col2, col3 = st.columns(3)
        selected_model = col1.selectbox("اختر موديل البراد", models['model_name'])
        selected_mat = col2.selectbox("اختر المادة الخام", materials['name'])
        req_qty = col3.number_input("الكمية المطلوبة للبراد الواحد", min_value=0.01, step=0.1)

        if st.button("ربط المادة بالبراد"):
            m_id = models[models['model_name'] == selected_model]['id'].values[0]
            mat_id = materials[materials['name'] == selected_mat]['id'].values[0]
            c = conn.cursor()
            c.execute("INSERT INTO recipe (model_id, material_id, required_qty) VALUES (?, ?, ?)", (m_id, mat_id, req_qty))
            conn.commit()
            st.success(f"تم ربط {selected_mat} بـ {selected_model}")
            st.rerun()

        # عرض المكونات لكل موديل
        st.subheader("📋 جدول المكونات المسجلة لكل براد")
        query = '''
            SELECT finished_coolers.model_name as 'الموديل', 
                   raw_materials.name as 'المادة الخام', 
                   recipe.required_qty as 'الكمية للبراد الواحد'
            FROM recipe
            JOIN finished_coolers ON recipe.model_id = finished_coolers.id
            JOIN raw_materials ON recipe.material_id = raw_materials.id
        '''
        st.dataframe(pd.read_sql_query(query, conn), use_container_width=True)

# --- 4. خط التصنيع والإنتاج (الخصم الآلي) ---
elif menu == "⚙️ خط التصنيع والإنتاج":
    st.title("⚙️ أمر تصنيع وتشغيل")
    st.markdown("عند كتابة العدد المراد تصنيعه، **سيقوم النظام تلقائياً بخصم المواد الخام من المخزن** وإضافة البرادات المصنعة إلى مخزن المنتجات التامة.")

    models = pd.read_sql_query("SELECT * FROM finished_coolers", conn)
    if models.empty:
        st.warning("يرجى تعريف موديلات البرادات أولاً من قائمة (تعريف خلطة البراد).")
    else:
        col1, col2 = st.columns(2)
        selected_model = col1.selectbox("اختر البراد المراد تصنيعه", models['model_name'])
        produce_qty = col2.number_input("عدد البرادات المراد إنتاجها", min_value=1, step=1)

        model_id = models[models['model_name'] == selected_model]['id'].values[0]

        # جلب المواد المطلوبة لهذا الموديل
        recipe_df = pd.read_sql_query(f'''
            SELECT recipe.material_id, recipe.required_qty, raw_materials.name, raw_materials.quantity as current_stock
            FROM recipe 
            JOIN raw_materials ON recipe.material_id = raw_materials.id
            WHERE recipe.model_id = {model_id}
        ''', conn)

        if recipe_df.empty:
            st.error("هذا البراد ليس له مواد خام معرّفة! يرجى إضافة مكوناته أولاً من قسم (تعريف خلطة البراد).")
        else:
            st.subheader("المواد المطلوب خصمها من المخزن:")
            recipe_df['الكمية الإجمالية المطلوبة'] = recipe_df['required_qty'] * produce_qty
            st.dataframe(recipe_df[['name', 'required_qty', 'الكمية الإجمالية المطلوبة', 'current_stock']].rename(columns={
                'name': 'المادة الخام',
                'required_qty': 'المطلوب للبراد الواحد',
                'current_stock': 'المتوفر بالمخزن حالياً'
            }), use_container_width=True)

            # التحقق من كفاية المخزون
            insufficient = recipe_df[recipe_df['الكمية الإجمالية المطلوبة'] > recipe_df['current_stock']]

            if not insufficient.empty:
                st.error("⚠️ لا يمكن إتمام التصنيع! بعض المواد الخام غير كافية بالمخزن:")
                for _, row in insufficient.iterrows():
                    st.write(f"- **{row['name']}**: المطلوب {row['الكمية الإجمالية المطلوبة']} والحيوي المتوفر {row['current_stock']}")
            else:
                if st.button("🚀 تأكيد تصنيع الوجبة وخصم المواد الخام"):
                    c = conn.cursor()
                    # 1. خصم المواد الخام
                    for _, row in recipe_df.iterrows():
                        new_qty = row['current_stock'] - row['الكمية الإجمالية المطلوبة']
                        c.execute("UPDATE raw_materials SET quantity = ? WHERE id = ?", (new_qty, row['material_id']))

                    # 2. إضافة البرادات لمخزن المنتج التام
                    c.execute("UPDATE finished_coolers SET stock = stock + ? WHERE id = ?", (produce_qty, model_id))
                    
                    conn.commit()
                    st.success(f"✅ تم تصنيع {produce_qty} براد بنجاح! وتم خصم جميع المواد الخام من المخزن.")
                    st.rerun()

# --- 5. مخزن البرادات ---
elif menu == "مخزن البرادات":
    st.title("🧊 مخزن البرادات الجاهزة للبيع")
    df_coolers = pd.read_sql_query("SELECT id as '#', model_name as 'الموديل', stock as 'العدد المتوفر', selling_price as 'سعر البيع للوكيل' FROM finished_coolers", conn)
    st.dataframe(df_coolers, use_container_width=True)

# --- 6. الوكلاء والديون ---
elif menu == "الوكلاء والديون":
    st.title("👥 إدارة حسابات الوكلاء والديون")
    
    with st.expander("➕ إضافة وكيل جديد / دين سابق"):
        with st.form("add_client"):
            name = st.text_input("اسم الوكيل/الزبون")
            phone = st.text_input("رقم الهاتف")
            balance = st.number_input("الدين السابـق", value=0.0)
            if st.form_submit_button("حفظ الوكيل") and name:
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
        details = col3.text_input("التفاصيل (مثلاً: دفعة نقداً / تسليم برادات)")
        
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

conn.close()
