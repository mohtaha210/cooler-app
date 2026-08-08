import streamlit as st
import pandas as pd
import json
import os

# --- إعدادات الصفحة ---
st.set_page_config(page_title="معمل الرافدين", page_icon="🏭", layout="wide")

# --- تنسيق CSS للسلايدر ---
st.markdown("""
<style>
    .stApp { background-color: #0b1120; color: #f1f5f9; }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] { display: flex !important; overflow-x: auto !important; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "multi_factory_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

all_factories = load_data()

# --- الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center'>🏭 معمل الرافدين</h2>", unsafe_allow_html=True)
    f_name = st.selectbox("المعمل:", list(all_factories.keys()))
    user = st.text_input("اسم المستخدم:")
    password = st.text_input("كلمة المرور:", type="password")
    if st.button("دخول"):
        if f_name in all_factories and all_factories[f_name]["users"].get(user, {}).get("password") == password:
            st.session_state.update({"authenticated": True, "factory_key": f_name, "role": all_factories[f_name]["users"][user]["role"]})
            st.rerun()
    st.stop()

# --- التطبيق ---
factory = all_factories[st.session_state.factory_key]
role = st.session_state.role

# التبويبات بالترتيب الأصلي
tabs = st.tabs(["📊 الرئيسية", "🛒 بيع برادات", "🏭 إنتاج", "📦 مخزن", "➕ إضافة مواد"])

with tabs[0]: # الرئيسية
    st.write("📊 ملخص العمل")
    st.metric("المبيعات الكلية", f"{sum([s.get('total', 0) for s in factory.get('sales_history', [])]):,} د.ع")

with tabs[1]: # بيع
    st.write("🛒 بيع برادات")
    goods = factory.get("finished_goods", {})
    m = st.selectbox("البراد:", list(goods.keys()))
    q = st.number_input("الكمية:", 1, goods.get(m, 0))
    if st.button("بيع"):
        factory["finished_goods"][m] -= q
        save_data(all_factories)
        st.rerun()

with tabs[2]: # إنتاج
    st.write("🏭 إنتاج برادات")
    bom = list(factory.get("bom", {}).keys())
    m = st.selectbox("النوع:", bom)
    q = st.number_input("الكمية:", 1, 100)
    if st.button("إنتاج"):
        factory["finished_goods"][m] = factory["finished_goods"].get(m, 0) + q
        save_data(all_factories)
        st.rerun()

with tabs[3]: # مخزن
    st.write("📦 مخزن المواد الخام")
    st.dataframe(pd.DataFrame(list(factory["inventory"].items()), columns=["المادة", "الكمية"]))

with tabs[4]: # إضافة مواد
    st.write("➕ إضافة مواد")
    name = st.text_input("اسم المادة:")
    qty = st.number_input("الكمية:", min_value=0.0)
    if st.button("تحديث المخزن"):
        factory["inventory"][name] = factory["inventory"].get(name, 0.0) + qty
        save_data(all_factories)
        st.rerun()
