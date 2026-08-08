import os
import requests
import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة معمل برادات الماء الشامل", layout="wide")

# --- 1. تهيئة ذاكرة المخزون الديناميكي (المواد الخام) ---
if "raw_materials" not in st.session_state:
    st.session_state.raw_materials = {
        "ضغاط (كومبريسور)": {"qty": 50, "unit": "قطعة"},
        "مكثف (شبك تبريد)": {"qty": 50, "unit": "قطعة"},
        "مبخر (مبرد الخزان)": {"qty": 50, "unit": "قطعة"},
        "خزان استيل ماء بارد": {"qty": 50, "unit": "قطعة"},
        "خزان ماء حار": {"qty": 50, "unit": "قطعة"},
        "حنفية ماء بارد": {"qty": 100, "unit": "قطعة"},
        "حنفية ماء حار (أمان)": {"qty": 100, "unit": "قطعة"}
    }

# --- 2. تهيئة أنواع البرادات المُنتجة ---
if "product_models" not in st.session_state:
    st.session_state.product_models = {
        "براد ماء قياسي": {
            "recipe": {"ضغاط (كومبريسور)": 1, "مكثف (شبك تبريد)": 1, "حنفية ماء بارد": 1},
            "stock": 0
        }
    }

# --- دالة معالجة النصوص العربية للـ PDF ---
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

st.sidebar.title("⚙️ نظام المعمل الشامل")

# زر لتصفير وشطب كافة البيانات الافتراضية
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ مسح وتفريغ كل البيانات الافتراضية", type="secondary"):
    st.session_state.raw_materials = {}
    st.session_state.product_models = {}
    st.sidebar.success("تم مسح كافة المواد والموديلات بنجاح!")
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "القائمة الرئيسية:",
    [
        "الرئيسية (لوحة التحكم)", 
        "إدارة المواد الخام (المخزن)", 
        "إدارة موديلات البرادات", 
        "خط الإنتاج والتصنيع", 
        "الحسابات والسندات"
    ]
)

# --- 1. الرئيسية ---
if menu == "الرئيسية (لوحة التحكم)":
    st.title("📊 لوحة تحكم المعمل الشاملة")
    
    tot_raw_types = len(st.session_state.raw_materials)
    tot_models = len(st.session_state.product_models)
    tot_produced = sum(m["stock"] for m in st.session_state.product_models.values()) if st.session_state.product_models else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("المواد الخام المسجلة", f"{tot_raw_types} مادة")
    col2.metric("أنواع البرادات المصممة", f"{tot_models} موديل")
    col3.metric("إجمالي البرادات الجاهزة بالمخزن", f"{tot_produced} براد")

    st.divider()
    st.subheader("📦 مخزون البرادات المصنعة الحالي")
    if st.session_state.product_models:
        prod_data = [{"نوع البراد / الموديل": k, "الكمية الجاهزة بالمخزن": v["stock"]} for k, v in st.session_state.product_models.items()]
        st.dataframe(pd.DataFrame(prod_data), use_container_width=True)
    else:
        st.info("لا توجد موديلات برادات مسجلة حالياً.")

# --- 2. إدارة المواد الخام (إضافة / تعديل / حذف) ---
elif menu == "إدارة المواد الخام (المخزن)":
    st.title("🏗️ إدارة المواد الخام بالمخزن")

    col_a, col_b = st.columns(2)
    
    # ➕ إضافة مادة خام جديدة
    with col_a:
        with st.expander("➕ إضافة مادة خام جديدة", expanded=True):
            with st.form("add_mat_form", clear_on_submit=True):
                m_name = st.text_input("اسم المادة الخام الجديدة")
                m_qty = st.number_input("الكمية الأولية", min_value=0, value=100)
                m_unit = st.text_input("الوحدة (قطعة / متر / كغم...)", value="قطعة")
                if st.form_submit_button("إضافة للمخزن"):
                    if m_name.strip():
                        st.session_state.raw_materials[m_name] = {"qty": m_qty, "unit": m_unit}
                        st.success(f"تمت إضافة ({m_name}) بنجاح!")
                        st.rerun()

    # 🗑️ تعديل أو حذف مادة خام
    with col_b:
        with st.expander("🛠️ تعديل أو حذف مادة خام", expanded=True):
            if st.session_state.raw_materials:
                selected_mat = st.selectbox("اختر المادة الخام:", options=list(st.session_state.raw_materials.keys()))
                new_qty_val = st.number_input("الكمية الجديدة بالمخزن:", value=st.session_state.raw_materials[selected_mat]["qty"])
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("تحديث الكمية"):
                    st.session_state.raw_materials[selected_mat]["qty"] = new_qty_val
                    st.success("تم التحديث!")
                    st.rerun()
                if c_btn2.button("🗑️ حذف هذه المادة", type="primary"):
                    del st.session_state.raw_materials[selected_mat]
                    st.success("تم حذف المادة بنجاح!")
                    st.rerun()
            else:
                st.info("المخزن فارغ حالياً من المواد الخام.")

    st.subheader("📋 جدول المواد الخام المتوفرة حالياً")
    if st.session_state.raw_materials:
        raw_df = pd.DataFrame([
            {"اسم المادة الخام": k, "الكمية المتاحة": v["qty"], "الوحدة": v["unit"]} 
            for k, v in st.session_state.raw_materials.items()
        ])
        st.dataframe(raw_df, use_container_width=True)
    else:
        st.warning("لا توجد مواد خام في المخزن.")

