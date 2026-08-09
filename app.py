from datetime import datetime
import json
import os
import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF
import pandas as pd
import requests
import streamlit as st

DATA_FILE = "multi_factory_data.json"

# --- 1. إدارة ملف البيانات والتخزين الدائم ---
def get_default_factory_data(factory_name, admin_user, admin_pass):
    return {
        "info": {"factory_name": factory_name},
        "users": {
            admin_user: {
                "password": admin_pass,
                "role": "admin",
                "name": f"مدير {factory_name}",
            }
        },
        "inventory": {
            "الحنفية": 100.0, "البانكة": 50.0, "الماطور": 50.0, "التوماتيك": 50.0,
            "الطواف": 50.0, "الراديتر": 50.0, "زواية القاعدة": 200.0,
            "المنيوم القاعدة 1.35m": 50.0, "الجكنة": 100.0, "واشر حديد": 100.0,
            "واشر بلاستك": 100.0, "زبانة": 100.0, "كبلري 1.7m": 50.0,
            "كويل": 50.0, "بوري ربع 1.5m": 50.0, "طبقة وربع بليت": 1.25,
        },
        "finished_goods": {"براد حنفية واحدة": 0, "براد حنفيتين": 0},
        "agents": {},
        "bom": {
            "براد حنفية واحدة": {"الحنفية": 1, "البانكة": 1, "الماطور": 1, "التوماتيك": 1, "الطواف": 1, "الراديتر": 1, "زواية القاعدة": 4, "المنيوم القاعدة 1.35m": 1, "الجكنة": 1, "واشر حديد": 1, "واشر بلاستك": 1, "زبانة": 1, "كبلري 1.7m": 1, "كويل": 1, "بوري ربع 1.5m": 1, "طبقة وربع بليت": 1.25},
            "براد حنفيتين": {"الحنفية": 2, "البانكة": 1, "الماطور": 1, "التوماتيك": 1, "الطواف": 1, "الراديتر": 1, "زواية القاعدة": 4, "المنيوم القاعدة 1.35m": 1, "الجكنة": 2, "واشر حديد": 2, "واشر بلاستك": 2, "زبانة": 2, "كبلري 1.7m": 1, "كويل": 1, "بوري ربع 1.5m": 1, "طبقة وربع بليت": 1.25},
        },
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": [],
    }

def load_all_factories():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: 
            return {}
    return {}

def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. الطباعة و PDF ---
def ar(text):
    if not text: 
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))

@st.cache_resource
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        try:
            with open(font_path, "wb") as f: 
                f.write(requests.get(url).content)
        except: 
            pass
    return font_path

def generate_receipt_pdf(factory_name, customer_name, date_str, items_data, grand_total, paid_amount, remaining_amount, receipt_no):
    pdf = FPDF()
    pdf.add_page()
    font_path = ensure_arabic_font()
    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path, uni=True)
        pdf.set_font("Amiri", "", 16)
    pdf.cell(0, 10, ar(f"قائمة حساب - {factory_name}"), ln=True, align="C")
    pdf.cell(0, 10, ar(f"الزبون: {customer_name} | التاريخ: {date_str}"), ln=True, align="R")
    pdf.cell(0, 10, ar(f"رقم القائمة: #{receipt_no}"), ln=True, align="R")
    pdf.ln(10)
    for item in items_data:
        pdf.cell(0, 10, ar(f"{item['model']} x {item['count']} = {item['total']:,} د.ع"), ln=True, align="R")
    pdf.cell(0, 10, ar(f"الإجمالي: {grand_total:,} | المدفوع: {paid_amount:,} | المتبقي: {remaining_amount:,}"), ln=True, align="R")
    return bytes(pdf.output())

# --- 3. إعداد الصفحة وتسجيل الدخول ---
st.set_page_config(page_title="نظام إدارة معمل البرادات", layout="wide")
all_factories = load_all_factories()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not all_factories:
    st.title("⚙️ الإعداد الأولي للمعمل")
    with st.form("setup_form"):
        f_name = st.text_input("اسم المعمل:", value="معمل البرادات")
        u_name = st.text_input("اسم مستخدم المدير:", value="admin")
        u_pass = st.text_input("كلمة المرور:", type="password", value="1234")
        submitted = st.form_submit_button("إنشاء المعمل وبدء النظام")
        if submitted:
            all_factories["main_factory"] = get_default_factory_data(f_name, u_name, u_pass)
            save_all_factories(all_factories)
            st.success("تم الإنشاء بنجاح! يرجى إعادة تحميل الصفحة.")
            st.rerun()
    st.stop()

