import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- إعدادات النظام ---
st.set_page_config(page_title="نظام معمل الرافدين المتقدم", layout="wide")
DATA_FILE = "factory_data.json"

# --- الدوال الأساسية لإدارة البيانات ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "inventory": {}, "bom": {}, "finished_goods": {}, "sales_history": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- محرك العمليات (Logic Engine) ---
def perform_production(data, item, qty):
    bom = data["bom"].get(item, {})
    # التحقق من توفر المواد
    for material, amount in bom.items():
        if data["inventory"].get(material, 0) < (amount * qty):
            return False, f"نقص في مادة: {material}"
    
    # خصم المواد الخام
    for material, amount in bom.items():
        data["inventory"][material] -= (amount * qty)
    
    # زيادة الإنتاج
    data["finished_goods"][item] = data["finished_goods"].get(item, 0) + qty
    return True, "تمت عملية الإنتاج بنجاح"

# --- الواجهة ---
data = load_data()

# تسجيل الدخول البسيط
if "user" not in st.session_state:
    st.title("🏭 نظام معمل الرافدين")
    user = st.text_input("اسم المستخدم")
    if st.button("دخول"):
        st.session_state.user = user
        st.rerun()
    st.stop()

# التبويبات الرئيسية
tabs = st.tabs(["📊 لوحة القيادة", "🏭 خط الإنتاج", "📦 إدارة المخزن", "🛒 المبيعات", "⚙️ الإعدادات"])

with tabs[0]: # لوحة القيادة
    st.subheader("مؤشرات الأداء")
    col1, col2 = st.columns(2)
    col1.metric("إجمالي المبيعات", f"{sum(s['total'] for s in data['sales_history']):,} د.ع")
    col2.metric("عدد أنواع المنتجات", len(data["finished_goods"]))

with tabs[1]: # خط الإنتاج
    st.subheader("تصنيع جديد")
    item = st.selectbox("اختر المنتج:", list(data["bom"].keys()))
    qty = st.number_input("الكمية المطلوبة:", min_value=1)
    if st.button("تأكيد الإنتاج"):
        success, msg = perform_production(data, item, qty)
        if success:
            save_data(data)
            st.success(msg)
        else:
            st.error(msg)

with tabs[2]: # المخزن
    st.subheader("جرد المواد الخام")
    df = pd.DataFrame(list(data["inventory"].items()), columns=["المادة", "الكمية"])
    st.dataframe(df, use_container_width=True)
    
    with st.expander("إضافة مادة جديدة"):
        new_mat = st.text_input("اسم المادة")
        new_qty = st.number_input("الكمية")
        if st.button("إضافة للمخزن"):
            data["inventory"][new_mat] = data["inventory"].get(new_mat, 0) + new_qty
            save_data(data)
            st.rerun()

with tabs[3]: # المبيعات
    st.subheader("سجل المبيعات")
    item = st.selectbox("المنتج المباع:", list(data["finished_goods"].keys()))
    qty = st.number_input("الكمية:", min_value=1)
    price = st.number_input("سعر البيع للقطعة:", min_value=0)
    
    if st.button("تسجيل عملية بيع"):
        if data["finished_goods"].get(item, 0) >= qty:
            data["finished_goods"][item] -= qty
            data["sales_history"].append({"date": str(datetime.now()), "item": item, "qty": qty, "total": qty * price})
            save_data(data)
            st.success("تم تسجيل البيع!")
        else:
            st.error("المخزون غير كافٍ")

with tabs[4]: # الإعدادات
    st.subheader("إدارة الوصفات (BOM)")
    # هنا يمكنك إضافة واجهة لإضافة مكونات المنتجات
    st.json(data["bom"])
