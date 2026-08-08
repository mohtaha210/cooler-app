import os
import requests
import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة المعمل المتكامل", layout="wide")

# --- تهيئة ذاكرة المخزون (Session State) ---
if "inventory" not in st.session_state:
    st.session_state.inventory = [
        {"اسم المنتج / المادة": "مادة خام A", "الكمية": 100, "سعر الوحدة ($)": 15.0, "إجمالي القيمة ($)": 1500.0},
        {"اسم المنتج / المادة": "منتج نهائي B", "الكمية": 50, "سعر الوحدة ($)": 40.0, "إجمالي القيمة ($)": 2000.0}
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

    # الصف الأول: رقم المستند (يمين) | العملة (يسار)
    y1 = 28
    pdf.set_xy(105, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("رقم المستند"), border=1, align="C")
    
    pdf.set_xy(10, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("العملة"), border=1, align="C")

    # الصف الثاني: تاريخ المستند (يمين) | السيد (يسار)
    y2 = y1 + 11
    pdf.set_xy(105, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(10, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("السيد"), border=1, align="C")

    # الصف الثالث: المبلغ رقماً + المبلغ كتابةً
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

    # جدول الأرصدة السفلي
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
    ["الرئيسية (لوحة التحكم)", "إدارة المخزن والمواد الخام", "الحسابات والسندات", "إدارة الإنتاج والطلبيات"]
)

# --- 1. قسم الرئيسية ---
if menu == "الرئيسية (لوحة التحكم)":
    st.title("📊 لوحة تحكم المعمل")
    st.write("مرحباً بك في نظام إدارة المعمل. يمكنك متابعة العمليات والحسابات من هنا.")
    
    total_items = sum(item["الكمية"] for item in st.session_state.inventory)
    total_val = sum(item["إجمالي القيمة ($)"] for item in st.session_state.inventory)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي القطع بالمخزن", f"{total_items:,}")
    col2.metric("قيمة المخزون الكلية", f"${total_val:,.2f}")
    col3.metric("الأنواع المسجلة", len(st.session_state.inventory))

# --- 2. قسم المخزن المتكامل (إضافة / عرض / حذف) ---
elif menu == "إدارة المخزن والمواد الخام":
    st.title("🏗️ إدارة المخزن والمواد الخام")
    st.write("يمكنك إضافة عناصر جديدة إلى المخزون أو التعديل والحذف مباشرة.")

    # ➕ نموذج إضافة عنصر جديد للمخزن
    with st.expander("➕ إضافة منتج / مادة خام جديدة للمخزن", expanded=True):
        with st.form("add_inventory_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                item_name = st.text_input("اسم المنتج / المادة")
            with col_b:
                item_qty = st.number_input("الكمية", min_value=1, value=10, step=1)
            with col_c:
                item_price = st.number_input("سعر الوحدة ($)", min_value=0.0, value=5.0, step=0.5)
            
            submit_btn = st.form_submit_button("حفظ وإضافة للمخزن")
            
            if submit_btn:
                if item_name.strip() != "":
                    total_p = item_qty * item_price
                    st.session_state.inventory.append({
                        "اسم المنتج / المادة": item_name,
                        "الكمية": item_qty,
                        "سعر الوحدة ($)": item_price,
                        "إجمالي القيمة ($)": total_p
                    })
                    st.success(f"تمت إضافة ({item_name}) بنجاح إلى المخزن!")
                else:
                    st.error("يرجى إدخال اسم المنتج أولاً.")

    st.divider()

    # 📋 عرض جدول المخزون الحالي
    st.subheader("📋 جدول المخزون الحالي")
    if len(st.session_state.inventory) > 0:
        df = pd.DataFrame(st.session_state.inventory)
        st.dataframe(df, use_container_width=True)
        
        # حاسبة إجماليات المخزن
        tot_qty = sum(item["الكمية"] for item in st.session_state.inventory)
        tot_val = sum(item["إجمالي القيمة ($)"] for item in st.session_state.inventory)
        
        col_m1, col_m2 = st.columns(2)
        col_m1.info(f"📦 مجموع الكميات بالمخزن: **{tot_qty:,}** قطعة")
        col_m2.success(f"💰 إجمالي قيمة المخزون: **${tot_val:,.2f}**")

        # 🗑️ خيار حذف عنصر من المخزن
        st.subheader("🗑️ إدارة / حذف عنصر من المخزن")
        item_to_delete = st.selectbox(
            "اختر المنتج المراد حذفه:",
            options=[item["اسم المنتج / المادة"] for item in st.session_state.inventory]
        )
        if st.button("حذف المنتج المحدد", type="primary"):
            st.session_state.inventory = [
                item for item in st.session_state.inventory if item["اسم المنتج / المادة"] != item_to_delete
            ]
            st.success(f"تم حذف {item_to_delete} بنجاح.")
            st.rerun()
    else:
        st.warning("المخزن فارغ حالياً. قم بإضافة عناصر جديدة أعلاه.")

# --- 3. قسم الحسابات والسندات ---
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

# --- 4. قسم الإنتاج ---
elif menu == "إدارة الإنتاج والطلبيات":
    st.title("📦 إدارة الإنتاج والطلبيات")
    st.subheader("سجل الطلبيات الحالية")
    st.info("هنا يتم عرض وتحديث خطوط الإنتاج والطلبيات الخاصة بالعملاء.")
