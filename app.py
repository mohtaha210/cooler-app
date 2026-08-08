import os
import requests
import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة المعمل المتكامل", layout="wide")

# --- تهيئة ذاكرة النظام (Session State) ---
if "inventory" not in st.session_state:
    st.session_state.inventory = [
        {"اسم المادة الخام": "جلد طبيعي", "الكمية": 200, "سعر الوحدة ($)": 10.0, "إجمالي القيمة ($)": 2000.0},
        {"اسم المادة الخام": "نعل مطاطي", "الكمية": 500, "سعر الوحدة ($)": 3.0, "إجمالي القيمة ($)": 1500.0},
        {"اسم المادة الخام": "خيوط حياكة", "الكمية": 50, "سعر الوحدة ($)": 2.0, "إجمالي القيمة ($)": 100.0}
    ]

if "products" not in st.session_state:
    st.session_state.products = [
        {"اسم المنتج النهائي": "حذاء كلاسيك", "المادة الخام المستهلكة": "جلد طبيعي", "الكمية المستهلكة للقطعة": 2, "المخزون الحالي": 20}
    ]

# --- دالة معالجة النصوص العربية ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

# --- تنزيل الخط العربي للـ PDF ---
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# --- دالة إنشاء سند القبض (فارغ طبق الأصل 100%) ---
def generate_blank_sanad_qabd_pdf():
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # عنوان السند بالمنتصف
    pdf.set_font("Amiri", "", 24)
    pdf.set_xy(10, 12)
    pdf.cell(190, 12, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 12)

    # الصف الأول: رقم المستند | العملة
    y1 = 28
    pdf.set_xy(105, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("رقم المستند"), border=1, align="C")
    
    pdf.set_xy(10, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("العملة"), border=1, align="C")

    # الصف الثاني: تاريخ المستند | السيد
    y2 = y1 + 11
    pdf.set_xy(105, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(10, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("السيد"), border=1, align="C")

    # الصف الثالث: المبلغ
    y3 = y2 + 11
    pdf.set_xy(10, y3)
    pdf.cell(95, 11, "", border=1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("المبلغ"), border=1, align="C")

    # الصف الرابع: الملاحظات
    y4 = y3 + 11
    pdf.set_xy(10, y4)
    pdf.cell(160, 12, "", border=1)
    pdf.cell(30, 12, ar("الملاحظات"), border=1, align="C")

    # جدول الأرصدة
    y5 = y4 + 14
    pdf.set_xy(105, y5)
    pdf.cell(65, 10, "", border=1)
    pdf.cell(30, 10, ar("الرصيد السابق"), border=1, align="C")

    pdf.set_xy(105, y5 + 10)
    pdf.cell(65, 10, "", border=1)
    pdf.cell(30, 10, ar("الرصيد بعد التسديد"), border=1, align="C")

    pdf_out = pdf.output()
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin1')
    return bytes(pdf_out)


# ==========================================
#      واجهة نظام إدارة المعمل المتكامل
# ==========================================

st.sidebar.title("🏭 نظام إدارة المعمل")
menu = st.sidebar.radio(
    "القائمة الرئيسية:",
    ["الرئيسية (لوحة التحكم)", "إدارة المواد الخام (المخزن)", "منتجات المعمل والإنتاج", "الحسابات والسندات"]
)

# --- 1. قسم الرئيسية ---
if menu == "الرئيسية (لوحة التحكم)":
    st.title("📊 لوحة تحكم المعمل")
    
    tot_raw = sum(item["الكمية"] for item in st.session_state.inventory)
    tot_val = sum(item["إجمالي القيمة ($)"] for item in st.session_state.inventory)
    tot_prods = sum(p["المخزون الحالي"] for p in st.session_state.products)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("المواد الخام بالمخزن", f"{tot_raw:,} وحدة")
    col2.metric("إجمالي المنتجات الجاهزة", f"{tot_prods:,} قطعة")
    col3.metric("قيمة المواد الخام الكلية", f"${tot_val:,.2f}")

# --- 2. قسم المخزن والمواد الخام ---
elif menu == "إدارة المواد الخام (المخزن)":
    st.title("🏗️ إدارة المواد الخام بالمخزن")

    with st.expander("➕ إضافة مادة خام جديدة للمخزن", expanded=True):
        with st.form("add_raw_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                raw_name = st.text_input("اسم المادة الخام")
            with col_b:
                raw_qty = st.number_input("الكمية المتاحة", min_value=1, value=50)
            with col_c:
                raw_price = st.number_input("سعر الوحدة ($)", min_value=0.0, value=5.0)
            
            if st.form_submit_button("حفظ المادة الخام"):
                if raw_name.strip():
                    st.session_state.inventory.append({
                        "اسم المادة الخام": raw_name,
                        "الكمية": raw_qty,
                        "سعر الوحدة ($)": raw_price,
                        "إجمالي القيمة ($)": raw_qty * raw_price
                    })
                    st.success(f"تمت إضافة ({raw_name}) إلى المخزن بنجاح!")
                    st.rerun()

    st.subheader("📋 جدول المواد الخام المتوفرة")
    if st.session_state.inventory:
        st.dataframe(pd.DataFrame(st.session_state.inventory), use_container_width=True)
    else:
        st.warning("لا توجد مواد خام حالياً.")

# --- 3. قسم منتجات المعمل والإنتاج (ربط المنتجات بالمواد الخام) ---
elif menu == "منتجات المعمل والإنتاج":
    st.title("🛠️ إدارة منتجات المعمل وخطوط الإنتاج")
    
    raw_materials_list = [item["اسم المادة الخام"] for item in st.session_state.inventory]
    
    if not raw_materials_list:
        st.error("⚠️ يجب إضافة مواد خام في قسم المخزن أولاً حتى تتمكن من إضافة وتصنيع المنتجات.")
    else:
        # 1. إضافة منتج جديد وتحديد المادة الخام التي يستهلكها
        with st.expander("➕ تعريف منتج جديد وتحديد المواد المستهلكة", expanded=True):
            with st.form("add_product_form", clear_on_submit=True):
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    p_name = st.text_input("اسم المنتج الذي ينتجه المعمل")
                with col_p2:
                    selected_raw = st.selectbox("المادة الخام التي يستهلكها:", options=raw_materials_list)
                with col_p3:
                    raw_needed = st.number_input("كم مادة خام تستهلك القطعة الواحدة؟", min_value=1, value=1)
                
                if st.form_submit_button("تسجيل المنتج"):
                    if p_name.strip():
                        st.session_state.products.append({
                            "اسم المنتج النهائي": p_name,
                            "المادة الخام المستهلكة": selected_raw,
                            "الكمية المستهلكة للقطعة": raw_needed,
                            "المخزون الحالي": 0
                        })
                        st.success(f"تم تعريف منتج ({p_name}) وتحديده لاستهلاك ({raw_needed} من {selected_raw}) لكل قطعة.")
                        st.rerun()

        st.divider()

        # 2. خط الإنتاج (تصنيع الكميات وخصم المواد الخام أوتوماتيكياً)
        st.subheader("🏭 تسجيل عملية إنتاج جديدة (خصم تلقائي من المخزن)")
        if st.session_state.products:
            prod_names = [p["اسم المنتج النهائي"] for p in st.session_state.products]
            
            c_prod, c_qty, c_btn = st.columns([2, 2, 1])
            with c_prod:
                selected_p_to_make = st.selectbox("اختر المنتج للإنتاج:", options=prod_names)
            with c_qty:
                qty_to_make = st.number_input("الكمية المراد تصنيعها:", min_value=1, value=10)
            
            with c_btn:
                st.write("")
                st.write("")
                if st.button("بدء الإنتاج 🚀", type="primary"):
                    # البحث عن المنتج والمعادلة
                    prod_info = next(p for p in st.session_state.products if p["اسم المنتج النهائي"] == selected_p_to_make)
                    needed_material = prod_info["المادة الخام المستهلكة"]
                    total_material_needed = prod_info["الكمية المستهلكة للقطعة"] * qty_to_make
                    
                    # البحث عن المادة الخام في المخزن
                    raw_item = next((r for r in st.session_state.inventory if r["اسم المادة الخام"] == needed_material), None)
                    
                    if raw_item and raw_item["الكمية"] >= total_material_needed:
                        # 1. خصم المادة الخام من المخزن
                        raw_item["الكمية"] -= total_material_needed
                        raw_item["إجمالي القيمة ($)"] = raw_item["الكمية"] * raw_item["سعر الوحدة ($)"]
                        
                        # 2. زيادة مخزون المنتج النهائي
                        prod_info["المخزون الحالي"] += qty_to_make
                        
                        st.success(f"تم تصنيع {qty_to_make} قطعة من ({selected_p_to_make}) بنجاح! وتم خصم {total_material_needed} من مادة ({needed_material}) من المخزن.")
                        st.rerun()
                    else:
                        st.error(f"❌ المادة الخام غير كافية! تحتاج {total_material_needed} من ({needed_material}) بينما المتاح في المخزن هو {raw_item['الكمية'] if raw_item else 0}.")

        # 3. جدول المنتجات الحالية
        st.subheader("📦 قائمة منتجات المعمل والمخزون الحالي")
        if st.session_state.products:
            st.dataframe(pd.DataFrame(st.session_state.products), use_container_width=True)

# --- 4. قسم الحسابات والسندات ---
elif menu == "الحسابات والسندات":
    st.title("💰 قسم الحسابات والسندات المالية")
    
    st.subheader("📄 طباعة نماذج السندات الورقية")
    st.write("اضغط على الزر أدناه لتحميل أو طباعة **سند قبض فارغ** جاهز للطباعة يدوياً وبنفس مقاسات وتقسيمات الورق الرسمي للمعمل:")
    
    blank_pdf = generate_blank_sanad_qabd_pdf()
    st.download_button(
        label="🖨️ تحميل / طباعة سند قبض فارغ (PDF)",
        data=blank_pdf,
        file_name="Sanad_Qabd_Blank.pdf",
        mime="application/pdf",
        type="primary"
    )
