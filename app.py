import os
import requests
import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة معمل برادات الماء", layout="wide")

# --- 1. تهيئة المخزون الافتراضي للمواد الخام (28 مادة أساسية لصناعة براد الماء) ---
if "inventory" not in st.session_state:
    st.session_state.inventory = [
        {"المادة الخام": "ضغاط (كومبريسور)", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "مكثف (شبك تبريد)", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "مبخر (مبرد الخزان)", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "خزان استيل ماء بارد", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "خزان ماء حار", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "غاز تبريد (R134a/R600a)", "الكمية بالمخزن": 100, "الوحدة": "كغم"},
        {"المادة الخام": "أنبوب شعري (Capillary)", "الكمية بالمخزن": 200, "الوحدة": "متر"},
        {"المادة الخام": "أنبوب نحاس تبريد", "الكمية بالمخزن": 300, "الوحدة": "متر"},
        {"المادة الخام": "فلتر منقي غاز", "الكمية بالمخزن": 100, "الوحدة": "قطعة"},
        {"المادة الخام": "ترموستات حرارة (حراري/برودة)", "الكمية بالمخزن": 100, "الوحدة": "قطعة"},
        {"المادة الخام": "هيكل صاج خارجي", "الكمية بالمخزن": 50, "الوحدة": "طقم"},
        {"المادة الخام": "قاعدة بلاستيك سفلية", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "غطاء علوي بلاستيك", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "عازل فوم (Foom)", "الكمية بالمخزن": 80, "الوحدة": "كغم"},
        {"المادة الخام": "حنفية ماء بارد", "الكمية بالمخزن": 100, "الوحدة": "قطعة"},
        {"المادة الخام": "حنفية ماء حار (أمان)", "الكمية بالمخزن": 100, "الوحدة": "قطعة"},
        {"المادة الخام": "حنفية ماء عادي", "الكمية بالمخزن": 100, "الوحدة": "قطعة"},
        {"المادة الخام": "أسلاك كهربائية وتوصيلات", "الكمية بالمخزن": 500, "الوحدة": "متر"},
        {"المادة الخام": "قابس كهرباء (سلك فيشة)", "الكمية بالمخزن": 60, "الوحدة": "قطعة"},
        {"المادة الخام": "مفتاح تشغيل/إطفاء", "الكمية بالمخزن": 120, "الوحدة": "قطعة"},
        {"المادة الخام": "لمبات إشارة LED", "الكمية بالمخزن": 200, "الوحدة": "قطعة"},
        {"المادة الخام": "صينية تجميع التقطير", "الكمية بالمخزن": 60, "الوحدة": "قطعة"},
        {"المادة الخام": "براغي وتثبيت متنوعة", "الكمية بالمخزن": 5000, "الوحدة": "برغي"},
        {"المادة الخام": "قواعد مطاطية لامتزاز الاهتزاز", "الكمية بالمخزن": 200, "الوحدة": "قطعة"},
        {"المادة الخام": "كارتون تغليف خارجي", "الكمية بالمخزن": 50, "الوحدة": "قطعة"},
        {"المادة الخام": "فلين حماية للتغليف", "الكمية بالمخزن": 100, "الوحدة": "طقم"},
        {"المادة الخام": "كتالوج/دليل المستخدم", "الكمية بالمخزن": 100, "الوحدة": "نسخة"},
        {"المادة الخام": "لاصق وشعار المعمل", "الكمية بالمخزن": 200, "الوحدة": "ملصق"}
    ]

# --- 2. قائمة المكونات الـ 28 المطلوبة لتصنيع (1 براد ماء) ---
if "cooler_bom" not in st.session_state:
    st.session_state.cooler_bom = {
        "ضغاط (كومبريسور)": 1,
        "مكثف (شبك تبريد)": 1,
        "مبخر (مبرد الخزان)": 1,
        "خزان استيل ماء بارد": 1,
        "خزان ماء حار": 1,
        "غاز تبريد (R134a/R600a)": 0.5,
        "أنبوب شعري (Capillary)": 1.5,
        "أنبوب نحاس تبريد": 2,
        "فلتر منقي غاز": 1,
        "ترموستات حرارة (حراري/برودة)": 2,
        "هيكل صاج خارجي": 1,
        "قاعدة بلاستيك سفلية": 1,
        "غطاء علوي بلاستيك": 1,
        "عازل فوم (Foom)": 1,
        "حنفية ماء بارد": 1,
        "حنفية ماء حار (أمان)": 1,
        "حنفية ماء عادي": 1,
        "أسلاك كهربائية وتوصيلات": 3,
        "قابس كهرباء (سلك فيشة)": 1,
        "مفتاح تشغيل/إطفاء": 2,
        "لمبات إشارة LED": 3,
        "صينية تجميع التقطير": 1,
        "براغي وتثبيت متنوعة": 30,
        "قواعد مطاطية لامتزاز الاهتزاز": 4,
        "كارتون تغليف خارجي": 1,
        "فلين حماية للتغليف": 1,
        "كتالوج/دليل المستخدم": 1,
        "لاصق وشعار المعمل": 2
    }

if "produced_coolers" not in st.session_state:
    st.session_state.produced_coolers = 0

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

