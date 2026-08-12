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

DATA_FILE = "factory_full_data.json"

# --- 0. دوال مساعدة وتحويل النصوص والأرقام إلى كلمات عربية ---
def number_to_arabic_words(num):
    if num == 0:
        return "صفر"
    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
    teens = ["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    tens_list = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
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
                    res.append(ones[u] + " و " + tens_list[t])
                else:
                    res.append(tens_list[t])
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
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": [],
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
    pdf.cell(0, 6, ar("قائمة حساب مبيعات رسمية"), ln=True, align="C")
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
    pdf.cell(90, 6, ar(f"اسم الزبون: {customer_name if customer_name else 'زبون عام'}"), align="R")
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
        headers = [ar("الإجمالي ($)"), ar("السعر ($)"), ar("الكمية"), ar("الإجمالي (د.ع)"), ar("اسم Mادة / براد")]
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
    pdf.cell(95, 7, ar("المبلغ المتبقي"), border=1, align="R")
    pdf.ln(12)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 10)
    pdf.cell(0, 6, ar("توقيع المحاسب: ..........................                توقيع المستلم: .........................."), ln=True, align="C")
    
    return bytes(pdf.output())

# --- 3. تهيئة واجهة التطبيق ---
st.set_page_config(
    page_title="نظام إدارة المعمل المبسط",
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
    "🛒 نقطة البيع",
    "🏭 تسجيل إنتاج",
    "📦 المخزون",
    "💲 الأسعار",
    "🛠️ هيكل البرادات (BOM)",
    "📊 التقارير",
    "⚙️ الإعدادات"
])

