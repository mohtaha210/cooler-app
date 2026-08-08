import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- إعدادات الصفحة ---
st.set_page_config(page_title="معمل الرافدين", page_icon="🏭", layout="wide")

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

# --- تسجيل الدخول ---
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

if role == "admin":
    tabs = st.tabs(["📊 رئيسية", "🛒 بيع برادات", "🏭 إنتاج", "📦 مخزن", "➕ إضافة مواد"])
    
    with tabs[0]: # الرئيسية
        st.write("### 📊 ملخص المبيعات")
        sales = factory.get("sales_history", [])
        st.metric("إجمالي المبيعات", f"{sum([s.get('total', 0) for s in sales]):,} د.ع")
    
    with tabs[1]: # بيع برادات
        st.write("### 🛒 تسجيل بيع براد")
        goods = {m: q for m, q in factory.get("finished_goods", {}).items() if q > 0}
        if goods:
            m = st.selectbox("اختر البراد:", list(goods.keys()))
            q = st.number_input(f"الكمية (المتوفر {goods[m]}):", 1, goods[m])
            if st.button("إتمام عملية البيع"):
                factory["finished_goods"][m] -= q
                factory.setdefault("sales_history", []).append({"item": m, "qty": q, "total": 0})
                save_data(all_factories)
                st.success(f"تم بيع {q} من {m}")
                st.rerun()
        else: st.warning("لا يوجد مخزون جاهز للبيع")
        
    with tabs[2]: # إنتاج
        st.write("### 🏭 قسم الإنتاج")
        bom_types = list(factory.get("bom", {}).keys())
        if bom_types:
            selected_type = st.selectbox("اختر البراد للإنتاج:", bom_types)
            prod_qty = st.number_input("الكمية المراد إنتاجها:", 1, 100)
            if st.button("🚀 تأكيد الإنتاج"):
                factory["finished_goods"][selected_type] = factory["finished_goods"].get(selected_type, 0) + prod_qty
                save_data(all_factories)
                st.success(f"تم إنتاج {prod_qty} من {selected_type}")
                st.rerun()
        else: st.warning("لا توجد وصفات إنتاج (BOM) معرفة")
            
    with tabs[3]: # مخزن
        st.write("### 📦 مخزن المواد الخام")
        st.dataframe(pd.DataFrame(list(factory["inventory"].items()), columns=["المادة", "الكمية"]), use_container_width=True)
        
    with tabs[4]: # إضافة مواد
        st.write("### ➕ إضافة مواد خام")
        name = st.text_input("اسم المادة:")
        qty = st.number_input("الكمية:", min_value=0.0)
        if st.button("تحديث المخزن"):
            factory["inventory"][name] = factory["inventory"].get(name, 0.0) + qty
            save_data(all_factories)
            st.success("تم التحديث")
            st.rerun()
else:
    st.write("ليس لديك صلاحية الدخول.")
