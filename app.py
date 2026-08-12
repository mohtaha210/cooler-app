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

DATA_FILE = "single_factory_data.json"

# --- 0. دالة التفقيط باللغة العربية ---
def number_to_arabic_words(num):
    if num == 0:
        return "صفر"
    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
    teens = ["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    tens_arr = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
    hundreds = ["", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]
    
    def convert_group(n):
        res = []
        h = n // 100
        rem = n % 100
        if h > 0:
            res.append(hundreds[h])
        if rem > 0:
            if rem < 10:
                res.append(ones[rem])
            elif rem < 20:
                res.append(teens[rem - 10])
            else:
                t = rem // 10
                u = rem % 10
                if u > 0:
                    res.append(ones[u] + " و " + tens_arr[t])
                else:
                    res.append(tens_arr[t])
        return " و ".join(res)
    
    parts = []
    b = num // 1000000000
    if b > 0:
        if b == 1: parts.append("مليار")
        elif b == 2: parts.append("ملياران")
        elif 3 <= b <= 10: parts.append(convert_group(b) + " مليارات")
        else: parts.append(convert_group(b) + " مليار")
    num %= 1000000000
    
    m = num // 1000000
    if m > 0:
        if m == 1: parts.append("مليون")
        elif m == 2: parts.append("مليونان")
        elif 3 <= m <= 10: parts.append(convert_group(m) + " ملايين")
        else: parts.append(convert_group(m) + " مليون")
    num %= 1000000
    
    k = num // 1000
    if k > 0:
        if k == 1: parts.append("ألف")
        elif k == 2: parts.append("ألفان")
        elif 3 <= k <= 10: parts.append(convert_group(k) + " آلاف")
        else: parts.append(convert_group(k) + " ألف")
    num %= 1000
    
    if num > 0:
        parts.append(convert_group(num))
    return " و ".join(parts).strip()

# --- 1. هيكل البيانات لمعمل الرافدين ---
def get_default_factory_data():
    return {
        "info": {"factory_name": "معمل الرافدين للبرادات"},
        "users": {
            "admin": {
                "password": "123",
                "role": "admin",
                "name": "المدير العام",
            }
        },
        "inventory": {
            "الحنفية": 50.0,
            "البانكة": 20.0,
            "الماطور": 20.0,
            "التوماتيك": 20.0,
            "الطواف": 20.0,
            "الراديتر": 20.0,
            "زواية القاعدة": 80.0,
            "المنيوم القاعدة 1.35m": 20.0,
            "الجكنة": 20.0,
            "واشر حديد": 50.0,
            "واشر بلاستك": 50.0,
            "زبانة": 20.0,
            "كبلري 1.7m": 20.0,
            "كويل": 20.0,
            "بوري ربع 1.5m": 20.0,
            "طبقة وربع بليت": 30.0,
        },
        "finished_goods": {
            "براد حنفية واحدة": 10,
            "براد حنفيتين": 10,
        },
        "agents": {},
        "bom": {
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
        },
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": [],
    }

def load_factory_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "users" not in data:
                data["users"] = {"admin": {"password": "123", "role": "admin", "name": "المدير العام"}}
            if "info" in data:
                data["info"]["factory_name"] = "معمل الرافدين للبرادات"
            return data
        except Exception:
            return get_default_factory_data()
    else:
        d = get_default_factory_data()
        save_factory_data(d)
        return d

def save_factory_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. دوال الطباعة والتصدير PDF (مطابقة تماماً للصورة بتوزيع الأعمدة والعناوين والتوقيع السفلي) ---
def ar(text):
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))

@st.cache_resource
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
            res = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(res.content)
        except Exception:
            pass
    return font_path

