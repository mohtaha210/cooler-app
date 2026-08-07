import io
import pandas as pd
import streamlit as st

# 1. ضبط إعدادات الصفحة والتصميم
st.set_page_config(
    page_title="نظام إدارة مخزون البرادات",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# تحسين مظهر الواجهة باستخدام CSS بسيط
st.markdown(
    """
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
        border-right: 5px solid #007bff;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 2. نظام تسجيل الدخول
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 تسجيل الدخول - معمل البرادات")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")

    if st.button("تسجيل الدخول", type="primary", use_container_width=True):
        if username == "admin" and password == "123456":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()

# 3. تهيئة البيانات الافتراضية
if "inventory" not in st.session_state:
    st.session_state.inventory = {
        "الحنفية": 100.0,
        "البانكة": 50.0,
        "الماطور": 50.0,
        "التوماتيك": 50.0,
        "الطواف": 50.0,
        "الراديتر": 50.0,
        "زواية القاعدة": 200.0,
        "المنيوم القاعدة 1.35m": 50.0,
        "الجكنة": 100.0,
        "واشر حديد": 100.0,
        "واشر بلاستك": 100.0,
        "زبانة": 100.0,
        "كبلري 1.7m": 50.0,
        "كويل": 50.0,
        "بوري ربع 1.5m": 50.0,
        "طبقة وربع بليت": 50.0,
    }

if "bom" not in st.session_state:
    st.session_state.bom = {
        "براد حنفية واحدة": {
            "الحنفية": 1,
            "البانكة": 1,
            "الماطور": 1,
            "التوماتيك": 1,
            "الطواف": 1,
            "الراديتر": 1,
            "زواية القاعدة": 4,
            "المنيوم القاعدة 1.35m": 1,
            "الجكنة": 1,
            "واشر حديد": 1,
            "واشر بلاستك": 1,
            "زبانة": 1,
            "كبلري 1.7m": 1,
            "كويل": 1,
            "بوري ربع 1.5m": 1,
            "طبقة وربع بليت": 1.25,
        },
        "براد حنفيتين": {
            "الحنفية": 2,
            "البانكة": 1,
            "الماطور": 1,
            "التوماتيك": 1,
            "الطواف": 1,
            "الراديتر": 1,
            "زواية القاعدة": 4,
            "المنيوم القاعدة 1.35m": 1,
            "الجكنة": 2,
            "واشر حديد": 2,
            "واشر بلاستك": 2,
            "زبانة": 2,
            "كبلري 1.7m": 1,
            "كويل": 1,
            "بوري ربع 1.5m": 1,
            "طبقة وربع بليت": 1.25,
        },
    }

# 4. الرأس والإحصائيات السريعة
st.title("❄️ نظام إدارة وتتبع مخزون البرادات")

# عرض بطاقات إحصائية في الأعلى
col_stat1, col_stat2, col_stat3 = st.columns(3)
total_items = len(st.session_state.inventory)
zero_items = sum(
    1 for qty in st.session_state.inventory.values() if qty <= 0
)

with col_stat1:
    st.metric(label="إجمالي أصل المواد", value=f"{total_items} مادة")
with col_stat2:
    st.metric(label="المواد المنتهية (0)", value=f"{zero_items} مادة")
with col_stat3:
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.authenticated = False
        st.rerun()

st.write("---")

# 5. التبويبات الرئيسية
tabs = st.tabs(
    [
        "🏭 تسجيل إنتاج",
        "📦 إدارة وتعديل المخزون",
        "📄 طباعة وتصدير Excel",
        "➕ إضافة مادة جديدة",
        "🛠️ أنواع البرادات (BOM)",
    ]
)

# --- 1. تسجيل الإنتاج ---
with tabs[0]:
    st.header("تسجيل عملية إنتاج براد")
    model_list = list(st.session_state.bom.keys())
    if not model_list:
        st.warning("لا توجد أنواع برادات معروفة في النظام حالياً.")
    else:
        model = st.selectbox("اختر نوع البراد المصنوع:", model_list)
        count = st.number_input(
            "عدد البرادات المصنعة:", min_value=1, value=1, step=1
        )

        if st.button(
            "🚀 خصم المواد وتأكيد الإنتاج",
            type="primary",
            use_container_width=True,
        ):
            required_bom = st.session_state.bom[model]
            missing_items = []

            for item, qty in required_bom.items():
                needed = qty * count
                available = st.session_state.inventory.get(item, 0)
                if available < needed:
                    missing_items.append(
                        f"- **{item}**: المطلوب ({needed})، المتوفر ({available})"
                    )

            if missing_items:
                st.error("❌ لا يوجد مخزون كافٍ لإتمام العملية!")
                for m in missing_items:
                    st.write(m)
            else:
                for item, qty in required_bom.items():
                    st.session_state.inventory[item] -= qty * count
                st.success(
                    f"✅ تم تسجيل إنتاج ({count}) من [{model}] وخصم المواد بنجاح!"
                )
                st.rerun()

# --- 2. إدارة وتعديل المخزون (مع زر التصفير) ---
with tabs[1]:
    st.header("عرض وتعديل كميات المخزون الحالية")

    df = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة"],
    )

    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True
    )

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button(
            "💾 حفظ التعديلات على الجدول", use_container_width=True
        ):
            new_inv = {}
            for _, row in edited_df.iterrows():
                if row["اسم المادة الخام"]:
                    new_inv[row["اسم المادة الخام"]] = float(
                        row["الكمية المتوفرة"]
                    )
            st.session_state.inventory = new_inv
            st.success("✅ تم تحديث بيانات المخزون بنجاح!")
            st.rerun()

    # قسم تصفير المخزون مع التحذير
    with col_btn2:
        with st.popover("⚠️ تصفير جميع المواد في المخزن"):
            st.warning(
                "هل أنت أصلًا متأكد؟ هذا الإجراء سيجعل جميع كميات المواد مساوية لـ (0)!"
            )
            if st.button(
                "نعم، أؤكد تصفير كافة الكميات",
                type="primary",
                use_container_width=True,
            ):
                for item in st.session_state.inventory:
                    st.session_state.inventory[item] = 0.0
                st.success("⚠️ تم تصفير كافة كميات المخزون بنجاح!")
                st.rerun()

# --- 3. طباعة وتصدير مستند Excel ---
with tabs[2]:
    st.header("تصدير تقرير جرد المخزون إلى Excel")
    st.write(
        "يمكنك تنزيل ملف Excel يحتوي على الكميات النهائية الحالية لاستخدامه في الطباعة أو الجرد الورقي."
    )

    df_export = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة حالياً"],
    )

    # إنشاء ملف Excel في الذاكرة لتنزيله
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="جرد_المخزون")

    st.download_button(
        label="📥 تنزيل تقرير المخزون (Excel)",
        data=buffer.getvalue(),
        file_name="جرد_مخزون_المعمل.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.subheader("معاينة البيانات قبل التصدير:")
    st.dataframe(df_export, use_container_width=True)

# --- 4. إضافة مادة جديدة ---
with tabs[3]:
    st.header("إضافة مادة خام جديدة كلياً")
    new_item_name = st.text_input("اسم المادة الخام الجديدة:")
    initial_qty = st.number_input("الكمية الأولية:", min_value=0.0, value=0.0)

    if st.button(
        "➕ إضافة المادة للمخزن", type="primary", use_container_width=True
    ):
        if new_item_name:
            if new_item_name in st.session_state.inventory:
                st.warning("هذه المادة موجودة بالفعل بالمخزن!")
            else:
                st.session_state.inventory[new_item_name] = initial_qty
                st.success(f"✅ تمت إضافة المادة [{new_item_name}] بنجاح!")
                st.rerun()
        else:
            st.error("يرجى إدخال اسم المادة.")

# --- 5. أنواع البرادات (BOM) ---
with tabs[4]:
    st.header("تعريف نموذج براد جديد وقائمة مكوناته")
    new_model_name = st.text_input(
        "اسم نموذج البراد الجديد (مثال: براد 3 حنفيات):"
    )

    st.subheader("حدد المواد والكميات التي يستهلكها البراد الواحد:")
    selected_ingredients = {}

    for item in st.session_state.inventory.keys():
        use_item = st.checkbox(f"يدخل فيه: {item}", key=f"chk_{item}")
        if use_item:
            qty_needed = st.number_input(
                f"الكمية المطلوبة من [{item}]:",
                min_value=0.1,
                value=1.0,
                key=f"qty_{item}",
            )
            selected_ingredients[item] = qty_needed

    if st.button("🛠️ حفظ النموذج الجديد", use_container_width=True):
        if new_model_name and selected_ingredients:
            st.session_state.bom[new_model_name] = selected_ingredients
            st.success(f"✅ تم تعريف النموذج [{new_model_name}] بنجاح!")
            st.rerun()
        else:
            st.error("يرجى تحديد اسم النموذج واختيار مادة واحدة على الأقل!")
