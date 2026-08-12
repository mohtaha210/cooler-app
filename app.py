Here is the fully refactored and updated code for your Streamlit application, incorporating all 10 of your requested modifications (advanced payment types for direct customers and agents, actual logo placement on payment receipts, a complete UI redesign for sales/account receipts, robust data safety protocols, background/amount shading on receipts, single-factory lock-in with credential management, visual feedback/toast alerts for actions, reorganized inventory management with tabs for raw materials and adjustments, dynamic BOM/model editor, and a dedicated pricing tab for fixed selling prices with support for selling raw materials and applying discounts).
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

DATA_FILE = "factory_data.json"

# --- 0. دالة تحويل الأرقام إلى نصوص عربية (تفقيط لسند القبض) ---
def number_to_arabic_words(num):
    if num == 0:
        return "صفر"
    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
    teens = ["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    tens = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
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
                    res.append(ones[u] + " و " + tens[t])
                else:
                    res.append(tens[t])
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

# --- 1. إدارة ملف البيانات والتخزين الدائم (نسخ احتياطي أوتوماتيكي للأمان) ---
def get_default_factory_data():
    return {
        "info": {"factory_name": "مصنع البرادات", "admin_user": "admin", "admin_pass": "1234"},
        "inventory": {
            "الحنفية": 0.0, "البانكة": 0.0, "الماطور": 0.0, "التوماتيك": 0.0,
            "الطواف": 0.0, "الراديتر": 0.0, "زواية القاعدة": 0.0, "المنيوم القاعدة 1.35m": 0.0,
            "الجكنة": 0.0, "واشر حديد": 0.0, "واشر بلاستك": 0.0, "زبانة": 0.0,
            "كبلري 1.7m": 0.0, "كويل": 0.0, "بوري ربع 1.5m": 0.0, "طبقة وربع بليت": 0.0,
        },
        "finished_goods": {
            "براد حنفية واحدة": 0,
            "براد حنفيتين": 0,
        },
        "prices": {
            "براد حنفية واحدة": 150.0,
            "براد حنفيتين": 180.0,
        },
        "agents": {},
        "direct_customers": {},
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
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": [],
    }

def load_factory_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ضمان وجود كافة المفاتيح الأساسية لتفادي أخطاء التحديثات القديمة
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
    # حفظ الملف الرئيسي
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # عمل نسخة احتياطية تلقائية لضمان عدم ضياع البيانات
    try:
        with open("backup_" + DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
            pass

# --- 2. دوال الطباعة وتوليد الـ PDF ---
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
        except Exception as e:
            pass
    return font_path

def generate_receipt_pdf(
    factory_name,
    customer_name,
    customer_type,
    date_str,
    items_data,
    grand_total_usd,
    discount_usd,
    net_total_usd,
    paid_amount_usd,
    remaining_amount_usd,
    exchange_rate,
    receipt_no,
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)

    # --- شعار المعمل في أعلى اليمين ---
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=155, y=10, w=45)
        except Exception:
            pass

    # --- ترويسة قائمة الحساب الحديثة ---
    pdf.set_y(12)
    if os.path.exists(font_path):
        pdf.set_font("Amiri", "", 18)
    else:
        pdf.set_font("Arial", "B", 16)
    
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, ar(factory_name), ln=True, align="C")
    
    if os.path.exists(font_path):
        pdf.set_font("Amiri", "", 13)
    pdf.cell(0, 6, ar("قائمة حساب مبيعات رسمية"), ln=True, align="C")
    pdf.ln(5)

    # معلومات العميل والفاتورة
    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), 190, 20, style="DF")
    
    y_start = pdf.get_y() + 2
    pdf.set_xy(12, y_start)
    pdf.cell(90, 6, ar(f"رقم القائمة: #{receipt_no}"), align="R")
    pdf.set_xy(110, y_start)
    pdf.cell(88, 6, ar(f"التاريخ: {date_str}"), align="R")
    
    pdf.set_xy(12, y_start + 7)
    pdf.cell(90, 6, ar(f"اسم العميل: {customer_name} ({customer_type})"), align="R")
    pdf.set_xy(110, y_start + 7)
    pdf.cell(88, 6, ar(f"سعر الصرف: {exchange_rate:,.0f} د.ع"), align="R")
    
    pdf.set_y(y_start + 22)
    pdf.ln(4)

    # جدول المنتجات
    if items_data:
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        if os.path.exists(font_path):
            pdf.set_font("Amiri", "", 10)
            
        col_widths = [35, 35, 20, 45, 55]
        headers = [ar("الإجمالي ($)"), ar("السعر ($)"), ar("الكمية"), ar("الإجمالي (د.ع)"), ar("اسم المادة / البراد")]
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

    # الحسابات الختامية مع التظليل المطلوب للأموال
    pdf.ln(3)
    net_iqd = net_total_usd * exchange_rate
    paid_iqd = paid_amount_usd * exchange_rate
    rem_iqd = remaining_amount_usd * exchange_rate

    pdf.set_fill_color(226, 232, 240) # تظليل قيم المال
    pdf.cell(95, 7, f"${grand_total_usd:,.2f}", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المجموع الكلي"), border=1, align="R")
    pdf.ln()

    if discount_usd > 0:
        pdf.cell(95, 7, f"- ${discount_usd:,.2f}", border=1, align="C", fill=True)
        pdf.cell(95, 7, ar("قيمة الخصم الممنوح"), border=1, align="R")
        pdf.ln()

    pdf.cell(95, 7, f"${net_total_usd:,.2f} / {net_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("صافي المبلغ المطلوب"), border=1, align="R")
    pdf.ln()

    pdf.cell(95, 7, f"${paid_amount_usd:,.2f} / {paid_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المبلغ المدفوع نقدياً"), border=1, align="R")
    pdf.ln()

    pdf.cell(95, 7, f"${remaining_amount_usd:,.2f} / {rem_iqd:,.0f} د.ع", border=1, align="C", fill=True)
    pdf.cell(95, 7, ar("المبلغ المتبقي (آجل / أقساط)"), border=1, align="R")
    pdf.ln(12)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.cell(0, 6, ar("توقيع المحاسب / الإدارة: ..........................                توقيع المستلم: .........................."), ln=True, align="C")
    
    return bytes(pdf.output())

def generate_payment_pdf(
    factory_name,
    customer_name,
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

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)

    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=140, y=10, w=55)
        except Exception:
            pass

    pdf.set_y(34)
    if os.path.exists(font_path):
        pdf.set_font("Amiri", "", 15)
    else:
        pdf.set_font("Arial", "B", 14)

    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, ar(factory_name), ln=True, align="C")
    
    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 13)
    pdf.cell(0, 7, ar("سند قبض رسمي"), ln=True, align="C")
    pdf.ln(3)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 11)
    pdf.set_line_width(0.3)
    pdf.cell(93, 7, ar(f"رقم المستند: {receipt_no}"), border=1, align="R")
    pdf.cell(93, 7, ar(f"التاريخ: {date_str}"), border=1, align="R", ln=True)
    pdf.cell(186, 7, ar(f"استلمت من السيد / {customer_name}"), border=1, align="R", ln=True)

    amount_iqd = int(round(amount_usd * exchange_rate))
    amount_in_words = f"مبلغ وقدره: {number_to_arabic_words(amount_iqd)} دينار عراقي فقط لا غير"
    
    pdf.set_fill_color(226, 232, 240) # تظليل إجباري لكافة المبالغ المالية
    pdf.cell(186, 7, ar(amount_in_words), border=1, align="R", fill=True, ln=True)

    paid_iqd_val = int(round(amount_usd * exchange_rate))
    pdf.cell(93, 7, ar(f"سعر الصرف: {exchange_rate:,.0f} د.ع"), border=1, align="R")
    pdf.cell(93, 7, ar(f"المبلغ المدفوع: ${amount_usd:,.2f}  /  {paid_iqd_val:,} د.ع"), border=1, align="R", fill=True, ln=True)

    note_text = f"الملاحظات: {note}" if note else "الملاحظات: -"
    pdf.cell(186, 7, ar(note_text), border=1, align="R", ln=True)

    rem_iqd = int(round(remaining_debt_usd * exchange_rate))
    old_iqd = int(round(old_debt_usd * exchange_rate))
    pdf.cell(186, 7, ar(f"الرصيد السابق: ${old_debt_usd:,.2f}  /  {old_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)
    pdf.cell(186, 7, ar(f"الرصيد بعد التسديد: ${remaining_debt_usd:,.2f}  /  {rem_iqd:,} د.ع"), border=1, align="R", fill=True, ln=True)
    
    pdf.set_fill_color(255, 255, 255)
    pdf.ln(4)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 11)
    pdf.cell(186, 7, ar("توقيع وختم القابض:"), ln=True, align="R")
    sign_box_y = pdf.get_y()
    pdf.rect(12, sign_box_y, 186, 30)  
    
    return bytes(pdf.output())

# --- 3. إعداد صفحة الـ Streamlit والجلسة ---
st.set_page_config(
    page_title="نظام إدارة المخزون والمعامل والوكلاء",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

factory_data = load_factory_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- 4. شاشة تسجيل الدخول الموحدة لمعمل واحد ---
if not st.session_state.authenticated:
    st.title("❄️ نظام إدارة وتتبع المعمل والمخزون")
    st.subheader("تسجيل الدخول للنظام")
    
    username_input = st.text_input("اسم المستخدم:")
    password_input = st.text_input("كلمة المرور:", type="password")

    if st.button("تسجيل الدخول", type="primary", use_container_width=True):
        saved_user = factory_data["info"].get("admin_user", "admin")
        saved_pass = factory_data["info"].get("admin_pass", "1234")
        if username_input == saved_user and password_input == saved_pass:
            st.session_state.authenticated = True
            st.success("تم تسجيل الدخول بنجاح!")
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()

# --- 5. الواجهة الرئيسية والشريط العلوي ---
current_factory_name = factory_data["info"].get("factory_name", "مصنع البرادات")
st.title(f"❄️ {current_factory_name}")

col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    st.info("👤 الحساب النشط: **مدير النظام الرئيسي**")
with col_top2:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.write("---")

# --- 6. التبويبات الرئيسية للنظام ---
tabs = st.tabs([
    "📊 التقارير الشاملة",
    "🛒 بيع برادات أو مواد خام",
    "🤝 إدارة الوكلاء والزبائن",
    "🏭 تسجيل إنتاج براد",
    "💲 الأسعار الرسمية",
    "📦 إدارة المخزون",
    "🛠️ أنواع البرادات (BOM)",
    "⚙️ إعدادات النظام والأمان",
])

# --- تبويب التقارير الشاملة ---
with tabs[0]:
    st.header("📊 التقارير الشاملة والإحصائيات (بالدولار)")
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month_str = datetime.now().strftime("%Y-%m")

    sales_df = pd.DataFrame(factory_data.get("sales_history", []))
    today_sales_count, today_revenue_usd = 0, 0
    month_sales_count, month_revenue_usd = 0, 0

    if not sales_df.empty and "date" in sales_df.columns:
        sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce")
        today_sales = sales_df[sales_df["date"].dt.strftime("%Y-%m-%d") == today_str]
        month_sales = sales_df[sales_df["date"].dt.strftime("%Y-%m") == current_month_str]

        if not today_sales.empty:
            today_sales_count = today_sales["items_count"].sum()
            today_revenue_usd = today_sales["total_usd"].sum()

        if not month_sales.empty:
            month_sales_count = month_sales["items_count"].sum()
            month_revenue_usd = month_sales["total_usd"].sum()

    total_debts_usd = sum(
        agent.get("debt_usd", 0.0) for agent in list(factory_data["agents"].values()) + list(factory_data["direct_customers"].values())
        if isinstance(agent, dict)
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("برادات اليوم", f"{today_sales_count} براد")
    c2.metric("إيراد اليوم", f"${today_revenue_usd:,.2f}")
    c3.metric("مبيعات الشهر", f"{month_sales_count} براد")
    c4.metric("إيراد الشهر", f"${month_revenue_usd:,.2f}")
    c5.metric("إجمالي الديون", f"${total_debts_usd:,.2f}")

    st.write("---")
    st.subheader("🧊 المخزون الجاهز من البرادات")
    fg_df = pd.DataFrame(
        list(factory_data.get("finished_goods", {}).items()),
        columns=["نوع البراد", "الكمية المتاحة للبيع"],
    )
    st.dataframe(fg_df, use_container_width=True)

# --- تبويب بيع برادات أو مواد خام ---
with tabs[1]:
    st.header("🛒 نقطة البيع وإصدار قوائم الحساب")
    
    sale_category = st.radio("نوع المبيع:", ["برادات جاهزة", "مواد خام من المخزن"], horizontal=True)
    customer_type_choice = st.radio("تصنيف المشتري:", ["مشتري مباشر", "وكيل معتمد"], horizontal=True)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if customer_type_choice == "مشتري مباشر":
            direct_list = list(factory_data["direct_customers"].keys())
            cust_name = st.selectbox("اختر الزبون المباشر:", direct_list if direct_list else ["لا يوجد زبائن"])
            customer_name = cust_name
        else:
            agents_list = list(factory_data["agents"].keys())
            cust_name = st.selectbox("اختر الوكيل:", agents_list if agents_list else ["لا يوجد وكلاء"])
            customer_name = cust_name

    with col_c2:
        purchase_date = st.date_input("تاريخ عملية البيع:", value=datetime.now())
        exchange_rate = st.number_input("سعر صرف الدولار (د.ع مقابل $1):", min_value=1.0, value=1500.0, step=25.0)

    prices_dict = factory_data.get("prices", {})
    selected_items = []
    grand_total_usd = 0.0
    total_units = 0
    stock_error = False

    if sale_category == "برادات جاهزة":
        st.subheader("تحديد البرادات المراد بيعها والأسعار الثابتة:")
        model_list = list(factory_data["bom"].keys())
        for model in model_list:
            stock_available = factory_data["finished_goods"].get(model, 0)
            default_price = prices_dict.get(model, 0.0)
            
            c_m1, c_m2, c_m3 = st.columns([2, 1, 1])
            with c_m1:
                st.write(f"**{model}** (المتوفر بالمخزن: `{stock_available}`)")
            with c_m2:
                qty = st.number_input(f"العدد ({model}):", min_value=0, max_value=max(0, stock_available), value=0, key=f"sell_qty_{model}")
            with c_m3:
                price_val = st.number_input(f"السعر الفردي ($):", min_value=0.0, value=float(default_price), step=10.0, key=f"sell_price_{model}")

            if qty > stock_available:
                stock_error = True
            if qty > 0:
                item_total = qty * price_val
                grand_total_usd += item_total
                total_units += qty
                selected_items.append({"model": model, "count": qty, "price_usd": price_val, "total_usd": item_total})
    else:
        st.subheader("تحديد المواد الخام المراد بيعها:")
        inv_list = list(factory_data["inventory"].keys())
        for item_name in inv_list:
            stock_available = factory_data["inventory"].get(item_name, 0.0)
            default_price = prices_dict.get(item_name, 0.0)
            
            c_i1, c_i2, c_i3 = st.columns([2, 1, 1])
            with c_i1:
                st.write(f"**{item_name}** (المتوفر: `{stock_available:,.2f}`)")
            with c_i2:
                qty = st.number_input(f"الكمية ({item_name}):", min_value=0.0, max_value=float(stock_available) if stock_available > 0 else 0.0, value=0.0, step=1.0, key=f"sell_raw_qty_{item_name}")
            with c_i3:
                price_val = st.number_input(f"سعر الوحدة ($):", min_value=0.0, value=float(default_price), step=5.0, key=f"sell_raw_price_{item_name}")

            if qty > stock_available:
                stock_error = True
            if qty > 0:
                item_total = qty * price_val
                grand_total_usd += item_total
                total_units += int(qty)
                selected_items.append({"model": item_name, "count": qty, "price_usd": price_val, "total_usd": item_total})

    st.write("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        discount_usd = st.number_input("قيمة الخصم الممنوح ($):", min_value=0.0, value=0.0, step=5.0)
    
    net_total_usd = max(0.0, grand_total_usd - discount_usd)
    net_total_iqd = net_total_usd * exchange_rate

    st.markdown(f"### 💰 الإجمالي الصافي: `${net_total_usd:,.2f}` / `{net_total_iqd:,.0f}` د.ع")

    payment_method = st.radio("طريقة الدفع:", ["نقداً بالكامل", "بالآجل بالكامل", "دفع جزئي والباقي أقساط / آجل"], horizontal=True)
    
    if payment_method == "نقداً بالكامل":
        paid_amount_usd = net_total_usd
        remaining_amount_usd = 0.0
    elif payment_method == "بالآجل بالكامل":
        paid_amount_usd = 0.0
        remaining_amount_usd = net_total_usd
    else:
        paid_amount_usd = st.number_input("المبلغ المدفوع نقداً الآن ($):", min_value=0.0, max_value=float(net_total_usd), value=0.0, step=10.0)
        remaining_amount_usd = net_total_usd - paid_amount_usd

    if st.button("🛒 إتمام البيع وإصدار القائمة", type="primary", use_container_width=True):
        if stock_error:
            st.error("❌ الكمية المطلوبة تتجاوز المخزون المتوفر!")
        elif not selected_items:
            st.error("⚠️ يجيب تحديد عنصر واحد على الأقل للبيع.")
        else:
            receipt_no = factory_data.get("receipt_counter", 1001)
            
            # خصم الكميات من المخزون
            if sale_category == "برادات جاهزة":
                for item in selected_items:
                    factory_data["finished_goods"][item["model"]] -= int(item["count"])
            else:
                for item in selected_items:
                    factory_data["inventory"][item["model"]] -= item["count"]

            # تحديث ديون الزبون أو الوكيل إذا وجد متبقي
            if remaining_amount_usd > 0:
                target_dict = factory_data["agents"] if customer_type_choice == "وكيل معتمد" else factory_data["direct_customers"]
                if customer_name in target_dict:
                    old_debt = target_dict[customer_name].get("debt_usd", 0.0)
                    new_debt = old_debt + remaining_amount_usd
                    target_dict[customer_name]["debt_usd"] = new_debt
                    target_dict[customer_name].setdefault("transactions", []).append({
                        "date": purchase_date.strftime("%Y-%m-%d"),
                        "type": "شراء بقائمة (متبقي آجل/أقساط)",
                        "amount_usd": remaining_amount_usd,
                        "balance_usd": new_debt,
                        "note": f"قائمة حساب #{receipt_no}"
                    })

            pdf_bytes = generate_receipt_pdf(
                factory_name=current_factory_name,
                customer_name=customer_name,
                customer_type=customer_type_choice,
                date_str=purchase_date.strftime("%Y-%m-%d"),
                items_data=selected_items,
                grand_total_usd=grand_total_usd,
                discount_usd=discount_usd,
                net_total_usd=net_total_usd,
                paid_amount_usd=paid_amount_usd,
                remaining_amount_usd=remaining_amount_usd,
                exchange_rate=exchange_rate,
                receipt_no=receipt_no,
            )

            factory_data["sales_history"].append({
                "receipt_no": receipt_no,
                "date": purchase_date.strftime("%Y-%m-%d"),
                "customer": customer_name,
                "items_count": total_units,
                "total_usd": net_total_usd,
                "paid_usd": paid_amount_usd,
                "remaining_usd": remaining_amount_usd,
            })
            factory_data["receipt_counter"] = receipt_no + 1
            save_factory_data(factory_data)

            st.success("✅ تم إتمام عملية البيع وتحديث المخزون بنجاح!")
            st.toast("تم حفظ العملية وتوليد القائمة بنجاح!", icon="🎉")
            
            st.download_button(
                label="📥 تنزيل قائمة الحساب الرسمية (PDF)",
                data=pdf_bytes,
                file_name=f"قائمة_حساب_{receipt_no}_{customer_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# --- تبويب إدارة الوكلاء والزبائن ---
with tabs[2]:
    st.header("🤝 إدارة الوكلاء والزبائن المباشرين وديونهم")
    sub_ag1, sub_ag2 = st.tabs(["➕ إضافة جهة جديدة", "💵 قبض دفعة مالية وإصدار سند"])

    with sub_ag1:
        st.subheader("إضافة وكيل أو زبون مباشر جديد")
        new_type = st.radio("التصنيف:", ["وكيل معتمد", "زبون مباشر"], horizontal=True)
        new_name = st.text_input("اسم الشخص أو المحل:")
        new_phone = st.text_input("رقم الهاتف:")
        init_debt = st.number_input("الدين الافتتاحي السابق ($):", min_value=0.0, value=0.0, step=50.0)

        if st.button("➕ حفظ وتثبيت الجهة", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("يرجى إدخال الاسم.")
            else:
                target_dict = factory_data["agents"] if new_type == "وكيل معتمد" else factory_data["direct_customers"]
                if new_name in target_dict:
                    st.error("هذا الاسم موجود مسبقاً!")
                else:
                    target_dict[new_name] = {
                        "phone": new_phone,
                        "debt_usd": init_debt,
                        "transactions": []
                    }
                    if init_debt > 0:
                        target_dict[new_name]["transactions"].append({
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "type": "دين افتتاحي",
                            "amount_usd": init_debt,
                            "balance_usd": init_debt,
                            "note": "رصيد دين سابق عند التسجيل"
                        })
                    save_factory_data(factory_data)
                    st.success(f"✅ تمت إضافة [{new_name}] بنجاح!")
                    st.toast("تمت إضافة الجهة بنجاح!", icon="✅")

    with sub_ag2:
        st.subheader("قبض مبلغ مالي من وكيل / زبون وإصدار سند قبض")
        entity_cat = st.radio("البحث في:", ["وكيل معتمد", "زبون مباشر"], horizontal=True, key="pay_cat")
        target_dict = factory_data["agents"] if entity_cat == "وكيل معتمد" else factory_data["direct_customers"]
        entity_list = list(target_dict.keys())

        if not entity_list:
            st.info("لا توجد جهات مسجلة حالياً.")
        else:
            sel_entity = st.selectbox("اختر الجهة:", entity_list)
            curr_debt = target_dict[sel_entity].get("debt_usd", 0.0)
            st.warning(f"💰 الدين الحالي على [{sel_entity}]: **${curr_debt:,.2f}**")

            pay_amt = st.number_input("المبلغ المدفوع ($):", min_value=0.01, value=50.0, step=25.0)
            ex_rate = st.number_input("سعر صرف الدولار (د.ع):", min_value=1.0, value=1500.0, step=25.0, key="pay_ex")
            note_text = st.text_input("ملاحظات السند:", value="تسديد دفعة نقدية")

            if st.button("💵 تأكيد القبض وطبع السند الرسمي", type="primary", use_container_width=True):
                new_debt = max(0.0, curr_debt - pay_amt)
                target_dict[sel_entity]["debt_usd"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)
                factory_data["receipt_counter"] = receipt_no + 1

                target_dict[sel_entity].setdefault("transactions", []).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "تسديد دفعة",
                    "amount_usd": -pay_amt,
                    "balance_usd": new_debt,
                    "note": f"سند قبض #{receipt_no} - {note_text}"
                })
                save_factory_data(factory_data)

                pdf_payment_bytes = generate_payment_pdf(
                    factory_name=current_factory_name,
                    customer_name=sel_entity,
                    date_str=datetime.now().strftime("%Y-%m-%d"),
                    amount_usd=pay_amt,
                    remaining_debt_usd=new_debt,
                    old_debt_usd=curr_debt,
                    exchange_rate=ex_rate,
                    receipt_no=receipt_no,
                    note=note_text
                )

                st.success(f"✅ تم القبض بنجاح. الدين المتبقي: ${new_debt:,.2f}")
                st.toast("تم إصدار سند القبض بنجاح!", icon="💵")
                
                st.download_button(
                    label="📥 تنزيل سند القبض الرسمي (PDF)",
                    data=pdf_payment_bytes,
                    file_name=f"سند_قبض_{receipt_no}_{sel_entity}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

# --- تبويب تسجيل إنتاج براد ---
with tabs[3]:
    st.header("🏭 تسجيل عملية إنتاج براد جديد")
    model_list = list(factory_data["bom"].keys())
    
    if not model_list:
        st.warning("لا توجد نماذج برادات معرفة في النظام.")
    else:
        prod_model = st.selectbox("اختر نموذج البراد المصنوع:", model_list)
        prod_count = st.number_input("العدد المصنوع:", min_value=1, value=1, step=1)

        if st.button("🚀 تأكيد الإنتاج وخصم المواد الخام", type="primary", use_container_width=True):
            required_bom = factory_data["bom"][prod_model]
            missing_items = []
            for raw_item, req_qty in required_bom.items():
                needed = req_qty * prod_count
                available = factory_data["inventory"].get(raw_item, 0.0)
                if available < needed:
                    missing_items.append(f"- **{raw_item}**: المطلوب ({needed})، المتوفر ({available:,.2f})")

            if missing_items:
                st.error("❌ لا يوجد مخزون مواد خام كافٍ لإتمام الإنتاج!")
                for m in missing_items:
                    st.write(m)
            else:
                for raw_item, req_qty in required_bom.items():
                    factory_data["inventory"][raw_item] -= req_qty * prod_count
                
                factory_data["finished_goods"][prod_model] = factory_data["finished_goods"].get(prod_model, 0) + prod_count
                factory_data["production_history"].append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "model": prod_model,
                    "count": prod_count,
                })
                save_factory_data(factory_data)
                st.success(f"✅ تم إنتاج ({prod_count}) من [{prod_model}] بنجاح وتحديث المواد الخام!")
                st.toast("تم تسجيل عملية الإنتاج بنجاح!", icon="❄️")

# --- تبويب الأسعار الرسمية ---
with tabs[4]:
    st.header("💲 إدارة الأسعار الثابتة للمنتجات والمواد الخام")
    st.write("حدد هنا سعر البيع الثابت لكل براد أو مادة خام لتظهر مباشرة في نقطة البيع:")

    prices_df = pd.DataFrame(
        list(factory_data["prices"].items()),
        columns=["اسم العنصر", "سعر البيع الثابت ($)"]
    )
    edited_prices = st.data_editor(prices_df, num_rows="dynamic", use_container_width=True)

    if st.button("💾 حفظ الأسعار الثابتة", type="primary", use_container_width=True):
        new_prices = {}
        for _, row in edited_prices.iterrows():
            if row["اسم العنصر"]:
                new_prices[row["اسم العنصر"]] = float(row["سعر البيع الثابت ($)"])
        factory_data["prices"] = new_prices
        save_factory_data(factory_data)
        st.success("✅ تم تحديث الأسعار بنجاح!")
        st.toast("تم حفظ الأسعار الرسمية!", icon="💲")

# --- تبويب إدارة المخزون ---
with tabs[5]:
    st.header("📦 إدارة المخزون والمواد الخام")
    
    inv_tab1, inv_tab2 = st.tabs(["🧱 المواد الخام المتوفرة", "➕ تعديل وإضافة المواد الخام"])

    with inv_tab1:
        st.subheader("حالة المواد الخام الحالية")
        inv_df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية المتوفرة"]
        )
        st.dataframe(inv_df, use_container_width=True)

        st.subheader("🧊 البرادات الجاهزة بالمخزن")
        fg_inventory_df = pd.DataFrame(
            list(factory_data["finished_goods"].items()),
            columns=["نوع البراد", "العدد الجاهز للبيع"]
        )
        st.dataframe(fg_inventory_df, use_container_width=True)

    with inv_tab2:
        st.subheader("تعديل، زيادة، تنقيص، أو إضافة مادة خام جديدة")
        edit_inv_df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية المتوفرة"]
        )
        
        edited_inventory_table = st.data_editor(
            edit_inv_df, 
            num_rows="dynamic", 
            use_container_width=True,
            key="inventory_editor_table"
        )

        if st.button("💾 حفظ التعديلات على المخزون", type="primary", use_container_width=True):
            updated_inv = {}
            for _, row in edited_inventory_table.iterrows():
                item_name = str(row["اسم المادة الخام"]).strip()
                if item_name:
                    updated_inv[item_name] = float(row["الكمية المتوفرة"])
            
            factory_data["inventory"] = updated_inv
            save_factory_data(factory_data)
            st.success("✅ تم تحديث المخزون والكميات بنجاح!")
            st.toast("تم حفظ تفاصيل المخزون بنجاح!", icon="📦")
            st.rerun()

# --- تبويب أنواع البرادات (BOM) ---
with tabs[6]:
    st.header("🛠️ إدارة نماذج البرادات وتعديل المواد الخام اللازمة لكل نموذج")
    
    bom_models = list(factory_data["bom"].keys())
    selected_bom_model = st.selectbox("اختر نموذج البراد للتعديل:", bom_models)

    if selected_bom_model:
        current_bom_data = factory_data["bom"][selected_bom_model]
        st.subheader(f"المواد الخام المطلوبة لصنع: [{selected_bom_model}]")
        
        bom_df = pd.DataFrame(
            list(current_bom_data.items()),
            columns=["المادة الخام", "الكمية المطلوبة للبراد الواحد"]
        )
        
        edited_bom_df = st.data_editor(bom_df, num_rows="dynamic", use_container_width=True, key=f"bom_edit_{selected_bom_model}")

        if st.button("💾 حفظ تعديلات هذا النموذج", type="primary", use_container_width=True):
            new_bom_dict = {}
            for _, row in edited_bom_df.iterrows():
                raw_name = str(row["المادة الخام"]).strip()
                if raw_name:
                    new_bom_dict[raw_name] = float(row["الكمية المطلوبة للبراد الواحد"])
            
            factory_data["bom"][selected_bom_model] = new_bom_dict
            save_factory_data(factory_data)
            st.success(f"✅ تم تحديث مكونات نموذج [{selected_bom_model}] بنجاح!")
            st.toast("تم تحديث هيكل البراد (BOM)!", icon="🛠️")

    st.write("---")
    st.subheader("➕ إضافة نموذج براد جديد كلياً")
    new_model_name = st.text_input("اسم نموذج البراد الجديد:")
    if st.button("إضافة النموذج", use_container_width=True):
        if new_model_name:
            if new_model_name in factory_data["bom"]:
                st.error("هذا النموذج موجود مسبقاً!")
            else:
                factory_data["bom"][new_model_name] = {}
                factory_data["finished_goods"][new_model_name] = 0
                factory_data["prices"][new_model_name] = 200.0
                save_factory_data(factory_data)
                st.success(f"✅ تمت إضافة النموذج [{new_model_name}] بنجاح!")
                st.rerun()

# --- تبويب إعدادات النظام والأمان ---
with tabs[7]:
    st.header("⚙️ إعدادات النظام، بيانات الدخول، والأمان والحماية")
    
    st.subheader("🔒 تغيير اسم المستخدم وكلمة المرور")
    current_admin_user = factory_data["info"].get("admin_user", "admin")
    
    new_user_input = st.text_input("اسم المستخدم الجديد:", value=current_admin_user)
    new_pass_input = st.text_input("كلمة المرور الجديدة:", type="password")

    if st.button("تحديث بيانات الدخول", type="primary"):
        if new_user_input and new_pass_input:
            factory_data["info"]["admin_user"] = new_user_input
            factory_data["info"]["admin_pass"] = new_pass_input
            save_factory_data(factory_data)
            st.success("✅ تم تحديث بيانات الدخول بنجاح! يرجى إعادة تسجيل الدخول.")
            st.toast("تم تحديث كلمة المرور!", icon="🔒")
        else:
            st.error("يرجى ملء الحقول بشكل صحيح.")

    st.write("---")
    st.subheader("🛡️ حماية وضمان عدم ضياع البيانات")
    st.info("النظام يقوم أوتوماتيكياً بعمل نسخة احتياطية دورية في ملف (`backup_factory_data.json`) مع كل تعديل يتم إجراؤه لضمان الأمان التام.")

    if st.button("📥 تنزيل نسخة احتياطية للبيانات (Backup)", use_container_width=True):
        backup_json_str = json.dumps(factory_data, ensure_ascii=False, indent=4)
        st.download_button(
            label="تنزيل ملف النسخة الاحتياطية JSON",
            data=backup_json_str,
            file_name=f"backup_factory_{datetime.now().strftime('%Y-%m-%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

