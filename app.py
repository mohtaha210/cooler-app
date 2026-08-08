import os
import requests
import streamlit as st
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة المعمل المتكامل", layout="wide")

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

# --- دالة إنشاء سند القبض (فارغ طبق الأصل 100% بدون مدخلات) ---
def generate_blank_sanad_qabd_pdf():
    font_path = ensure_arabic_font()
    
    # قياس A5 Landscape (أفقي) بنفس مقاس الورقة الأصلية
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # عنوان السند بالمنتصف
    pdf.set_font("Amiri", "", 24)
    pdf.set_xy(10, 12)
    pdf.cell(190, 12, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 12)

    # --- الجدول الرئيسي ---
    # الصف الأول: رقم المستند (يمين) | العملة (يسار)
    y1 = 28
    pdf.set_xy(105, y1)
    pdf.cell(65, 11, "", border=1) # فارغ
    pdf.cell(30, 11, ar("رقم المستند"), border=1, align="C")
    
    pdf.set_xy(10, y1)
    pdf.cell(65, 11, "", border=1) # فارغ
    pdf.cell(30, 11, ar("العملة"), border=1, align="C")

    # الصف الثاني: تاريخ المستند (يمين) | السيد (يسار)
    y2 = y1 + 11
    pdf.set_xy(105, y2)
    pdf.cell(65, 11, "", border=1) # فارغ
    pdf.cell(30, 11, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(10, y2)
    pdf.cell(65, 11, "", border=1) # فارغ
    pdf.cell(30, 11, ar("السيد"), border=1, align="C")

    # الصف الثالث: المبلغ رقماً + المبلغ كتابةً
    y3 = y2 + 11
    pdf.set_xy(10, y3)
    pdf.cell(95, 11, "", border=1) # مساحة كتابة المبلغ تفقيطاً
    pdf.cell(65, 11, "", border=1) # مساحة المبلغ رقماً
    pdf.cell(30, 11, ar("المبلغ"), border=1, align="C")

    # الصف الرابع: الملاحظات
    y4 = y3 + 11
    pdf.set_xy(10, y4)
    pdf.cell(160, 12, "", border=1) # فارغ للملاحظات
    pdf.cell(30, 12, ar("الملاحظات"), border=1, align="C")

    # --- جدول الأرصدة السفلي (على اليمين) ---
    y5 = y4 + 14
    pdf.set_xy(105, y5)
    pdf.cell(65, 10, "", border=1) # فارغ للرصيد السابق
    pdf.cell(30, 10, ar("الرصيد السابق"), border=1, align="C")

    pdf.set_xy(105, y5 + 10)
    pdf.cell(65, 10, "", border=1) # فارغ للرصيد بعد التسديد
    pdf.cell(30, 10, ar("الرصيد بعد التسديد"), border=1, align="C")

    pdf_out = pdf.output()
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin1')
    return bytes(pdf_out)


# ==========================================
#      واجهة نظام إدارة المعمل المتكامل
# ==========================================

# الشريط الجانبي للتنقل بين أقسام المعمل
st.sidebar.title("🏭 نظام إدارة المعمل")
menu = st.sidebar.radio(
    "القائمة الرئيسية:",
    ["الرئيسية (لوحة التحكم)", "إدارة الإنتاج والطلبيات", "الحسابات والسندات", "المخزن والمواد الخام"]
)

# --- 1. قسم الرئيسية ---
if menu == "الرئيسية (لوحة التحكم)":
    st.title("📊 لوحة تحكم المعمل")
    st.write("مرحباً بك في نظام إدارة المعمل. يمكنك متابعة العمليات والحسابات من هنا.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الإنتاج اليومي", "1,250 وحدة")
    col2.metric("إجمالي المبيعات", "$4,300")
    col3.metric("الطلبيات المعلقة", "5 طلبيات")

# --- 2. قسم الإنتاج ---
elif menu == "إدارة الإنتاج والطلبيات":
    st.title("📦 إدارة الإنتاج والطلبيات")
    st.subheader("سجل الطلبيات الحالية")
    st.info("هنا يتم عرض وتحديث خطوط الإنتاج والطلبيات الخاصة بالعملاء.")

# --- 3. قسم الحسابات والسندات (وفيه طباعة السند الفارغ) ---
elif menu == "الحسابات والسندات":
    st.title("💰 قسم الحسابات والسندات المالية")
    
    st.subheader("📄 طباعة نماذج السندات الورقية")
    st.write("اضغط على الزر أدناه لتحميل أو طباعة **سند قبض فارغ** جاهز للطباعة يدوياً وبنفس مقاسات وتقسيمات الورق الرسمي للمعمل:")
    
    # زر تحميل السند الفارغ فوراً
    blank_pdf = generate_blank_sanad_qabd_pdf()
    st.download_button(
        label="🖨️ تحميل / طباعة سند قبض فارغ (PDF)",
        data=blank_pdf,
        file_name="Sanad_Qabd_Blank.pdf",
        mime="application/pdf",
        type="primary"
    )

# --- 4. قسم المخزن ---
elif menu == "المخزن والمواد الخام":
    st.title("🏗️ إدارة المخزن والمواد الخام")
    st.write("متابعة حركة المخزون والمواد الأولية للمعمل.")
