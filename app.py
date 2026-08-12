from datetime import datetime
import io
import json
import os
import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF
import pandas as pd
import requests
import streamlit as st

DATA_FILE = "factory_agents_pos_data.json"

# --- 0. دوال مساعدة وتحويل النصوص ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

@st.cache_resource
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
            response = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(response.content)
        except Exception:
            pass
    return font_path

# --- 1. هيكل البيانات الأساسي والشامل ---
def get_default_factory_data():
    return {
        "info": {"factory_name": "مصنع البرادات", "admin_user": "admin", "admin_pass": "1234"},
        "inventory": {
            "الحنفية": 50.0, "البانكة": 20.0, "الماطور": 15.0, "التوماتيك": 20.0,
            "الطواف": 20.0, "الراديتر": 20.0, "زواية القاعدة": 100.0, "المنيوم القاعدة 1.35m": 30.0,
            "الجكنة": 25.0, "واشر حديد": 100.0, "واشر بلاستك": 100.0, "زبانة": 50.0,
            "كبلري 1.7m": 30.0, "كويل": 20.0, "بوري ربع 1.5m": 30.0, "طبقة وربع بليت": 40.0,
            "بوري نص": 30.0, "فلاتر": 30.0, "قاعدة بلاستيك": 20.0, "غطاء علوي": 20.0,
            "صامولة": 100.0, "براغي متنوعة": 500.0, "لحام فضة": 10.0, "غاز رديتر": 15.0,
            "عازل حراري": 25.0, "سلك كهرباء": 50.0, "فيشة كهرباء": 30.0, "لصق وجه": 40.0
        },
        "finished_goods": {
            "براد حنفية واحدة": 10,
            "براد حنفيتين": 10,
        },
        "prices": {
            "براد حنفية واحدة": 150.0,
            "براد حنفيتين": 180.0,
            "الحنفية": 5.0,
            "الماطور": 45.0,
        },
        "bom": {
            "براد حنفية واحدة": {
                "الحنفية": 1, "البانكة": 1, "الماطور": 1, "التوماتيك": 1,
                "الطواف": 1, "الراديتر": 1, "زواية القاعدة": 4, "المنيوم القاعدة 1.35m": 1,
                "الجكنة": 1, "واشر حديد": 1, "واشر بلاستك": 1, "زبانة": 1,
                "كبلري 1.7m": 1, "كويل": 1, "بوري ربع 1.5m": 1, "طبقة وربع بليت": 1.25,
            },
            "براد حنفيتين": {
                "الحنفية": 2, "البانكة": 1, "الماطور": 1, "التوماتيك": 1,
                "الطواف": 1, "الراديتر": 1, "زواية القاعدة": 4, "المنيوم القاعدة 1.35m": 1,
                "الجكنة": 2, "واشر حديد": 2, "واشر بلاستك": 2, "زبانة": 2,
                "كبلري 1.7m": 1, "كويل": 1, "بوري ربع 1.5m": 1, "طبقة وربع بليت": 1.25,
            },
        },
        "agents": {
            "وكيل عام (نقدي)": {"phone": "07700000000", "address": "المصنع", "balance": 0.0}
        },
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": []
    }

def load_factory_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default_structure = get_default_factory_data()
            for key in default_structure:
                if key not in data:
                    data[key] = default_structure[key]
            return data
        except Exception:
            return get_default_factory_data()
    else:
        initial_data = get_default_factory_data()
        save_factory_data(initial_data)
        return initial_data