if not st.session_state.authenticated:
    st.title("🔐 تسجيل الدخول إلى النظام")
    factory_key = list(all_factories.keys())[0]
    factory_data = all_factories[factory_key]
    
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        login_btn = st.form_submit_button("دخول")
        if login_btn:
            if username in factory_data["users"] and factory_data["users"][username]["password"] == password:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.factory_key = factory_key
                st.success("تم تسجيل الدخول بنجاح!")
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
    st.stop()

# --- 4. واجهة النظام الرئيسية ---
current_factory_key = st.session_state.get("factory_key", list(all_factories.keys())[0])
factory_data = all_factories[current_factory_key]

st.title(f"🏭 {factory_data['info']['factory_name']} - لوحة التحكم")

tabs = st.tabs(["إدارة الوكلاء والديون", "الإنتاج", "المبيعات", "المخزون"])

# --- تبويب إدارة الوكلاء والديون (مع الإصلاح النهائي للسالب) ---
with tabs[0]:
    st.subheader("إدارة الوكلاء وتسديد الديون")
    
    sub_tab1, sub_tab2 = st.tabs(["➕ إضافة وكيل", "💵 تسديد دين / قبض نقدي"])
    
    with sub_tab1:
        new_agent_name = st.text_input("اسم الوكيل الجديد:")
        init_debt = st.number_input("الدين الافتتاحي (ضع علامة سالب إذا كان ديناً عليه مثل -50000):", value=0.0)
        if st.button("حفظ الوكيل الجديد"):
            if new_agent_name:
                if new_agent_name not in factory_data["agents"]:
                    factory_data["agents"][new_agent_name] = {"debt": init_debt, "transactions": []}
                    save_all_factories(all_factories)
                    st.success(f"تم إضافة الوكيل {new_agent_name} بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم الوكيل موجود مسبقاً.")
            else:
                st.warning("يرجى إدخال اسم الوكيل.")

    with sub_tab2:
        agents = list(factory_data["agents"].keys())
        if agents:
            selected_ag = st.selectbox("اختر الوكيل:", agents)
            current_debt = factory_data["agents"][selected_ag].get("debt", 0.0)
            
            st.info(f"💰 الدين الحالي على الوكيل [{selected_ag}]: {current_debt:,.1f} د.ع")
            
            pay_amount = st.number_input("المبلغ المدفوع (المستلم):", min_value=0.0, value=0.0, step=1000.0)
            pay_note = st.text_input("ملاحظات / بيان الدفعة:", value="تسديد دفعة نقداً")
            
            if st.button("💵 تأكيد استلام المبلغ وخصمه من الدين", type="primary"):
                if pay_amount > 0:
                    # التصحيح البرمجي النهائي: جمع المبلغ الموجب مع الدين السالب لتقليصه نحو الصفر
                    new_debt = current_debt + pay_amount
                    factory_data["agents"][selected_ag]["debt"] = new_debt
                    
                    receipt_no = factory_data.get("receipt_counter", 1001)
                    factory_data["receipt_counter"] = receipt_no + 1
                    
                    factory_data["agents"][selected_ag].setdefault("transactions", []).append({
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "تسديد دفعة",
                        "amount": pay_amount,
                        "balance": new_debt,
                        "note": f"وصل قبض #{receipt_no} - {pay_note}"
                    })
                    
                    save_all_factories(all_factories)
                    st.success(f"تمت العملية بنجاح! الرصيد الجديد: {new_debt:,.1f} د.ع")
                    st.rerun()
                else:
                    st.warning("يرجى إدخال مبلغ صحيح أكبر من صفر.")
            
            # عرض كشف حساب الوكيل
            st.markdown("---")
            st.markdown("### سجل الحركات والديون للوكيل")
            trans_list = factory_data["agents"][selected_ag].get("transactions", [])
            if trans_list:
                df_trans = pd.DataFrame(trans_list)
                st.dataframe(df_trans, use_container_width=True)
            else:
                st.write("لا توجد حركات مسجلة لهذا الوكيل حتى الآن.")
        else:
            st.warning("لا يوجد وكلاء مضافون حالياً. يرجى إضافة وكيل من تبويب (➕ إضافة وكيل).")