# --- 3. إدارة موديلات البرادات (إضافة / حذف) ---
elif menu == "إدارة موديلات البرادات":
    st.title("📐 تصميم وتعديل وحذف موديلات البرادات")

    # 1. إضافة موديل جديد
    with st.expander("➕ إضافة موديل براد جديد وتحديد معايير تصنيعه", expanded=True):
        new_model_name = st.text_input("اسم موديل البراد الجديد")
        
        st.write("---")
        st.write("🎯 **حدد المواد الخام التي يستهلكها هذا الموديل والكمية لكل براد واحد:**")
        
        selected_recipe = {}
        if st.session_state.raw_materials:
            cols = st.columns(2)
            for idx, (mat, data) in enumerate(st.session_state.raw_materials.items()):
                col = cols[idx % 2]
                use_it = col.checkbox(f"استهلاك: {mat} ({data['unit']})", value=False, key=f"chk_{mat}")
                if use_it:
                    qty_needed = col.number_input(f"الكمية لـ ({mat}):", min_value=0.1, value=1.0, step=0.5, key=f"num_{mat}")
                    selected_recipe[mat] = qty_needed
        else:
            st.warning("⚠️ يرجى إضافة مواد خام في المخزن أولاً حتى تتمكن من تحديد مكونات البراد.")

        if st.button("حفظ الموديل الجديد", type="primary"):
            if new_model_name.strip():
                if selected_recipe:
                    st.session_state.product_models[new_model_name] = {
                        "recipe": selected_recipe,
                        "stock": 0
                    }
                    st.success(f"🎉 تم حفظ الموديل الجديد ({new_model_name}) بنجاح!")
                    st.rerun()
                else:
                    st.error("يرجى اختيار مادة خام واحدة على الأقل لإنتاج هذا الموديل.")
            else:
                st.error("يرجى إدخال اسم الموديل.")

    # 2. حذف موديل موجود
    st.divider()
    st.subheader("📋 الموديلات المسجلة حالياً وإمكانية الحذف")
    if st.session_state.product_models:
        for model_name, info in list(st.session_state.product_models.items()):
            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                with st.expander(f"🔹 موديل: {model_name} (المخزون الحالي: {info['stock']} قطعة)"):
                    st.write("**المواد الخام المستهلكة لإنتاج قطعة واحدة:**")
                    st.json(info["recipe"])
            with col_m2:
                if st.button(f"🗑️ حذف {model_name}", key=f"del_{model_name}", type="primary"):
                    del st.session_state.product_models[model_name]
                    st.success(f"تم حذف موديل ({model_name}) بنجاح!")
                    st.rerun()
    else:
        st.info("لا توجد موديلات برادات مسجلة.")

# --- 4. خط الإنتاج والتصنيع ---
elif menu == "خط الإنتاج والتصنيع":
    st.title("🏭 خط الإنتاج الفعلي")

    if not st.session_state.product_models:
        st.warning("لا توجد موديلات برادات مسجلة! قم بإضافة موديل من قسم 'إدارة موديلات البرادات'.")
    else:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            selected_model = st.selectbox("اختر الموديل المراد تصنيعه:", options=list(st.session_state.product_models.keys()))
        with col_p2:
            qty_to_build = st.number_input("العدد المطلوب تصنيعه:", min_value=1, value=5, step=1)

        recipe = st.session_state.product_models[selected_model]["recipe"]
        
        st.subheader("🔍 معاينة المواد المطلوبة لهذا أمر الإنتاج:")
        req_df_list = []
        can_produce = True
        
        for mat, amount_per_unit in recipe.items():
            tot_req = amount_per_unit * qty_to_build
            available = st.session_state.raw_materials.get(mat, {}).get("qty", 0)
            status = "✅ متوفر" if available >= tot_req else "❌ غير كافٍ"
            if available < tot_req:
                can_produce = False
            req_df_list.append({
                "المادة الخام": mat,
                "المطلوب للقطعة": amount_per_unit,
                "إجمالي المطلوب": tot_req,
                "المتاح بالمخزن": available,
                "الحالة": status
            })
            
        st.dataframe(pd.DataFrame(req_df_list), use_container_width=True)

        if st.button("🚀 بدء تصنيع الطلبية وتحديث المخزن", type="primary"):
            if not can_produce:
                st.error("❌ لا يمكن بدء الإنتاج بسبب نقص في بعض المواد الخام الموضحة أعلاه!")
            else:
                for mat, amount_per_unit in recipe.items():
                    tot_req = amount_per_unit * qty_to_build
                    st.session_state.raw_materials[mat]["qty"] -= tot_req
                
                st.session_state.product_models[selected_model]["stock"] += qty_to_build
                st.balloons()
                st.success(f"🎉 تم تصنيع {qty_to_build} قطعة من ({selected_model}) بنجاح وتم تحديث المخزن!")
                st.rerun()

# --- 5. قسم الحسابات والسندات ---
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