# --- دالة إنشاء سند القبض الفارغ (طبق الأصل 100%) ---
def generate_blank_sanad_qabd_pdf():
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    pdf.set_font("Amiri", "", 24)
    pdf.set_xy(10, 12)
    pdf.cell(190, 12, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 12)

    # الصف الأول
    y1 = 28
    pdf.set_xy(105, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("رقم المستند"), border=1, align="C")
    
    pdf.set_xy(10, y1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("العملة"), border=1, align="C")

    # الصف الثاني
    y2 = y1 + 11
    pdf.set_xy(105, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(10, y2)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("السيد"), border=1, align="C")

    # الصف الثالث
    y3 = y2 + 11
    pdf.set_xy(10, y3)
    pdf.cell(95, 11, "", border=1)
    pdf.cell(65, 11, "", border=1)
    pdf.cell(30, 11, ar("المبلغ"), border=1, align="C")

    # الصف الرابع
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
#     واجهة نظام إدارة معمل برادات الماء
# ==========================================

st.sidebar.title("❄️ معمل برادات الماء")
menu = st.sidebar.radio(
    "القائمة الرئيسية:",
    ["الرئيسية (لوحة التحكم)", "خط إنتاج برادات الماء", "مخزن المواد الخام (28 مادة)", "الحسابات والسندات"]
)

# --- 1. لوحة التحكم ---
if menu == "الرئيسية (لوحة التحكم)":
    st.title("📊 لوحة تحكم المعمل")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي برادات الماء المصنعة", f"{st.session_state.produced_coolers} براد")
    col2.metric("أنواع المواد الخام المسجلة", f"{len(st.session_state.inventory)} مادة")
    col3.metric("حالة خط الإنتاج", "جاهز للعمل 🟢")

    st.divider()
    st.subheader("📋 خريطة استهلاك براد الماء الموحد (28 مادة خام)")
    bom_df = pd.DataFrame([
        {"المادة الخام": k, "الكمية المطلوبة للبراد الواحد": v} for k, v in st.session_state.cooler_bom.items()
    ])
    st.dataframe(bom_df, use_container_width=True)

# --- 2. خط الإنتاج (تصنيع برادات الماء وخصم المواد الـ 28 تلقائياً) ---
elif menu == "خط إنتاج برادات الماء":
    st.title("🏭 خط إنتاج وتجميع برادات الماء")
    st.write("عند تحديد عدد البرادات المطلوبة للإنتاج، سيقوم النظام بالتحقق من المواد الخام الـ 28 وخصمها أوتوماتيكياً من المخزن.")

    c1, c2 = st.columns([2, 1])
    with c1:
        coolers_to_make = st.number_input("أدخل عدد برادات الماء المراد تصنيعها الآن:", min_value=1, value=5, step=1)
    
    with c2:
        st.write("")
        st.write("")
        start_btn = st.button("🚀 البدء بتصنيع البرادات", type="primary")

    if start_btn:
        # فحص توفر المواد الـ 28
        missing_materials = []
        for mat_name, req_qty_per_unit in st.session_state.cooler_bom.items():
            total_needed = req_qty_per_unit * coolers_to_make
            # البحث في المخزون
            stock_item = next((item for item in st.session_state.inventory if item["المادة الخام"] == mat_name), None)
            
            if not stock_item or stock_item["الكمية بالمخزن"] < total_needed:
                available = stock_item["الكمية بالمخزن"] if stock_item else 0
                missing_materials.append(f"- {mat_name}: المطلوب {total_needed}، المتاح بالمخزن {available}")

        if missing_materials:
            st.error("❌ لا يمكن البدء بالإنتاج! هناك نقص في بعض المواد الخام الـ 28 التالية:")
            for m in missing_materials:
                st.write(m)
        else:
            # خصم كافة المواد الـ 28
            for mat_name, req_qty_per_unit in st.session_state.cooler_bom.items():
                total_needed = req_qty_per_unit * coolers_to_make
                stock_item = next(item for item in st.session_state.inventory if item["المادة الخام"] == mat_name)
                stock_item["الكمية بالمخزن"] -= total_needed

            st.session_state.produced_coolers += coolers_to_make
            st.balloons()
            st.success(f"🎉 تم تصنيع ({coolers_to_make}) براد ماء بنجاح! وتم خصم جميع المواد الخام الـ 28 من المخزن بنجاح.")

# --- 3. إدارة مخزن المواد الخام الـ 28 ---
elif menu == "مخزن المواد الخام (28 مادة)":
    st.title("🏗️ مخزن المواد الخام والمكونات")
    
    # إضافة مادة خام جديدة إن لزم الأمر
    with st.expander("➕ إضافة أو توريد شحنة مواد خام"):
        with st.form("add_mat_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                new_mat = st.text_input("اسم المادة الخام")
            with col_b:
                new_qty = st.number_input("الكمية الواردة", min_value=1, value=50)
            with col_c:
                new_unit = st.text_input("الوحدة (قطعة / متر / كغم...)", value="قطعة")
            
            if st.form_submit_button("حفظ الشحنة"):
                if new_mat.strip():
                    # فحص إن كانت موجودة مسبقاً لإضافة الكمية
                    existing = next((item for item in st.session_state.inventory if item["المادة الخام"] == new_mat), None)
                    if existing:
                        existing["الكمية بالمخزن"] += new_qty
                    else:
                        st.session_state.inventory.append({"المادة الخام": new_mat, "الكمية بالمخزن": new_qty, "الوحدة": new_unit})
                    st.success(f"تم تحديث مخزون {new_mat} بنجاح!")
                    st.rerun()

    st.subheader("📋 جدول كميات المواد الخام الحالية بالمخزن")
    st.dataframe(pd.DataFrame(st.session_state.inventory), use_container_width=True)

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