def save_factory_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    try:
        with open("backup_" + DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# --- 2. توليد مستندات الـ PDF الرسمية ---
def generate_receipt_pdf(
    factory_name, customer_name, date_str, items_data,
    grand_total_usd, discount_usd, net_total_usd, paid_amount_usd,
    remaining_amount_usd, exchange_rate, receipt_no
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)

    pdf.set_y(12)
    if os.path.exists(font_path):
        pdf.set_font("Amiri", "", 18)
    else:
        pdf.set_font("Arial", "B", 16)
    
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, ar(factory_name), ln=True, align="C")
    
    if os.path.exists(font_path):
        pdf.set_font("Amiri", "", 13)
    pdf.cell(0, 6, ar("قائمة حساب"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), 190, 18, style="DF")
    
    y_start = pdf.get_y() + 2
    pdf.set_xy(12, y_start)
    pdf.cell(90, 6, ar(f"رقم القائمة: #{receipt_no}"), align="R")
    pdf.set_xy(110, y_start)
    pdf.cell(88, 6, ar(f"التاريخ: {date_str}"), align="R")
    
    pdf.set_xy(12, y_start + 7)
    pdf.cell(90, 6, ar(f"اسم المشتري: {customer_name}"), align="R")
    pdf.set_xy(110, y_start + 7)
    pdf.cell(88, 6, ar(f"سعر الصرف: {exchange_rate:,.0f} د.ع"), align="R")
    
    pdf.set_y(y_start + 20)
    pdf.ln(4)

    if items_data:
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        if os.path.exists(font_path):
            pdf.set_font("Amiri", "", 10)
            
        col_widths = [35, 35, 20, 45, 55]
        headers = [ar("الإجمالي ($)"), ar("السعر ($)"), ar("الكمية"), ar("الإجمالي (د.ع)"), ar("اسم المادة")]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(33, 37, 41)
        for item in items_data:
            item_total_iqd = item['total_usd'] * exchange_rate
            pdf.cell(col_widths[0], 7, f"${item['total_usd']:,.2f}", border=1, align="C")
            pdf.cell(col_widths[1], 7, f"${item['price_usd']:,.2f}", border=1, align="C")
            pdf.cell(col_widths[2], 7, str(item["count"]), border=1, align="C")
            pdf.cell(col_widths[3], 7, f"{item_total_iqd:,.0f}", border=1, align="C")
            pdf.cell(col_widths[4], 7, ar(item["model"]), border=1, align="C")
            pdf.ln()

    pdf.ln(3)
    net_iqd = net_total_usd * exchange_rate
    paid_iqd = paid_amount_usd * exchange_rate
    rem_iqd = remaining_amount_usd * exchange_rate

    pdf.set_fill_color(226, 232, 240)
    pdf.cell(95, 7, f"${grand_total_usd:,.2f}", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المجموع الكلي"), border=1, align="R")
    pdf.ln()

    if discount_usd > 0:
        pdf.cell(95, 7, f"- ${discount_usd:,.2f}", border=1, align="C", fill=True)
        pdf.cell(95, 7, ar("قيمة الخصم"), border=1, align="R")
        pdf.ln()

    pdf.cell(95, 7, f"${net_total_usd:,.2f} / {net_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("صافي المبلغ المطلوب"), border=1, align="R")
    pdf.ln()

    pdf.cell(95, 7, f"${paid_amount_usd:,.2f} / {paid_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المبلغ المدفوع"), border=1, align="R")
    pdf.ln()

    pdf.cell(95, 7, f"${remaining_amount_usd:,.2f} / {rem_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المبلغ المتبقي (دينار ذمي)"), border=1, align="R")
    pdf.ln(12)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.cell(0, 6, ar("توقيع وختم المعمل: ...................................................."), ln=True, align="C")
    
    return bytes(pdf.output())