def generate_new_account_statement_pdf(
    customer_name,
    customer_type,
    date_str,
    items_data,
    grand_total_usd,
    paid_amount_usd,
    remaining_amount_usd,
    exchange_rate,
    invoice_no,
    payment_method_str
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    logo_path = "rafidain_logo.jpg"
    try:
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=135, y=10, w=55)
            pdf.set_y(32)
        else:
            pdf.set_y(12)
    except Exception:
        pdf.set_y(12)

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)
        pdf.set_font("Amiri", "", 13)
    else:
        pdf.set_font("Arial", "B", 12)

    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, ar("معمل الرافدين للبرادات"), ln=True, align="C")
    pdf.cell(0, 6, ar("قائمة حساب مبيعات (فاتورة)"), ln=True, align="C")
    pdf.ln(2)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.set_line_width(0.3)
    pdf.cell(93, 6, ar(f"رقم القائمة: {invoice_no}"), border=1, align="R")
    pdf.cell(93, 6, ar(f"التاريخ: {date_str}"), border=1, align="R", ln=True)
    pdf.cell(93, 6, ar(f"اسم العميل / الزبون: {customer_name}"), border=1, align="R")
    pdf.cell(93, 6, ar(f"طريقة الدفع: {payment_method_str}"), border=1, align="R", ln=True)
    pdf.cell(186, 6, ar(f"سعر الصرف المعتمد: {exchange_rate:,.0f} د.ع"), border=1, align="R", ln=True)
    pdf.ln(2)

    if items_data:
        # ترتيب الأعمدة تماماً مثل الصورة: [الصنف، الإجمالي د.ع، الكمية، السعر ($)، الإجمالي ($)] بمعكوس اليمين لليسار أو الترتيب المظبوط
        col_widths = [46, 45, 25, 40, 30]
        headers = [ar("الصنف"), ar("الإجمالي (د.ع)"), ar("الكمية"), ar("السعر ($)"), ar("الإجمالي ($)")]
        for i, h in enumerate(headers):
            is_shaded = i in [0, 2, 4] # الأعمدة المظللة مطابقة للصورة
            if is_shaded:
                pdf.set_fill_color(210, 225, 245)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_widths[i], 7, h, border=1, align="C", fill=True)
        pdf.ln()

        for item in items_data:
            tot_iqd = item['total_usd'] * exchange_rate
            row_cells = [
                (ar(item["model"]), True),                 # الصنف (مظلل)
                (f"{tot_iqd:,.0f}", False),                # الإجمالي د.ع (أبيض)
                (str(item["count"]), False),              # الكمية (أبيض)
                (f"${item['price_usd']:,.2f}", False),     # السعر $ (أبيض)
                (f"${item['total_usd']:,.2f}", True)       # الإجمالي $ (مظلل)
            ]
            for j, (val, shaded) in enumerate(row_cells):
                if shaded:
                    pdf.set_fill_color(210, 225, 245)
                else:
                    pdf.set_fill_color(255, 255, 255)
                pdf.cell(col_widths[j], 6, val, border=1, align="C", fill=True)
            pdf.ln()

    gt_iqd = int(round(grand_total_usd * exchange_rate))
    pd_iqd = int(round(paid_amount_usd * exchange_rate))
    rm_iqd = int(round(remaining_amount_usd * exchange_rate))

    total_in_words = f"المبلغ الإجمالي وقدره: {number_to_arabic_words(gt_iqd)} دينار عراقي فقط لا غير"
    pdf.set_fill_color(210, 225, 245)
    pdf.cell(186, 6, ar(total_in_words), border=1, align="R", fill=True, ln=True)

    pdf.set_fill_color(255, 255, 255)
    pdf.cell(93, 6, ar(f"المبلغ المدفوع: ${paid_amount_usd:,.2f} / {pd_iqd:,} د.ع"), border=1, align="R", fill=True)
    pdf.cell(93, 6, ar(f"المبلغ الإجمالي: ${grand_total_usd:,.2f} / {gt_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)

    pdf.set_fill_color(210, 225, 245)
    pdf.cell(186, 6, ar(f"المبلغ المتبقي (الذمة المالية): ${remaining_amount_usd:,.2f} / {rm_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)
    
    pdf.ln(4)
    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.cell(186, 6, ar("توقيع وختم البائع / المستلم:"), ln=True, align="R")
    sign_box_y = pdf.get_y()
    pdf.rect(12, sign_box_y, 186, 25)  

    return bytes(pdf.output())

def generate_payment_pdf(
    agent_name,
    date_str,
    amount_usd,
    remaining_debt_usd,
    old_debt_usd,
    exchange_rate,
    receipt_no,
    note=""
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    logo_path = "rafidain_logo.jpg"
    try:
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=135, y=10, w=55)
            pdf.set_y(32)
        else:
            pdf.set_y(12)
    except Exception:
        pdf.set_y(12)

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)
        pdf.set_font("Amiri", "", 13)
    else:
        pdf.set_font("Arial", "B", 12)

    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, ar("معمل الرافدين للبرادات"), ln=True, align="C")
    pdf.cell(0, 6, ar("سند قبض"), ln=True, align="C")
    pdf.ln(2)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.set_line_width(0.3)
    pdf.cell(93, 6, ar(f"رقم المستند: {receipt_no}"), border=1, align="R")
    pdf.cell(93, 6, ar(f"التاريخ: {date_str}"), border=1, align="R", ln=True)
    pdf.cell(186, 6, ar(f"استلمت من السيد / {agent_name}"), border=1, align="R", ln=True)

    amount_iqd = int(round(amount_usd * exchange_rate))
    amount_in_words = f"مبلغ وقدره: {number_to_arabic_words(amount_iqd)} دينار عراقي فقط لا غير"
    
    pdf.set_fill_color(210, 225, 245)
    pdf.cell(186, 6, ar(amount_in_words), border=1, align="R", fill=True, ln=True)

    paid_iqd_val = int(round(amount_usd * exchange_rate))
    pdf.cell(93, 6, ar(f"سعر الصرف: {exchange_rate:,.0f} د.ع"), border=1, align="R", fill=True)
    pdf.cell(93, 6, ar(f"المبلغ المدفوع: ${amount_usd:,.2f} / {paid_iqd_val:,} د.ع"), border=1, align="R", fill=True, ln=True)

    note_text = f"الملاحظات: {note}" if note else "الملاحظات: -"
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(186, 6, ar(note_text), border=1, align="R", ln=True)

    rem_iqd = int(round(remaining_debt_usd * exchange_rate))
    old_iqd = int(round(old_debt_usd * exchange_rate))
    
    pdf.set_fill_color(210, 225, 245)
    pdf.cell(186, 6, ar(f"الرصيد السابق: ${old_debt_usd:,.2f} / {old_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)
    pdf.cell(186, 6, ar(f"الرصيد بعد التسديد: ${remaining_debt_usd:,.2f} / {rem_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)
    
    pdf.ln(4)
    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.cell(186, 6, ar("توقيع وختم القابض:"), ln=True, align="R")
    sign_box_y = pdf.get_y()
    pdf.rect(12, sign_box_y, 186, 25)  
    
    return bytes(pdf.output())

# --- 3. إعداد الصفحة والجلسة ---
st.set_page_config(
    page_title="معمل الرافدين للبرادات",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

factory_data = load_factory_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_fullname = ""

# --- شاشة تسجيل الدخول ---
if not st.session_state.authenticated:
    st.title("❄️ تسجيل الدخول - معمل الرافدين للبرادات")
    st.write("مرحباً بك في النظام الموحد لإدارة المعمل.")
    
    username_input = st.text_input("اسم المستخدم:")
    password_input = st.text_input("كلمة المرور:", type="password")

    if st.button("تسجيل الدخول", type="primary", use_container_width=True):
        users_dict = factory_data.get("users", {})
        if username_input in users_dict and users_dict[username_input]["password"] == password_input:
            st.session_state.authenticated = True
            st.session_state.username = username_input
            st.session_state.role = users_dict[username_input]["role"]
            st.session_state.user_fullname = users_dict[username_input]["name"]
            st.success("تم تسجيل الدخول بنجاح!")
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()

# --- الواجهة الرئيسية والشريط العلوي ---
st.title(f"❄️ {factory_data['info']['factory_name']}")
col_u1, col_u2 = st.columns([3, 1])
with col_u1:
    role_badge = "👑 مدير عام" if st.session_state.role == "admin" else "👷 موظف"
    st.info(f"المستخدم الحالي: **{st.session_state.user_fullname}** | {role_badge}")
with col_u2:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

st.write("---")

# --- التبويبات الرئيسية ---
if st.session_state.role == "admin":
    tabs = st.tabs([
        "📊 التقارير الشاملة",
        "🤝 إدارة الوكلاء والديون",
        "🛒 نافذة البيع المبسطة",
        "🏭 تسجيل إنتاج براد",
        "📦 إدارة المخزون",
        "👥 الحسابات والموظفين",
        "⚙️ إعدادات الحساب",
        "➕ إضافة مادة خام",
        "🛠️ أنواع البرادات (BOM)",
        "⚠️ فورمات كامل",
    ])
else:
    tabs = st.tabs([
        "🛒 نافذة البيع المبسطة",
        "🤝 الوكلاء والديون",
        "🏭 تسجيل إنتاج براد",
        "📦 المخزون الحالي",
        "⚙️ إعدادات الحساب",
    ])

# --- 1. التقارير الشاملة (مدير فقط) ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.header("📊 التقارير الشاملة والإحصائيات")
        today_str = datetime.now().strftime("%Y-%m-%d")
        sales_history = factory_data.get("sales_history", [])
        
        today_rev = sum(s.get("total_usd", 0) for s in sales_history if s.get("date") == today_str)
        total_debts = sum(ag.get("debt_usd", 0) for ag in factory_data["agents"].values() if isinstance(ag, dict))

        c1, c2, c3 = st.columns(3)
        c1.metric("إيرادات مبيعات اليوم", f"${today_rev:,.2f}")
        c2.metric("إجمالي ديون الذمم", f"${total_debts:,.2f}")
        c3.metric("إجمالي عمليات البيع", f"{len(sales_history)} عملية")

        st.write("---")
        st.subheader("🧊 المخزون الجاهز")
        st.dataframe(pd.DataFrame(list(factory_data["finished_goods"].items()), columns=["البراد", "العدد"]), use_container_width=True)

# --- 2. إدارة الوكلاء والديون ---
tab_ag_idx = 1 if st.session_state.role == "admin" else 1
with tabs[tab_ag_idx]:
    st.header("🤝 إدارة الوكلاء وتسديد الديون والذمم")
    sub_ag1, sub_ag2, sub_ag3 = st.tabs(["➕ إضافة وكيل جديد", "💵 تسديد سند قبض", "📜 كشف الحساب"])

    with sub_ag1:
        st.subheader("إضافة وكيل أو زبون ذمم جديد")
        ag_name = st.text_input("اسم الوكيل / الزبون:", key="new_agent_name_input")
        ag_phone = st.text_input("رقم الهاتف:", key="new_agent_phone_input")
        ag_init_debt = st.number_input("الرصيد / الدين السابق ($):", min_value=0.0, value=0.0, step=50.0, key="new_agent_debt_input")
        
        if st.button("➕ تسجيل الوكيل", type="primary", use_container_width=True, key="new_agent_submit_btn"):
            if not ag_name.strip():
                st.error("يرجى إدخال اسم الوكيل.")
            elif ag_name in factory_data["agents"]:
                st.error("هذا الوكيل مسجل مسبقاً!")
            else:
                factory_data["agents"][ag_name] = {
                    "phone": ag_phone,
                    "debt_usd": ag_init_debt,
                    "transactions": []
                }
                if ag_init_debt > 0:
                    factory_data["agents"][ag_name]["transactions"].append({
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "دين سابق",
                        "amount_usd": ag_init_debt,
                        "balance_usd": ag_init_debt,
                        "note": "رصيد افتتاحى"
                    })
                save_factory_data(factory_data)
                st.success(f"✅ تم إضافة الوكيل [{ag_name}] بنجاح!")
                st.rerun()

    with sub_ag2:
        st.subheader("تسديد دفعة نقدية (إصدار سند قبض)")
        agents_list = list(factory_data["agents"].keys())
        if not agents_list:
            st.info("لا توجد حسابات وكلاء مسجلة حالياً.")
        else:
            sel_agent = st.selectbox("اختر الوكيل / الزبون:", agents_list, key="payment_agent_selectbox")
            cur_debt = factory_data["agents"][sel_agent].get("debt_usd", 0.0)
            st.warning(f"الذمة المالية الحالية على [{sel_agent}]: **${cur_debt:,.2f}**")

            pay_amt = st.number_input("المبلغ المدفوع ($):", min_value=0.01, value=100.0, step=25.0, key="payment_amount_input")
            ex_rate = st.number_input("سعر صرف الدولار (د.ع):", min_value=1.0, value=1500.0, step=25.0, key="payment_exchange_rate_input")
            pay_note = st.text_input("ملاحظات السند:", value="تسديد نقدآ", key="payment_note_input")

            if st.button("💵 تأكيد القبض وطباعة السند", type="primary", use_container_width=True, key="payment_submit_btn"):
                new_debt = cur_debt - pay_amt
                factory_data["agents"][sel_agent]["debt_usd"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)
                factory_data["receipt_counter"] = receipt_no + 1

                factory_data["agents"][sel_agent].setdefault("transactions", []).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "تسديد",
                    "amount_usd": -pay_amt,
                    "balance_usd": new_debt,
                    "note": f"سند قبض #{receipt_no}"
                })
                save_factory_data(factory_data)

                pdf_bytes = generate_payment_pdf(
                    agent_name=sel_agent,
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    amount_usd=pay_amt,
                    remaining_debt_usd=new_debt,
                    old_debt_usd=cur_debt,
                    exchange_rate=ex_rate,
                    receipt_no=receipt_no,
                    note=pay_note
                )
                st.success("✅ تمت العملية بنجاح!")
                st.download_button(
                    label="📥 تنزيل سند القبض (PDF)",
                    data=pdf_bytes,
                    file_name=f"سند_قبض_{receipt_no}_{sel_agent}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_payment_pdf_btn"
                )

    with sub_ag3:
        st.subheader("كشف الحساب التفصيلي")
        if not agents_list:
            st.info("لا توجد بيانات وكلاء.")
        else:
            v_ag = st.selectbox("اختر الوكيل للعرض:", agents_list, key="view_ag_box")
            ag_data = factory_data["agents"][v_ag]
            st.metric("صافي الذمة المالية", f"${ag_data.get('debt_usd', 0.0):,.2f}")
            
            trans = ag_data.get("transactions", [])
            if trans:
                st.dataframe(pd.DataFrame(trans), use_container_width=True)
            else:
                st.write("لا توجد حركات مسجلة لهذا الحساب.")
            
            with st.popover("⚠️ حذف هذا الوكيل نهائياً"):
                st.warning(f"هل أنت متأكد من حذف الوكيل [{v_ag}]؟ لا يمكن التراجع عن هذا الإجراء.")
                confirm_del_ag = st.text_input("اكتب كلمة (حذف) للتأكيد:", key="confirm_del_ag_input")
                if st.button("تأكيد الحذف النهائي", type="primary", key="confirm_del_ag_btn"):
                    if confirm_del_ag == "حذف":
                        del factory_data["agents"][v_ag]
                        save_factory_data(factory_data)
                        st.success("تم حذف الوكيل بنجاح.")
                        st.rerun()
                    else:
                        st.error("يرجى كتابة كلمة (حذف) بشكل صحيح للتأكيد.")

# --- 3. نافذة البيع المبسطة ---
tab_sale_idx = 2 if st.session_state.role == "admin" else 0
with tabs[tab_sale_idx]:
    st.header("🛒 نافذة البيع المبسطة")
    st.write("قم بإتمام عمليات البيع بنظام (نقداً، بالأجل، أو بالأقساط) لكل من الوكلاء والزبائن المباشرين بكل سهولة.")

    buyer_category = st.radio("تصنيف المشتري:", ["زبون مباشر", "وكيل مسجل"], horizontal=True, key="buyer_category_radio")
    
    if buyer_category == "وكيل مسجل":
        agents_list = list(factory_data["agents"].keys())
        if not agents_list:
            st.warning("⚠️ لا يوجد وكلاء مسجلون! قم بإضافتهم من تبويب الوكلاء.")
            customer_display_name = ""
            selected_agent_key = None
        else:
            selected_agent_key = st.selectbox("اختر الوكيل:", agents_list, key="sale_agent_selectbox")
            customer_display_name = selected_agent_key
    else:
        customer_display_name = st.text_input("اسم الزبون المباشر:", value="زبون نقدي", key="direct_customer_name_input")
        selected_agent_key = None

    payment_system = st.selectbox(
        "طريقة البيع وسداد المبلغ:",
        ["بيع نقدي بالكامل", "بيع بالأجل (على الذمة)", "بيع بالتقساط (دفعة مقدمة + أقساط متبقية)"],
        key="payment_system_selectbox"
    )

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        purchase_date = st.date_input("تاريخ العملية:", value=datetime.now(), key="sale_date_input")
    with col_s2:
        exchange_rate = st.number_input("سعر صرف الدولار (د.ع):", min_value=1.0, value=1500.0, step=25.0, key="sale_exchange_rate_input")

    st.write("---")
    st.subheader("📦 اختيار المنتجات والكميات:")
    
    bom_models = list(factory_data["bom"].keys())
    selected_items_list = []
    total_invoice_usd = 0.0
    total_units_count = 0
    stock_shortage = False

    for model_name in bom_models:
        available_qty = factory_data["finished_goods"].get(model_name, 0)
        c_m1, c_m2, c_m3 = st.columns([2, 1, 1])
        with c_m1:
            st.write(f"**{model_name}** (المتوفر بالمخزن: `{available_qty}`)")
        with c_m2:
            qty_bought = st.number_input("الكمية:", min_value=0, max_value=max(0, available_qty), value=0, key=f"simp_qty_{model_name}")
        with c_m3:
            unit_price_usd = st.number_input("السعر ($):", min_value=0.0, value=0.0, step=10.0, key=f"simp_pr_{model_name}")

        if qty_bought > available_qty:
            stock_shortage = True
        if qty_bought > 0:
            item_tot = qty_bought * unit_price_usd
            total_invoice_usd += item_tot
            total_units_count += qty_bought
            selected_items_list.append({
                "model": model_name,
                "count": qty_bought,
                "price_usd": unit_price_usd,
                "total_usd": item_tot
            })

    st.markdown(f"### 💰 إجمالي الفاتورة: `${total_invoice_usd:,.2f}` (`{total_invoice_usd * exchange_rate:,.0f}` د.ع)")

    paid_now_usd = 0.0
    remaining_debt_usd = 0.0
    installments_note = ""

    if payment_system == "بيع نقدي بالكامل":
        paid_now_usd = total_invoice_usd
        remaining_debt_usd = 0.0
        payment_desc_str = "نقدي بالكامل"
    elif payment_system == "بيع بالأجل (على الذمة)":
        paid_now_usd = 0.0
        remaining_debt_usd = total_invoice_usd
        payment_desc_str = "بيع بالأجل"
    else:
        paid_now_usd = st.number_input("المقدمة المدفوعة الآن ($):", min_value=0.0, max_value=float(total_invoice_usd), value=0.0, step=25.0, key="sale_paid_now_input")
        remaining_debt_usd = total_invoice_usd - paid_now_usd
        installments_note = st.text_input("تفاصيل جدول الأقساط:", value="أقساط شهرية متفق عليها", key="sale_installments_note_input")
        payment_desc_str = f"تقساط (مقدمة: ${paid_now_usd:,.2f})"

    if st.button("🚀 إتمام عملية البيع وتوليد قائمة الحساب", type="primary", use_container_width=True, key="complete_sale_btn"):
        if stock_shortage:
            st.error("❌ الكمية المطلوبة تتجاوز المخزون المتوفر!")
        elif not customer_display_name.strip():
            st.error("يرجى إدخال اسم العميل.")
        elif not selected_items_list:
            st.error("يرجى اختيار صنف واحد على الأقل.")
        else:
            invoice_seq = factory_data.get("receipt_counter", 1001)
            factory_data["receipt_counter"] = invoice_seq + 1

            for item in selected_items_list:
                factory_data["finished_goods"][item["model"]] -= item["count"]

            if remaining_debt_usd > 0:
                if selected_agent_key and selected_agent_key in factory_data["agents"]:
                    target_ag = selected_agent_key
                else:
                    target_ag = customer_display_name
                    if target_ag not in factory_data["agents"]:
                        factory_data["agents"][target_ag] = {"phone": "مباشر", "debt_usd": 0.0, "transactions": []}
                
                old_d = factory_data["agents"][target_ag].get("debt_usd", 0.0)
                new_d = old_d + remaining_debt_usd
                factory_data["agents"][target_ag]["debt_usd"] = new_d
                factory_data["agents"][target_ag]["transactions"].append({
                    "date": purchase_date.strftime("%Y-%m-%d"),
                    "type": payment_system,
                    "amount_usd": remaining_debt_usd,
                    "balance_usd": new_d,
                    "note": f"قائمة حساب #{invoice_seq} - {installments_note}"
                })

            factory_data["sales_history"].append({
                "invoice_no": invoice_seq,
                "date": purchase_date.strftime("%Y-%m-%d"),
                "customer": customer_display_name,
                "total_usd": total_invoice_usd,
                "payment_type": payment_desc_str
            })
            save_factory_data(factory_data)

            pdf_bytes = generate_new_account_statement_pdf(
                customer_name=customer_display_name,
                customer_type=buyer_category,
                date_str=purchase_date.strftime("%Y-%m-%d"),
                items_data=selected_items_list,
                grand_total_usd=total_invoice_usd,
                paid_amount_usd=paid_now_usd,
                remaining_amount_usd=remaining_debt_usd,
                exchange_rate=exchange_rate,
                invoice_no=invoice_seq,
                payment_method_str=payment_desc_str
            )

            st.success("✅ تمت العملية بنجاح!")
            st.download_button(
                label="📥 تنزيل قائمة الحساب (PDF)",
                data=pdf_bytes,
                file_name=f"قائمة_حساب_{invoice_seq}_{customer_display_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_sale_pdf_btn"
            )

# --- 4. تسجيل الإنتاج ---
tab_prod_idx = 3 if st.session_state.role == "admin" else 2
with tabs[tab_prod_idx]:
    st.header("🏭 تسجيل إنتاج براد جديد")
    models = list(factory_data["bom"].keys())
    if models:
        prod_model = st.selectbox("اختر البراد المراد إنتاجه:", models, key="prod_mod_box")
        prod_qty = st.number_input("العدد المصنوع:", min_value=1, value=1, step=1, key="prod_qty_box")

        if st.button("🚀 خصم المواد الخام وإضافة البرادات", type="primary", use_container_width=True, key="prod_submit_btn"):
            bom_req = factory_data["bom"][prod_model]
            missing = []
            for mat, req_val in bom_req.items():
                needed = req_val * prod_qty
                avail = factory_data["inventory"].get(mat, 0.0)
                if avail < needed:
                    missing.append(f"- {mat}: المطلوب ({needed})، المتوفر ({avail})")

            if missing:
                st.error("❌ المواد الخام غير كافية بالمخزن:")
                for m in missing:
                    st.write(m)
            else:
                for mat, req_val in bom_req.items():
                    factory_data["inventory"][mat] -= req_val * prod_qty
                factory_data["finished_goods"][prod_model] += prod_qty
                save_factory_data(factory_data)
                st.success(f"✅ تم إنتاج ({prod_qty}) من [{prod_model}] بنجاح!")
                st.rerun()

# --- 5. إدارة المخزون ---
tab_inv_idx = 4 if st.session_state.role == "admin" else 3
with tabs[tab_inv_idx]:
    if st.session_state.role == "admin":
        st.header("📦 إدارة المخزون الحالي")
        st.subheader("🧊 البرادات الجاهزة")
        st.dataframe(pd.DataFrame(list(factory_data["finished_goods"].items()), columns=["البراد", "الكمية"]), use_container_width=True)

        st.subheader("🧱 المواد الأولية الخام")
        inv_df = pd.DataFrame(list(factory_data["inventory"].items()), columns=["المادة الخام", "الكمية"])
        edited_inv = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, key="inventory_data_editor")
        if st.button("💾 حفظ تعديلات المخزون الخام", use_container_width=True, key="save_inventory_btn"):
            new_i = {}
            for _, r in edited_inv.iterrows():
                if r["المادة الخام"]:
                    new_i[r["المادة الخام"]] = float(r["الكمية"])
            factory_data["inventory"] = new_i
            save_factory_data(factory_data)
            st.success("✅ تم التحديث بنجاح!")
            st.rerun()
    else:
        st.header("📦 عرض المخزون")
        st.dataframe(pd.DataFrame(list(factory_data["finished_goods"].items()), columns=["البراد", "الكمية"]), use_container_width=True)
        st.dataframe(pd.DataFrame(list(factory_data["inventory"].items()), columns=["المادة الخام", "الكمية"]), use_container_width=True)

# --- الحسابات والموظفين (مدير فقط) ---
if st.session_state.role == "admin":
    with tabs[5]:
        st.header("👥 إدارة الحسابات والموظفين")
        st.subheader("إضافة حساب موظف جديد")
        u_name = st.text_input("اسم المستخدم:", key="new_user_name_input")
        u_full = st.text_input("الاسم الكامل:", key="new_user_full_input")
        u_pass = st.text_input("كلمة المرور:", type="password", key="new_user_pass_input")
        u_role = st.selectbox("الصلاحية:", ["staff", "admin"], format_func=lambda x: "مشرف / مدير" if x == "admin" else "موظف عادي", key="new_user_role_selectbox")

        if st.button("➕ إنشاء الحساب", type="primary", use_container_width=True, key="new_user_submit_btn"):
            if u_name and u_pass:
                if u_name in factory_data["users"]:
                    st.error("اسم المستخدم موجود مسبقاً!")
                else:
                    factory_data["users"][u_name] = {"password": u_pass, "role": u_role, "name": u_full}
                    save_factory_data(factory_data)
                    st.success("✅ تم إضافة الحساب بنجاح!")
                    st.rerun()

# --- إعدادات الحساب الشخصي ---
tab_set_idx = 6 if st.session_state.role == "admin" else 4
with tabs[tab_set_idx]:
    st.header("⚙️ إعدادات الحساب الشخصي")
    st.subheader("تغيير كلمة المرور أو اسم المستخدم")
    
    current_username = st.session_state.username
    curr_user_obj = factory_data["users"].get(current_username, {})

    new_username_input = st.text_input("اسم المستخدم الجديد:", value=current_username, key="settings_new_username_input")
    new_password_input = st.text_input("كلمة المرور الجديدة:", type="password", key="settings_new_password_input")
    confirm_password_input = st.text_input("تأكيد كلمة المرور الجديدة:", type="password", key="settings_confirm_password_input")

    if st.button("💾 حفظ التعديلات الشخصية", type="primary", use_container_width=True, key="settings_save_btn"):
        if not new_username_input.strip():
            st.error("اسم المستخدم لا يمكن أن يكون فارغاً.")
        elif new_password_input and new_password_input != confirm_password_input:
            st.error("كلمتا المرور غير متطابقتين!")
        else:
            if new_username_input != current_username:
                if new_username_input in factory_data["users"]:
                    st.error("اسم المستخدم هذا مستخدم بالفعل من قبل شخص آخر!")
                    st.stop()
                factory_data["users"][new_username_input] = factory_data["users"].pop(current_username)
                st.session_state.username = new_username_input
            
            if new_password_input:
                factory_data["users"][st.session_state.username]["password"] = new_password_input
            
            save_factory_data(factory_data)
            st.success("✅ تم تحديث بيانات الحساب بنجاح! يرجى إعادة تسجيل الدخول إذا قمت بتغيير اسم المستخدم.")

# --- تبويبات إضافية للمدير ---
if st.session_state.role == "admin":
    with tabs[7]:
        st.header("إضافة مادة خام جديدة")
        nm = st.text_input("اسم المادة:", key="add_raw_name_input")
        nq = st.number_input("الكمية الأولية:", min_value=0.0, value=0.0, key="add_raw_qty_input")
        if st.button("➕ إضافة المادة", type="primary", use_container_width=True, key="add_raw_submit_btn"):
            if nm:
                factory_data["inventory"][nm] = nq
                save_factory_data(factory_data)
                st.success("✅ تمت الإضافة!")
                st.rerun()

    with tabs[8]:
        st.header("🛠️ إدارة أنواع البرادات (BOM)")
        st.write("تعريف المواد الداخلة في تركيب كل نموذج براد.")
        mod_name = st.text_input("اسم النموذج الجديد:", key="bom_new_model_name_input")
        sel_ingredients = {}
        for mat_k in factory_data["inventory"].keys():
            chk = st.checkbox(f"يدخل فيه: {mat_k}", key=f"bom_chk_{mat_k}")
            if chk:
                q_val = st.number_input(f"الكمية من [{mat_k}]:", min_value=0.1, value=1.0, key=f"bom_q_{mat_k}")
                sel_ingredients[mat_k] = q_val
        if st.button("🛠️ حفظ نموذج البراد", use_container_width=True, key="bom_save_model_btn"):
            if mod_name and sel_ingredients:
                factory_data["bom"][mod_name] = sel_ingredients
                if mod_name not in factory_data["finished_goods"]:
                    factory_data["finished_goods"][mod_name] = 0
                save_factory_data(factory_data)
                st.success("✅ تم الحفظ بنجاح!")
                st.rerun()

    with tabs[9]:
        st.header("⚠️ فورمات كامل للنظام")
        st.error("تحذير صارم: سيؤدي هذا لتصفير وحذف جميع البيانات!")
        conf_word = st.text_input("اكتب كلمة (DELETE) للتأكيد:", key="format_del_word")
        if st.button("🔥 تنفيذ الفورمات الكامل", type="primary", use_container_width=True, key="format_submit_btn"):
            if conf_word == "DELETE":
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
                st.session_state.clear()
                st.success("✅ تم فورمات النظام وإعادة تهيئته بنجاح.")
                st.rerun()
            else:
                st.error("يجب كتابة كلمة (DELETE) بدقة لتأكيد العملية.")