# --- تبويب الإنتاج ---
with tabs[1]:
    st.subheader("تسجيل إنتاج البرادات وخصم المواد الأولية")
    prod_model = st.selectbox("اختر نموذج البراد للإنتاج:", list(factory_data["finished_goods"].keys()))
    prod_count = st.number_input("العدد المراد إنتاجه:", min_value=1, value=1)
    
    if st.button("تأكيد الإنتاج وخصم المواد"):
        bom_recipe = factory_data["bom"].get(prod_model, {})
        can_produce = True
        missing_items = []
        
        # التحقق من توفر المواد الأولية في المخزون
        for item, qty_per_unit in bom_recipe.items():
            required_qty = qty_per_unit * prod_count
            current_stock = factory_data["inventory"].get(item, 0.0)
            if current_stock < required_qty:
                can_produce = False
                missing_items.append(f"{item} (المطلوب: {required_qty}, المتوفر: {current_stock})")
        
        if can_produce:
            # خصم المواد من المخزون
            for item, qty_per_unit in bom_recipe.items():
                factory_data["inventory"][item] -= qty_per_unit * prod_count
            
            # زيادة المنتجات الجاهزة
            factory_data["finished_goods"][prod_model] += prod_count
            
            # تسجيل عملية الإنتاج
            factory_data["production_history"].append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "model": prod_model,
                "count": prod_count
            })
            
            save_all_factories(all_factories)
            st.success(f"تم إنتاج {prod_count} من {prod_model} بنجاح وتم خصم المواد من المخزون!")
            st.rerun()
        else:
            st.error("عذراً، لا يمكن إتمام الإنتاج لعدم توفر المواد التالية في المخزون:")
            for m in missing_items:
                st.write(f"- {m}")

# --- تبويب المبيعات ---
with tabs[2]:
    st.subheader("تسجيل عملية بيع جديدة")
    agents = list(factory_data["agents"].keys())
    if agents:
        sales_agent = st.selectbox("الوكيل / الزبون:", agents, key="sales_agent_select")
        sales_model = st.selectbox("نوع البراد:", list(factory_data["finished_goods"].keys()), key="sales_model_select")
        available_qty = factory_data["finished_goods"].get(sales_model, 0)
        
        st.write(գالرصيد الجاهز في المخزن: {available_qty} وحدةգ)
        sales_count = st.number_input("الكمية المباعة:", min_value=1, max_value=max(1, available_qty), value=1)
        unit_price = st.number_input("سعر الوحدة (د.ع):", min_value=0.0, value=0.0, step=1000.0)
        paid_now = st.number_input("المبلغ الواصل (المدفوع نقداً):", min_value=0.0, value=0.0, step=1000.0)
        
        if st.button("إتمام البيع وتحديث الحسابات"):
            total_price = sales_count * unit_price
            remaining_balance_change = total_price - paid_now # زيادة الدين على الوكيل بالمبلغ غير المؤدى
            
            if factory_data["finished_goods"][sales_model] >= sales_count:
                # خصم من المخزون الجاهز
                factory_data["finished_goods"][sales_model] -= sales_count
                
                # تحديث دين الوكيل (زيادة الدين بالمبلغ المتبقي غير المدفوع)
                current_debt = factory_data["agents"][sales_agent].get("debt", 0.0)
                # بما أن الدين سالب (يمثل ذمة مالية على الوكيل)، فإن زيادة الدين تعني جعله أكثر سالبية: current_debt - remaining_balance_change
                new_debt = current_debt - remaining_balance_change
                factory_data["agents"][sales_agent]["debt"] = new_debt
                
                receipt_no = factory_data.get("receipt_counter", 1001)
                factory_data["receipt_counter"] = receipt_no + 1
                
                # تسجيل الحركة في سجل الوكيل
                factory_data["agents"][sales_agent].setdefault("transactions", []).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "مبيعات",
                    "amount": -total_price,
                    "balance": new_debt,
                    "note": f"قائمة مبيعات #{receipt_no} - {sales_count}x {sales_model}"
                })
                
                save_all_factories(all_factories)
                st.success(f"تم إتمام البيع بنجاح! رقم القائمة: #{receipt_no}")
                st.rerun()
            else:
                st.error("الكمية المطلوبة غير متوفرة في المخزون الجاهز.")
    else:
        st.warning("يرجى إضافة وكيل أولاً لتسجيل عمليات المبيعات.")

# --- تبويب المخزون ---
with tabs[3]:
    st.subheader("مخزون المواد الأولية والمنتجات الجاهزة")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### المواد الأولية")
        df_inv = pd.DataFrame.from_dict(factory_data["inventory"], orient='index', columns=['الكمية المتوفرة'])
        st.dataframe(df_inv, use_container_width=True)
    with col2:
        st.markdown("### المنتجات الجاهزة")
        df_fg = pd.DataFrame.from_dict(factory_data["finished_goods"], orient='index', columns=['العدد الجاهز'])
        st.dataframe(df_fg, use_container_width=True)
