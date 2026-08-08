from datetime import datetime
import io
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات الصفحة ---
st.set_page_config(page_title="معمل الرافدين", page_icon="🏭", layout="wide")

# --- CSS للسلايدر الأفقي ---
st.markdown("""
<style>
    .stApp { background-color: #0b1120; color: #f1f5f9; }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        display: flex !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        scrollbar-width: none !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "multi_factory_data.json"

# --- الدوال الأساسية ---
def load_all_factories():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

all_factories = load_all_factories()

# --- تسجيل الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center'>🏭 معمل الرافدين</h2>", unsafe_allow_html=True)
    factory_list = list(all_factories.keys())
    selected_factory = st.selectbox("اختر المعمل:", factory_list)
    username = st.text_input("اسم المستخدم:")
    password = st.text_input("كلمة المرور:", type="password")
    if st.button("دخول"):
        if selected_factory in all_factories and all_factories[selected_factory]["users"].get(username, {}).get("password") == password:
            st.session_state.update({"authenticated": True, "factory_key": selected_factory, "role": all_factories[selected_factory]["users"][username]["role"], "user_fullname": all_factories[selected_factory]["users"][username]["name"]})
            st.rerun()
    st.stop()

# --- التطبيق الرئيسي ---
factory_data = all_factories[st.session_state.factory_key]

# نظام التبويبات (السلايدر)
tabs = st.tabs(["📊 رئيسية", "🛒 بيع برادات", "🏭 إنتاج", "📦 مخزن", "➕ إضافة مواد"])

# 1. الرئيسية
with tabs[0]:
    st.write("### 📊 ملخص المعمل")
    sales_df = pd.DataFrame(factory_data.get("sales_history", []))
    total = sales_df["total"].sum() if not sales_df.empty else 0
    st.metric("إجمالي المبيعات", f"{total:,} د.ع")

# 2. بيع البرادات
with tabs[1]:
    st.write("### 🛒 تسجيل بيع براد")
    # استعراض البرادات الجاهزة فقط
    for model, qty in factory_data["finished_goods"].items():
        st.write(f"**{model}** (المتوفر: {qty})")
        # هنا يمكنك إضافة زر البيع لكل نوع
    st.info("قم باختيار البراد المطلوب لإتمام عملية البيع...")

# 3. الإنتاج
with tabs[2]:
    st.write("### 🏭 تسجيل إنتاج براد")
    model_prod = st.selectbox("نوع البراد:", list(factory_data["bom"].keys()))
    if st.button("تأكيد الإنتاج"):
        # منطق خصم المواد من المخزن
        save_all_factories(all_factories)
        st.rerun()

# 4. المخزن
with tabs[3]:
    st.write("### 📦 مخزن المواد الخام")
    inv_df = pd.DataFrame(list(factory_data["inventory"].items()), columns=["المادة", "الكمية"])
    st.dataframe(inv_df, use_container_width=True)

# 5. إضافة مواد/إكمال النقص
with tabs[4]:
    st.write("### ➕ إضافة مواد خام للمخزن")
    mat_name = st.text_input("اسم المادة:")
    add_qty = st.number_input("الكمية المضافة:", min_value=0.0)
    if st.button("تحديث المخزن"):
        factory_data["inventory"][mat_name] = factory_data["inventory"].get(mat_name, 0.0) + add_qty
        save_all_factories(all_factories)
        st.success("تم تحديث المخزن!")
        st.rerun()
