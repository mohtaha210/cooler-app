from datetime import datetime
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات وتخطيط الصفحة ---
st.set_page_config(page_title="نظام معمل الرافدين", page_icon="🍏", layout="wide")

# --- تنسيقات CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b1120; color: #f1f5f9; font-family: Tahoma; }
    .card { background: #fff; color: #000; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "rafidain_factory_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"inventory": {}, "bom": {}, "finished_goods": {}, "agents": {}, "sales_history": [], "receipt_counter": 1001}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()

# تهيئة session_state للطباعة
if "last_invoice" not in st.session_state: st.session_state.last_invoice = None

tabs = st.tabs(["📦 المواد الخام", "🛠️ وصفات البرادات", "🏭 الإنتاج", "🤝 الوكلاء", "🛒 المبيعات"])

# 1, 2, 3: المواد، الوصفات، الإنتاج (نفس المنطق السابق)
with tabs[0]:
    mat_name = st.text_input("اسم المادة الخام:", key="m_name")
    mat_qty = st.number_input("الكمية:", min_value=0.0, value=0.0, key="m_qty")
    if st.button("حفظ المادة"):
        db["inventory"][mat_name] = db["inventory"].get(mat_name, 0.0) + mat_qty
        save_data(db); st.rerun()

with tabs[1]:
    model_name = st.text_input("اسم النموذج:", key="mod_name")
    if st.button("حفظ وصفة"):
        db["bom"][model_name] = {"مادة": 1.0} # مثال مبسط
        save_data(db); st.rerun()

with tabs[2]:
    p_mod = st.selectbox("نموذج للإنتاج:", list(db["bom"].keys()) if db["bom"] else [])
    if st.button("تأكيد الإنتاج"):
        db["finished_goods"][p_mod] = db["finished_goods"].get(p_mod, 0) + 1
        save_data(db); st.rerun()

with tabs[3]:
    a_name = st.text_input("اسم الوكيل:", key="ag_n")
    if st.button("إضافة وكيل"):
        db["agents"][a_name] = {"debt": 0.0}
        save_data(db); st.rerun()

# 5. المبيعات (القسم المعدل)
with tabs[4]:
    st.markdown("### 🛒 نقطة البيع")
    b_type = st.radio("نوع المشتري:", ["عميل مباشر", "وكيل مسجل"], horizontal=True)
    buyer = st.text_input("اسم العميل/الوكيل:")
    
    cart = {}
    for m, stock in db["finished_goods"].items():
        q = st.number_input(f"{m} (المتوفر {stock})", 0, stock, key=f"q_{m}")
        if q > 0: cart[m] = q
    
    tot_inv = sum(q * 100000 for m, q in cart.items()) # سعر افتراضي
    paid_now = st.number_input("المبلغ المدفوع:", 0.0, float(tot_inv), 0.0)
    
    if st.button("إتمام البيع وإصدار الوثائق"):
        r_no = db["receipt_counter"]
        db["receipt_counter"] += 1
        
        prev_debt = db["agents"].get(buyer, {}).get("debt", 0.0) if b_type == "وكيل مسجل" else 0.0
        remaining = tot_inv - paid_now
        
        if b_type == "وكيل مسجل" and buyer in db["agents"]:
            db["agents"][buyer]["debt"] += remaining
        
        save_data(db)
        
        # تخزين بيانات الطباعة
        st.session_state.last_invoice = {
            "r_no": r_no, "buyer": buyer, "rows": cart, "tot": tot_inv, 
            "paid": paid_now, "rem": remaining, "prev": prev_debt
        }
        st.success("تم إتمام البيع!")

    # عرض أزرار التحميل
    if st.session_state.last_invoice:
        inv = st.session_state.last_invoice
        rows_html = "".join([f"<tr><td>{m}</td><td>{q}</td></tr>" for m, q in inv['rows'].items()])
        
        invoice_html = f"""<html><body dir="rtl"><div class="card">
        <h3>قائمة حسابات #{inv['r_no']}</h3>
        <p>الاسم: {inv['buyer']}</p><table>{rows_html}</table>
        <p>الإجمالي: {inv['tot']} | المدفوع: {inv['paid']} | المتبقي: {inv['rem']}</p>
        </div></body></html>"""
        
        receipt_html = f"""<html><body dir="rtl"><div class="card">
        <h2>معمل الرافدين للبرادات</h2>
        <h3>وصل قبض نقدي #{inv['r_no']}</h3>
        <p>الاسم: {inv['buyer']}</p>
        <p>المبلغ المسدد: {inv['paid']} | المتبقي في الذمة: {inv['prev'] + inv['rem']}</p>
        </div></body></html>"""
        
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 تحميل قائمة الحسابات", invoice_html, f"قائمة_{inv['r_no']}.html", "text/html")
        with c2:
            st.download_button("📥 تحميل وصل القبض", receipt_html, f"وصل_{inv['r_no']}.html", "text/html")
