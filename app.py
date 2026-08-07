import pandas as pd
import streamlit as st

# ضبط إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة مخزون البرادات المتقدم", page_icon="🏭", layout="wide"
)

# --- نظام تسجيل الدخول البسيط ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 تسجيل الدخول لنظام المعمل")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")

    if st.button("تسجيل الدخول", type="primary"):
        # يمكنك تغيير كلمة المرور واسم المستخدم هنا
        if username == "admin" and password == "123456":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()  # إيقاف عرض بقية التطبيق حتى تسجيل الدخول

# --- تهيئة البيانات المبدئية عند التشغيل لأول مرة ---
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

# --- شريط الأقسام المتقدم ---
st.title("❄️ لوحة تحكم مخزون معمل البرادات")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

tabs = st.tabs(
    [
        "🏭 تسجيل إنتاج",
        "📦 إدارة وتعديل المخزون",
        "➕ إضافة مادة خام جديدة",
        "🛠️ إضافة/تعديل أنواع البرادات",
    ]
)

# --- 1. تسجيل الإنتاج ---
with tabs[0]:
    st.header("تسجيل عملية إنتاج براد")
    model_list = list(st.session_state.bom.keys())
    if not model_list:
        st.warning(" لا توجد أنواع برادات معرفة بالنظام حالياً.")
    else:
        model = st.selectbox("اختر نوع البراد المصنوع:", model_list)
        count = st.number_input(
            "عدد البرادات المصنعة:", min_value=1, value=1, step=1
        )

        if st.button("🚀 خصم المواد وتأكيد الإنتاج", type="primary"):
            required_bom = st.session_state.bom[model]
            missing_items = []

            for item, qty in required_bom.items():
                needed = qty * count
                available = st.session_state.inventory.get(item, 0)
                if available < needed:
                    missing_items.append(
                        f"- **{item}**: المطلوب ({needed})، المتوفر حالياً ({available})"
                    )

            if missing_items:
                st.error("❌ لا يوجد مخزون كافٍ!")
                for m in missing_items:
                    st.write(m)
            else:
                for item, qty in required_bom.items():
                    st.session_state.inventory[item] -= qty * count
                st.success(
                    f"✅ تم تسجيل إنتاج ({count}) من [{model}] وخصم المواد بنجاح!"
                )

# --- 2. إدارة وتعديل المخزون ---
with tabs[1]:
    st.header("عرض وتعديل كميات المخزون الحالية")

    df = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة"],
    )

    # جدول تفاعلي يسمح بتعديل الكميات مباشرة أو إزالة المادة
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True
    )

    if st.button("💾 حفظ التعديلات على الجدول"):
        # إعادة تحديث المخزون بالقيم الجديدة من الجدول
        new_inv = {}
        for _, row in edited_df.iterrows():
            if row["اسم المادة الخام"]:
                new_inv[row["اسم المادة الخام"]] = float(
                    row["الكمية المتوفرة"]
                )
        st.session_state.inventory = new_inv
        st.success("✅ تم تحديث المخزون بنجاح!")

# --- 3. إضافة مادة جديدة ---
with tabs[2]:
    st.header("إضافة مادة خام جديدة كلياً للمخزن")
    new_item_name = st.text_input("اسم المادة الخام الجديدة:")
    initial_qty = st.number_input("الكمية الأولية:", min_value=0.0, value=0.0)

    if st.button("➕ إضافة المادة للمخزن"):
        if new_item_name:
            if new_item_name in st.session_state.inventory:
                st.warning("هذه المادة موجودة بالفعل بالمخزن!")
            else:
                st.session_state.inventory[new_item_name] = initial_qty
                st.success(f"✅ تمت إضافة المادة [{new_item_name}] بنجاح!")
        else:
            st.error("يرجى إدخال اسم المادة.")

# --- 4. إضافة أو تعديل أنواع البرادات ---
with tabs[3]:
    st.header("إضافة نوع براد جديد وقائمة مكوناته (BOM)")
    new_model_name = st.text_input("اسم نموذج البراد الجديد (مثال: براد 3 حنفيات):")

    st.subheader("حدد المواد والكميات التي يستهلكها هذا البراد:")
    selected_ingredients = {}

    for item in st.session_state.inventory.keys():
        use_item = st.checkbox(f"يدخل فيه: {item}", key=f"chk_{item}")
        if use_item:
            qty_needed = st.number_input(
                f"الكمية المطلوبة من [{item}] لإنتاج براد واحد:",
                min_value=0.1,
                value=1.0,
                key=f"qty_{item}",
            )
            selected_ingredients[item] = qty_needed

    if st.button("🛠️ حفظ النموذج الجديد"):
        if new_model_name and selected_ingredients:
            st.session_state.bom[new_model_name] = selected_ingredients
            st.success(
                f"✅ تم تعريف النموذج الجديد [{new_model_name}] بنجاح!"
            )
        else:
            st.error("يرجى تحديد اسم النموذج واختيار مادة واحدة على الأقل!")
