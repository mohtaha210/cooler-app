import streamlit as st
import pandas as pd
import json
import os

# --- إعدادات الصفحة ---
st.set_page_config(page_title="معمل الرافدين", page_icon="🏭", layout="wide")

# --- تنسيق CSS للتبويبات (سلايدر الموبايل) ---
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
</style>
""", unsafe_allow_html=True)

DATA_FILE = "multi_factory_data.json"

# --- الدوال ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

all_factories = load_data()

# --- تسجيل الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center'>🏭 معمل الرافدين</h2>", unsafe_allow_html=True)
    f_name = st.selectbox("اختر المعمل:", list(all_factories.keys()) if all_factories else ["لا يوجد"])
    user = st.text_input("اسم المستخدم:")
    password = st.text_input("كلمة المرور:", type="password")
    if st.button("دخول"):
        if f_name in all_factories and all_factories[f_name]["users"].get(user, {}).get("password") == password:
            st.session_state.update({"authenticated": True, "factory_key": f_name, "role": all_factories[f_name]["users"][user]["role"]})
            st.rerun()
    st.stop()

# --- التطبيق ---
factory = all_factories[st.session_state.factory_key]

# التبويبات
if st.session_state.role == "admin":
    tabs = st.tabs(["📊 الرئيسية", "🛒 بيع", "🏭 إنتاج", "📦 مخزن", "➕ إضافة مواد", "👥 موظفين"])
else:
    tabs = st.tabs(["🛒 بيع", "📦 مخزن"])

# 1. الرئيسية
with tabs[0]:
    st.write("### 📊 ملخص العمل")
    st.metric("إجمالي المبيعات", f"{sum([s['total'] for s in factory.get('sales_history', [])]):,} د.ع")

# 2. البيع
with tabs[1]:
    st.write("### 🛒 تسجيل عملية بيع")
    item = st.selectbox("المادة:", list(factory["inventory"].keys()))
    qty = st.number_input("الكمية:", min_value=1)
    if st.button("بيع"):
        factory["inventory"][item] -= qty
        save_data(all_factories)
        st.success("تم البيع!")

# 3. الإنتاج (للأدمن فقط)
if st.session_state.role == "admin":
    with tabs[2]:
        st.write("### 🏭 تسجيل إنتاج")
        if st.button("تأكيد التصنيع"):
            save_data(all_factories)

# 4. المخزن
with tabs[3 if st.session_state.role == "admin" else 1]:
    st.write("### 📦 المخزون الحالي")
    df = pd.DataFrame(list(factory["inventory"].items()), columns=["المادة", "الكمية"])
    st.dataframe(df, use_container_width=True)

# 5. إضافة مواد (للأدمن فقط)
if st.session_state.role == "admin":
    with tabs[4]:
        st.write("### ➕ إضافة مواد خام")
        m_list = list(factory["inventory"].keys())
        m_choice = st.selectbox("المادة:", ["مادة جديدة..."] + m_list)
        m_name = st.text_input("اسم المادة الجديدة:") if m_choice == "مادة جديدة..." else m_choice
        m_qty = st.number_input("الكمية المضافة:", min_value=1.0)
        if st.button("تحديث المخزن"):
            factory["inventory"][m_name] = factory["inventory"].get(m_name, 0.0) + m_qty
            save_data(all_factories)
            st.success(f"تمت إضافة {m_qty} إلى {m_name}")
            st.rerun()

# 6. موظفين (للأدمن)
if st.session_state.role == "admin":
    with tabs[5]:
        st.write("### 👥 الموظفين")
        st.json(factory["users"])