# تبويب نقطة البيع المبسطة والفعالة
with tabs[0]:
    st.header("🛒 نقطة البيع وإصدار القوائم")
    
    customer_name = st.text_input("اسم الزبون (اختياري):", placeholder="اكتب اسم الزبون هنا...")
    exchange_rate = st.number_input("سعر صرف الدولار (د.ع مقابل $1):", min_value=1.0, value=1500.0, step=25.0)
    
    sale_type = st.radio("نوع المبيع:", ["برادات جاهزة", "مواد خام من المخزن"], horizontal=True)
    prices_dict = factory_data.get("prices", {})
    selected_items = []
    grand_total_usd = 0.0
    total_units = 0
    stock_error = False

    if sale_type == "برادات جاهزة":
        st.subheader("اختر البرادات والكميات المطلوبة:")
        for model in factory_data["bom"].keys():
            stock = factory_data["finished_goods"].get(model, 0)
            def_price = prices_dict.get(model, 0.0)
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"**{model}** (متوفر بالمخزن: `{stock}`)")
            with c2:
                qty = st.number_input(f"العدد ({model})", min_value=0, max_value=max(0, stock), value=0, key=f"p_{model}")
            with c3:
                price = st.number_input(f"السعر ($) ({model})", min_value=0.0, value=float(def_price), step=10.0, key=f"pr_{model}")

            if qty > stock:
                stock_error = True
            if qty > 0:
                item_tot = qty * price
                grand_total_usd += item_tot
                total_units += qty
                selected_items.append({"model": model, "count": qty, "price_usd": price, "total_usd": item_tot})
    else:
        st.subheader("اختر المواد الخام والكميات المطلوبة:")
        for item_name, stock in factory_data["inventory"].items():
            def_price = prices_dict.get(item_name, 0.0)
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"**{item_name}** (متوفر: `{stock:,.2f}`)")
            with c2:
                qty = st.number_input(f"الكمية ({item_name})", min_value=0.0, max_value=float(stock) if stock > 0 else 0.0, value=0.0, step=1.0, key=f"raw_{item_name}")
            with c3:
                price = st.number_input(f"سعر الوحدة ($) ({item_name})", min_value=0.0, value=float(def_price), step=5.0, key=f"rawpr_{item_name}")

            if qty > stock:
                stock_error = True
            if qty > 0:
                item_tot = qty * price
                grand_total_usd += item_tot
                total_units += int(qty)
                selected_items.append({"model": item_name, "count": qty, "price_usd": price, "total_usd": item_tot})

    discount_usd = st.number_input("قيمة الخصم ($):", min_value=0.0, value=0.0, step=5.0)
    net_total_usd = max(0.0, grand_total_usd - discount_usd)
    
    st.markdown(f"### 💰 الإجمالي الصافي: `${net_total_usd:,.2f}` (`{net_total_usd * exchange_rate:,.0f}` د.ع)")

    paid_amount_usd = st.number_input("المبلغ المدفوع ($):", min_value=0.0, value=float(net_total_usd), step=10.0)
    remaining_amount_usd = max(0.0, net_total_usd - paid_amount_usd)

    if st.button("🛒 إتمام البيع وإصدار القائمة", type="primary", use_container_width=True):
        if stock_error:
            st.error("❌ الكمية المطلوبة تتجاوز المخزون المتاح!")
        elif not selected_items:
            st.error("⚠️ يرجى اختيار عنصر واحد على الأقل للبيع.")
        else:
            receipt_no = factory_data.get("receipt_counter", 1001)
            
            if sale_type == "برادات جاهزة":
                for item in selected_items:
                    factory_data["finished_goods"][item["model"]] -= int(item["count"])
            else:
                for item in selected_items:
                    factory_data["inventory"][item["model"]] -= item["count"]

            pdf_bytes = generate_receipt_pdf(
                factory_name=current_factory_name,
                customer_name=customer_name,
                date_str=datetime.now().strftime("%Y-%m-%d"),
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
                "date": datetime.now().strftime("%Y-%m-%d"),
                "customer": customer_name if customer_name else "زبون عام",
                "total_usd": net_total_usd,
            })
            factory_data["receipt_counter"] = receipt_no + 1
            save_factory_data(factory_data)

            st.success("✅ تمت عملية البيع وتحديث المخزون بنجاح!")
            st.download_button(
                label="📥 تنزيل القائمة الرسمية (PDF)",
                data=pdf_bytes,
                file_name=f"قائمة_حساب_{receipt_no}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# تبويب تسجيل إنتاج البرادات
with tabs[1]:
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
with tabs[2]:
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
with tabs[3]:
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

# تبويب هيكل البرادات (BOM)
with tabs[4]:
    st.header("🛠️ إدارة مكونات البرادات (BOM)")
    bom_models = list(factory_data["bom"].keys())
    sel_model = st.selectbox("اختر نموذج البراد لتعديل مكوناته:", bom_models)

    if sel_model:
        current_bom = factory_data["bom"][sel_model]
        bom_df = pd.DataFrame(list(current_bom.items()), columns=["المادة الخام", "الكمية المطلوبة للبراد الواحد"])
        edited_bom = st.data_editor(bom_df, num_rows="dynamic", use_container_width=True, key=f"bom_{sel_model}")

        if st.button("💾 حفظ مكونات النموذج", type="primary"):
            new_bom_dict = {}
            for _, row in edited_bom.iterrows():
                raw_name = str(row["المادة الخام"]).strip()
                if raw_name:
                    new_bom_dict[raw_name] = float(row["الكمية المطلوبة للبراد الواحد"])
            factory_data["bom"][sel_model] = new_bom_dict
            save_factory_data(factory_data)
            st.success("✅ تم تحديث هيكل البراد بنجاح!")

    st.write("---")
    st.subheader("➕ إضافة نموذج براد جديد")
    new_model_name = st.text_input("اسم النموذج الجديد:")
    if st.button("إضافة النموذج الجديد"):
        if new_model_name:
            if new_model_name in factory_data["bom"]:
                st.error("النموذج موجود مسبقاً!")
            else:
                factory_data["bom"][new_model_name] = {}
                factory_data["finished_goods"][new_model_name] = 0
                factory_data["prices"][new_model_name] = 200.0
                save_factory_data(factory_data)
                st.success(f"✅ تمت إضافة [{new_model_name}] بنجاح!")
                st.rerun()

# تبويب التقارير
with tabs[5]:
    st.header("📊 سجل المبيعات والعمليات")
    sales_hist = pd.DataFrame(factory_data.get("sales_history", []))
    if sales_hist.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        st.dataframe(sales_hist, use_container_width=True)

# تبويب الإعدادات
with tabs[6]:
    st.header("⚙️ إعدادات النظام والأمان")
    new_user = st.text_input("اسم المستخدم الجديد:", value=factory_data["info"].get("admin_user", "admin"))
    new_pass = st.text_input("كلمة المرور الجديدة:", type="password")

    if st.button("تحديث بيانات الدخول"):
        if new_user and new_pass:
            factory_data["info"]["admin_user"] = new_user
            factory_data["info"]["admin_pass"] = new_pass
            save_factory_data(factory_data)
            st.success("✅ تم تحديث بيانات الدخول بنجاح!")