# --- 3. تهيئة واجهة التطبيق ---
st.set_page_config(
    page_title="نظام إدارة المعمل والوكلاء",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

factory_data = load_factory_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("❄️ نظام إدارة المعمل والمخزون")
    st.subheader("تسجيل الدخول للنظام")
    
    username_input = st.text_input("اسم المستخدم:")
    password_input = st.text_input("كلمة المرور:", type="password")

    if st.button("تسجيل الدخول", type="primary", use_container_width=True):
        saved_user = factory_data["info"].get("admin_user", "admin")
        saved_pass = factory_data["info"].get("admin_pass", "1234")
        if username_input == saved_user and password_input == saved_pass:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("خطأ في اسم المستخدم أو كلمة المرور!")
    st.stop()

current_factory_name = factory_data["info"].get("factory_name", "مصنع البرادات")
st.title(f"❄️ {current_factory_name}")

if st.button("🚪 تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

st.write("---")

# --- 4. التبويبات الشاملة ---
tabs = st.tabs([
    "🛒 بيع",
    "👥 إدارة الوكلاء والحسابات",
    "🏭 تسجيل إنتاج",
    "📦 المخزون",
    "💲 الأسعار",
    "🛠️ هيكل البرادات (BOM)",
    "📊 التقارير",
    "⚙️ الإعدادات"
])

# تبويب بيع (متطور وبدون جداول إكسل، مع اختيار المشتري والدين)
with tabs[0]:
    st.header("🛒 نقطة البيع والطلبات")
    
    # اختيار أو إدخال بيانات المشتري (وكيل أو زبون مباشر)
    buyer_type = st.radio("نوع المشتري:", ["وكيل معتمد", "زبون مباشر جديد"], horizontal=True)
    
    if buyer_type == "وكيل معتمد":
        agents_list = list(factory_data["agents"].keys())
        selected_buyer = st.selectbox("اختر اسم الوكيل:", agents_list)
        is_registered_agent = True
    else:
        selected_buyer = st.text_input("أدخل اسم الزبون المباشر (مثل: زبون نقدي / اسم الشخص):", value="زبون مباشر")
        is_registered_agent = False

    exchange_rate = st.number_input("سعر صرف الدولار (د.ع مقابل $1):", min_value=1.0, value=1500.0, step=25.0)
    sale_category = st.radio("تصنيف المواد المراد بيعها:", ["برادات جاهزة", "مواد خام"], horizontal=True)
    
    prices_dict = factory_data.get("prices", {})
    
    if "cart" not in st.session_state:
        st.session_state.cart = {}

    st.write("---")
    col_cat, col_crt = st.columns([1.3, 1])

    with col_cat:
        st.subheader("📦 المواد والمنتجات المتوفرة")
        if sale_category == "برادات جاهزة":
            for model, stock in factory_data["finished_goods"].items():
                def_pr = prices_dict.get(model, 0.0)
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**{model}**")
                        st.caption(f"المتوفر بالمخزن: `{stock}` وحدة | السعر الافتراضي: `${def_pr}`")
                    with c2:
                        q_add = st.number_input("الكمية", min_value=0, max_value=max(0, stock), value=0, key=f"p_qty_{model}")
                    with c3:
                        st.write("")
                        if st.button("➕ إضافة للسلة", key=f"p_btn_{model}"):
                            if q_add > 0:
                                if model in st.session_state.cart:
                                    st.session_state.cart[model]["count"] += q_add
                                else:
                                    st.session_state.cart[model] = {"count": q_add, "price_usd": def_pr, "type": "finished"}
                                st.success(f"تمت إضافة {q_add} من {model}")
                                st.rerun()
        else:
            for raw_name, stock in factory_data["inventory"].items():
                def_pr = prices_dict.get(raw_name, 0.0)
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**{raw_name}**")
                        st.caption(f"المتوفر: `{stock:,.2f}` | السعر: `${def_pr}`")
                    with c2:
                        q_add = st.number_input("الكمية", min_value=0.0, max_value=float(stock) if stock>0 else 0.0, value=0.0, step=1.0, key=f"r_qty_{raw_name}")
                    with c3:
                        st.write("")
                        if st.button("➕ إضافة للسلة", key=f"r_btn_{raw_name}"):
                            if q_add > 0:
                                if raw_name in st.session_state.cart:
                                    st.session_state.cart[raw_name]["count"] += q_add
                                else:
                                    st.session_state.cart[raw_name] = {"count": q_add, "price_usd": def_pr, "type": "raw"}
                                st.success(f"تمت إضافة {q_add} من {raw_name}")
                                st.rerun()

    with col_crt:
        st.subheader("🛍️ سلة الطلب الحالية")
        if not st.session_state.cart:
            st.info("السلة فارغة. اختر المواد من القائمة بجانبها.")
        else:
            cart_grand_total = 0.0
            items_to_del = []
            
            for item_name, details in st.session_state.cart.items():
                item_tot = details["count"] * details["price_usd"]
                cart_grand_total += item_tot
                
                with st.container(border=True):
                    st.markdown(f"**{item_name}**")
                    cc1, cc2 = st.columns([2, 1])
                    with cc1:
                        new_price = st.number_input("السعر ($)", value=float(details["price_usd"]), key=f"c_pr_{item_name}", step=5.0)
                        st.session_state.cart[item_name]["price_usd"] = new_price
                        st.text(f"الكمية: {details['count']} | الإجمالي: ${details['count'] * new_price:,.2f}")
                    with cc2:
                        st.write("")
                        if st.button("❌ حذف", key=f"del_{item_name}"):
                            items_to_del.append(item_name)
            
            for di in items_to_del:
                del st.session_state.cart[di]
                st.rerun()

            st.write("---")
            discount_usd = st.number_input("قيمة الخصم ($):", min_value=0.0, value=0.0, step=5.0)
            net_total_usd = max(0.0, cart_grand_total - discount_usd)
            
            st.markdown(f"### 💰 الصافي المطلوب: `${net_total_usd:,.2f}`")
            st.caption(f"بالدينار العراقي: `{net_total_usd * exchange_rate:,.0f}` د.ع")

            # حقل المبلغ المدفوع (مفتوح ليبين الدين المتبقي للوكيل أو الزبون)
            paid_amount_usd = st.number_input("المبلغ المدفوع فعلياً ($):", min_value=0.0, value=0.0, step=10.0)
            remaining_amount_usd = max(0.0, net_total_usd - paid_amount_usd)

            if remaining_amount_usd > 0:
                st.warning(f"⚠️ سيتم تسجيل مبلغ **${remaining_amount_usd:,.2f}** كدين ذمي مستحق على المشتري.")

            if st.button("🚀 إتمام عملية البيع وإصدار الفاتورة", type="primary", use_container_width=True):
                if not selected_buyer.strip():
                    st.error("❌ يرجى إدخال اسم المشتري أو اختيار وكيل صالح!")
                else:
                    stock_ok = True
                    for item_name, details in st.session_state.cart.items():
                        if details["type"] == "finished":
                            if details["count"] > factory_data["finished_goods"].get(item_name, 0):
                                stock_ok = False
                        else:
                            if details["count"] > factory_data["inventory"].get(item_name, 0.0):
                                stock_ok = False

                    if not stock_ok:
                        st.error("❌ الكمية المطلوبة تتجاوز المخزون المتوفر حالياً!")
                    else:
                        receipt_no = factory_data.get("receipt_counter", 1001)
                        final_items_list = []

                        for item_name, details in st.session_state.cart.items():
                            item_tot = details["count"] * details["price_usd"]
                            final_items_list.append({
                                "model": item_name,
                                "count": details["count"],
                                "price_usd": details["price_usd"],
                                "total_usd": item_tot
                            })
                            if details["type"] == "finished":
                                factory_data["finished_goods"][item_name] -= int(details["count"])
                            else:
                                factory_data["inventory"][item_name] -= details["count"]

                        # إذا كان وكيل معتمد، قم بتسجيل الدين في حسابه
                        if is_registered_agent and selected_buyer in factory_data["agents"]:
                            factory_data["agents"][selected_buyer]["balance"] += remaining_amount_usd

                        pdf_bytes = generate_receipt_pdf(
                            factory_name=current_factory_name,
                            customer_name=selected_buyer,
                            date_str=datetime.now().strftime("%Y-%m-%d"),
                            items_data=final_items_list,
                            grand_total_usd=cart_grand_total,
                            discount_usd=discount_usd,
                            net_total_usd=net_total_usd,
                            paid_amount_usd=paid_amount_usd,
                            remaining_amount_usd=remaining_amount_usd,
                            exchange_rate=exchange_rate,
                            receipt_no=receipt_no
                        )

                        factory_data["sales_history"].append({
                            "receipt_no": receipt_no,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "customer": selected_buyer,
                            "total_usd": net_total_usd,
                            "remaining_usd": remaining_amount_usd
                        })
                        factory_data["receipt_counter"] = receipt_no + 1
                        save_factory_data(factory_data)

                        st.success("✅ تمت عملية البيع بنجاح وتحديث الحسابات والمخزون!")
                        st.session_state.cart = {}

                        st.download_button(
                            label="📥 تحميل القائمة الرسمية (PDF)",
                            data=pdf_bytes,
                            file_name=f"قائمة_حساب_{receipt_no}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

# تبويب إدارة الوكلاء والحسابات
with tabs[1]:
    st.header("👥 إدارة الوكلاء والحسابات والديون الذمية")
    
    st.subheader("➕ إضافة وكيل جديد")
    with st.form("new_agent_form"):
        ag_name = st.text_input("اسم الوكيل / المحل:")
        ag_phone = st.text_input("رقم الهاتـف:")
        ag_addr = st.text_input("العنوان / المنطقة:")
        submit_ag = st.form_submit_button("حفظ الوكيل الجديد", type="primary")
        
        if submit_ag:
            if ag_name:
                if ag_name in factory_data["agents"]:
                    st.error("الوكيل موجود مسبقاً!")
                else:
                    factory_data["agents"][ag_name] = {"phone": ag_phone, "address": ag_addr, "balance": 0.0}
                    save_factory_data(factory_data)
                    st.success(f"✅ تمت إضافة الوكيل [{ag_name}] بنجاح!")
                    st.rerun()

    st.write("---")
    st.subheader("📋 قائمة الوكلاء وأرصدتهم الحالية")
    
    agents_data_rows = []
    for ag_key, ag_val in factory_data["agents"].items():
        agents_data_rows.append({
            "اسم الوكيل": ag_key,
            "الهاتف": ag_val.get("phone", ""),
            "العنوان": ag_val.get("address", ""),
            "الرصيد المتبقي (دينار ذمي $)": ag_val.get("balance", 0.0)
        })
    
    agents_df = pd.DataFrame(agents_data_rows)
    st.dataframe(agents_df, use_container_width=True)

    st.subheader("💵 تسديد دفعة من حساب وكيل")
    pay_agent = st.selectbox("اختر الوكيل لتسديد دفعة مالية:", list(factory_data["agents"].keys()), key="pay_ag_sel")
    current_bal = factory_data["agents"][pay_agent]["balance"]
    st.info(f"الرصيد الحالي المستحق على الوكيل: **${current_bal:,.2f}**")
    
    payment_amt = st.number_input("مبلغ التسديد ($):", min_value=0.0, value=0.0, step=10.0)
    if st.button("تأكيد التسديد وتخفيض الدين"):
        if payment_amt > 0:
            factory_data["agents"][pay_agent]["balance"] = max(0.0, current_bal - payment_amt)
            save_factory_data(factory_data)
            st.success(f"✅ تم تسديد مبلغ ${payment_amt:,.2f} بنجاح للوكيل [{pay_agent}]!")
            st.rerun()

# تبويب تسجيل إنتاج البرادات
with tabs[2]:
    st.header("🏭 تسجيل إنتاج برادات جديدة")
    model_list = list(factory_data["bom"].keys())
    
    prod_model = st.selectbox("اختر نموذج البراد المراد إنتاجه:", model_list)
    prod_count = st.number_input("العدد المصنوع:", min_value=1, value=1, step=1)

    if st.button("🚀 تأكيد الإنتاج وخصم المواد الخام أوتوماتيكياً", type="primary", use_container_width=True):
        required_bom = factory_data["bom"][prod_model]
        missing = []
        for raw, req in required_bom.items():
            needed = req * prod_count
            available = factory_data["inventory"].get(raw, 0.0)
            if available < needed:
                missing.append(f"- **{raw}**: المطلوب ({needed})، المتوفر ({available:,.2f})")

        if missing:
            st.error("❌ المواد الخام غير كافية لإتمام الإنتاج:")
            for m in missing:
                st.write(m)
        else:
            for raw, req in required_bom.items():
                factory_data["inventory"][raw] -= req * prod_count
            
            factory_data["finished_goods"][prod_model] = factory_data["finished_goods"].get(prod_model, 0) + prod_count
            factory_data["production_history"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "model": prod_model,
                "count": prod_count
            })
            save_factory_data(factory_data)
            st.success(f"✅ تم إنتاج ({prod_count}) من [{prod_model}] بنجاح وخصم المواد من المخزن!")

# تبويب المخزون
with tabs[3]:
    st.header("📦 إدارة المخزون والمواد الخام")
    
    st.subheader("🧊 البرادات الجاهزة بالمخزن")
    fg_df = pd.DataFrame(list(factory_data["finished_goods"].items()), columns=["نوع البراد", "العدد الجاهز للبيع"])
    st.dataframe(fg_df, use_container_width=True)

    st.subheader("🧱 المواد الخام المتوفرة")
    inv_df = pd.DataFrame(list(factory_data["inventory"].items()), columns=["المادة الخام", "الكمية المتوفرة"])
    edited_inv = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True)

    if st.button("💾 حفظ تعديلات المخزون", type="primary"):
        new_inv = {}
        for _, row in edited_inv.iterrows():
            if str(row["المادة الخام"]).strip():
                new_inv[str(row["المادة الخام"]).strip()] = float(row["الكمية المتوفرة"])
        factory_data["inventory"] = new_inv
        save_factory_data(factory_data)
        st.success("✅ تم تحديث المخزون بنجاح!")
        st.rerun()

# تبويب الأسعار
with tabs[4]:
    st.header("💲 الأسعار الثابتة للمنتجات والمواد")
    prices_df = pd.DataFrame(list(factory_data["prices"].items()), columns=["العنصر", "السعر الثابت ($)"])
    edited_prices = st.data_editor(prices_df, num_rows="dynamic", use_container_width=True)

    if st.button("💾 حفظ الأسعار", type="primary"):
        new_pr = {}
        for _, row in edited_prices.iterrows():
            if str(row["العنصر"]).strip():
                new_pr[str(row["العنصر"]).strip()] = float(row["السعر الثابت ($)"])
        factory_data["prices"] = new_pr
        save_factory_data(factory_data)
        st.success("✅ تم حفظ الأسعار بنجاح!")

# تبويب هيكل البرادات (BOM) - مصمم بدون جداول إكسل مع خيارات منسدلة واضحة
with tabs[5]:
    st.header("🛠️ إدارة مكونات البرادات (BOM)")
    
    # اختيار أو إضافة نموذج
    bom_models = list(factory_data["bom"].keys())
    selected_bom_model = st.selectbox("اختر نموذج البراد لتعديله أو إضافة مكونات له:", bom_models)

    st.write("---")
    st.subheader(f"⚙️ تعديل مكونات البراد: [{selected_bom_model}]")
    
    # عرض المكونات الحالية كقائمة تفاعلية وليست جدول إكسل
    current_bom = factory_data["bom"].get(selected_bom_model, {})
    
    with st.form(f"form_bom_{selected_bom_model}"):
        st.markdown("**حدد المواد الخام والكمية المطلوبة للبراد الواحد:**")
        updated_bom_dict = {}
        
        # قائمة بكل المواد الخام المتاحة بالمخزن لربطها بسهولة
        all_raw_materials = list(factory_data["inventory"].keys())
        
        # لعرض المواد الحالية أو إضافة مواد جديدة بسهولة عبر واجهة نظيفة
        col_r1, col_r2 = st.columns(2)
        
        # استخدام القوائم المنسدلة والعدد لتجنب الكتابة اليدوية وجداول الإكسل المعقدة
        selected_raws = st.multiselect(
            "اختر المواد الخام الداخلة في تركيب هذا البراد:",
            options=all_raw_materials,
            default=list(current_bom.keys())
        )
        
        quantities_dict = {}
        if selected_raws:
            st.write("حدد كمية كل مادة للبراد الواحد:")
            for raw in selected_raws:
                def_val = float(current_bom.get(raw, 1.0))
                quantities_dict[raw] = st.number_input(f"كمية ({raw}) للبراد الواحد:", min_value=0.01, value=def_val, step=0.25, key=f"qty_raw_{selected_bom_model}_{raw}")

        submit_bom = st.form_submit_button("💾 حفظ هيكل البراد", type="primary")
        
        if submit_bom:
            for raw in selected_raws:
                updated_bom_dict[raw] = quantities_dict[raw]
            factory_data["bom"][selected_bom_model] = updated_bom_dict
            save_factory_data(factory_data)
            st.success(f"✅ تم حفظ مكونات نموذج [{selected_bom_model}] بنجاح!")
            st.rerun()

    st.write("---")
    st.subheader("➕ إضافة نموذج براد جديد كلياً")
    with st.form("new_model_form"):
        new_model_name = st.text_input("اسم نموذج البراد الجديد:")
        sub_new_model = st.form_submit_button("إضافة النموذج")
        if sub_new_model:
            if new_model_name:
                if new_model_name in factory_data["bom"]:
                    st.error("النموذج موجود مسبقاً!")
                else:
                    factory_data["bom"][new_model_name] = {}
                    factory_data["finished_goods"][new_model_name] = 0
                    factory_data["prices"][new_model_name] = 200.0
                    save_factory_data(factory_data)
                    st.success(f"✅ تمت إضافة النموذج [{new_model_name}] بنجاح! يمكنك الآن تعديل مكوناته بالأعلى.")
                    st.rerun()

# تبويب التقارير
with tabs[6]:
    st.header("📊 سجل المبيعات والعمليات")
    sales_hist = pd.DataFrame(factory_data.get("sales_history", []))
    if sales_hist.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        st.dataframe(sales_hist, use_container_width=True)

# تبويب الإعدادات
with tabs[7]:
    st.header("⚙️ إعدادات النظام والأمان")
    new_user = st.text_input("اسم المستخدم الجديد:", value=factory_data["info"].get("admin_user", "admin"))
    new_pass = st.text_input("كلمة المرور الجديدة:", type="password")

    if st.button("تحديث بيانات الدخول"):
        if new_user and new_pass:
            factory_data["info"]["admin_user"] = new_user
            factory_data["info"]["admin_pass"] = new_pass
            save_factory_data(factory_data)
            st.success("✅ تم تحديث بيانات الدخول بنجاح!")
