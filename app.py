import os
import requests
import streamlit as st
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الصفحة والنظام ---
st.set_page_config(page_title="نظام إدارة معمل برادات الماء الشامل", layout="wide")

# --- 1. تهيئة ذاكرة المواد الخام ---
if "raw_materials" not in st.session_state:
    st.session_state.raw_materials = {}

# --- 2. تهيئة ذاكرة موديلات البرادات ---
if "product_models" not in st.session_state:
    st.session_state.product_models = {}

# --- 3. تهيئة ذاكرة الوكلاء (الاسم، الرصيد السابق/الدين) ---
if "agents" not in st.session_state:
    st.session_state.agents = {
        "معرض البركة للتجارة": {"balance": 1500.0, "phone": "07700000000"}  # balance موجب = دين على الوكيل
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

# --- دالة إنشاء (سند قبض وموقف مالي للوكيل) PDF ---
def generate_receipt_pdf(agent_name, paid_amount, prev_balance, new_balance):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    pdf.set_font("Amiri", "", 22)
    pdf.set_xy(10, 10)
    pdf.cell(190, 10, ar("سند قبض وموقف مالي"), align="C")

    pdf.set_font("Amiri", "", 12)

    # تفاصيل المستند
    y = 25
    pdf.set_xy(10, y)
    pdf.cell(190, 10, ar(f"استلمنا من السيد / الوكيل: {agent_name}"), border=1, align="R")
    
    y += 12
    pdf.set_xy(10, y)
    pdf.cell(190, 10, ar(f"المبلغ المسدد حالياً: ${paid_amount:,.2f}"), border=1, align="R")

    # جدول الحسابات
    y += 15
    pdf.set_xy(105, y)
    pdf.cell(65, 10, ar(f"${prev_balance:,.2f}"), border=1, align="C")
    pdf.cell(30, 10, ar("الرصيد السابق"), border=1, align="C")

    pdf.set_xy(10, y)
    pdf.cell(65, 10, ar(f"${paid_amount:,.2f}"), border=1, align="C")
    pdf.cell(30, 10, ar("المبلغ الواصل"), border=1, align="C")

    y += 10
    pdf.set_xy(105, y)
    pdf.cell(65, 10, ar(f"${new_balance:,.2f}"), border=1, align="C")
    pdf.cell(30, 10, ar("الرصيد المتبقي (الدين)"), border=1, align="C")

    pdf_out = pdf.output()
    return bytes(pdf_out) if not isinstance(pdf_out, str) else pdf_out.encode('latin1')

# --- دالة إنشاء (قائمة حسابات / فاتورة بضاعة) PDF ---
def generate_invoice_pdf(agent_name, items_list, grand_total):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='P', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    pdf.set_font("Amiri", "", 20)
    pdf.cell(130, 10, ar("قائمة حساب بضاعة (فاتورة مبيعات)"), align="C", ln=True)
    pdf.set_font("Amiri", "", 12)
    pdf.cell(130, 8, ar(f"الوكيل: {agent_name}"), ln=True, align="R")
    pdf.ln(4)

    # عناوين الجدول
    pdf.cell(30, 8, ar("الإجمالي ($)"), border=1, align="C")
    pdf.cell(30, 8, ar("السعر ($)"), border=1, align="C")
    pdf.cell(20, 8, ar("الكمية"), border=1, align="C")
    pdf.cell(50, 8, ar("الموديل / التفاصيل"), border=1, align="C")
    pdf.ln()

    # عناصر الفاتورة
    for item in items_list:
        pdf.cell(30, 8, ar(f"${item['total']:,.2f}"), border=1, align="C")
        pdf.cell(30, 8, ar(f"${item['price']:,.2f}"), border=1, align="C")
        pdf.cell(20, 8, ar(str(item['qty'])), border=1, align="C")
        pdf.cell(50, 8, ar(item['model']), border=1, align="C")
        pdf.ln()

    pdf.set_font("Amiri", "", 12)
    pdf.cell(80, 10, ar(f"${grand_total:,.2f}"), border=1, align="C")
    pdf.cell(50, 10, ar("إجمالي القائمة الكلي"), border=1, align="C")

    pdf_out = pdf.output()
    return bytes(pdf_out) if not isinstance(pdf_out, str) else pdf_out.encode('latin1')


# ==========================================
#     واجهة نظام إدارة معمل برادات الماء
# ==========================================

st.sidebar.title("⚙️ نظام المعمل الشامل")

if st.sidebar.button("🗑️ مسح وتفريغ كل البيانات الافتراضية", type="secondary"):
    st.session_state.raw_materials = {}
    st.session_state.product_models = {}
    st.session_state.agents = {}
    st.sidebar.success("تم مسح كافة البيانات بنجاح!")
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "القائمة الرئيسية:",
    [
        "الرئيسية (لوحة التحكم)", 
        "إدارة الوكلاء والمبيعات 🤝", 
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
    tot_agents = len(st.session_state.agents)
    tot_debts = sum(a["balance"] for a in st.session_state.agents.values()) if st.session_state.agents else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("المواد الخام المسجلة", f"{tot_raw_types} مادة")
    col2.metric("أنواع البرادات المصممة", f"{tot_models} موديل")
    col3.metric("عدد الوكلاء المسجلين", f"{tot_agents} وكيل")
    col4.metric("إجمالي الديون على الوكلاء", f"${tot_debts:,.2f}")

# --- 2. إدارة الوكلاء والمبيعات (الجديدة) ---
elif menu == "إدارة الوكلاء والمبيعات 🤝":
    st.title("🤝 إدارة الوكلاء والمبيعات وإصدار الفواتير والسندات")

    tab1, tab2, tab3 = st.tabs(["🛒 عملية بيع جديدة وتصدير القوائم", "👥 إضافة وإدارة سجل الوكلاء", "📋 كشف حسابات الديون"])

    # 🛒 1. عملية بيع جديدة
    with tab1:
        st.subheader("🛒 تسجيل عملية بيع بضاعة لوكيل")
        if not st.session_state.agents:
            st.warning("⚠️ لا يوجد وكلاء مسجلون! أضف وكيلاً أولاً من تبويب 'إضافة وإدارة سجل الوكلاء'.")
        elif not st.session_state.product_models:
            st.warning("⚠️ لا توجد موديلات برادات مسجلة للبيع!")
        else:
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                selected_agent = st.selectbox("اختر الوكيل:", options=list(st.session_state.agents.keys()))
                agent_curr_balance = st.session_state.agents[selected_agent]["balance"]
                st.info(f"💰 الرصيد الحالي للوكيل قبل الشراء: **${agent_curr_balance:,.2f}** ({'دَين عليه' if agent_curr_balance >= 0 else 'رصيد له'})")
            
            st.divider()
            st.write("📦 **تحديد البضاعة المبيعة:**")

            if "cart" not in st.session_state:
                st.session_state.cart = []

            col_m1, col_m2, col_m3, col_m4 = st.columns([3, 2, 2, 1])
            with col_m1:
                p_model = st.selectbox("موديل البراد:", options=list(st.session_state.product_models.keys()))
            with col_m2:
                available_stock = st.session_state.product_models[p_model]["stock"]
                p_qty = st.number_input("الكمية المبيعة:", min_value=1, max_value=max(1, available_stock), value=1)
                st.caption(f"المتاح بالمخزن: {available_stock} قطعة")
            with col_m3:
                p_price = st.number_input("سعر البراد الواحد ($):", min_value=0.0, value=150.0, step=10.0)
            with col_m4:
                st.write("")
                st.write("")
                if st.button("➕ إضافة للفاتورة"):
                    if available_stock >= p_qty:
                        st.session_state.cart.append({
                            "model": p_model,
                            "qty": p_qty,
                            "price": p_price,
                            "total": p_qty * p_price
                        })
                        st.success("تمت الإضافة للفاتورة!")
                    else:
                        st.error("الكمية المطلوبة غير متوفرة في مخزن البرادات!")

            # عرض قائمة البضاعة في السلة
            if st.session_state.cart:
                st.write("---")
                st.subheader("📋 سلة البضاعة المحددة للفاتورة:")
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df, use_container_width=True)

                grand_total = sum(item["total"] for item in st.session_state.cart)
                st.success(f"💵 **إجمالي قيمة البضاعة المبيعة:** **${grand_total:,.2f}**")

                st.divider()
                # التسديد والموقف المالي
                col_pay1, col_pay2 = st.columns(2)
                with col_pay1:
                    paid_now = st.number_input("المبلغ المسدد نقداً من الوكيل الآن ($):", min_value=0.0, value=grand_total)
                
                new_balance = agent_curr_balance + grand_total - paid_now
                with col_pay2:
                    st.write("")
                    st.warning(f"⚖️ **الرصيد المتبقي النهائي على الوكيل بعد هذه البيعة:** **${new_balance:,.2f}**")

                if st.button("✅ إتمام عملية البيع وتحديث الحسابات والمخزن", type="primary"):
                    # 1. خصم البرادات من مخزن المعمل
                    for item in st.session_state.cart:
                        st.session_state.product_models[item["model"]]["stock"] -= item["qty"]
                    
                    # 2. تحديث دَين الوكيل
                    prev_bal = st.session_state.agents[selected_agent]["balance"]
                    st.session_state.agents[selected_agent]["balance"] = new_balance

                    st.balloons()
                    st.success("🎉 تم تسجيل عملية البيع وخصم البضاعة من المخزن وتحديث رصيد الوكيل بنجاح!")

                    # إنشاء الوصلين (سند قبض + قائمة حسابات)
                    pdf_receipt = generate_receipt_pdf(selected_agent, paid_now, prev_bal, new_balance)
                    pdf_invoice = generate_invoice_pdf(selected_agent, st.session_state.cart, grand_total)

                    st.subheader("🖨️ طباعة المستندات المزدوجة:")
                    col_pdf1, col_pdf2 = st.columns(2)
                    with col_pdf1:
                        st.download_button(
                            label="📄 تحميل سند قبض وموقف مالي (PDF)",
                            data=pdf_receipt,
                            file_name=f"Sanad_Qabd_{selected_agent}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    with col_pdf2:
                        st.download_button(
                            label="🧾 تحميل قائمة حسابات البضاعة (PDF)",
                            data=pdf_invoice,
                            file_name=f"Invoice_{selected_agent}.pdf",
                            mime="application/pdf"
                        )

                    # تفريغ السلة
                    st.session_state.cart = []

    # 👥 2. إضافة وإدارة سجل الوكلاء
    with tab2:
        st.subheader("➕ إضافة وكيل جديد")
        with st.form("add_agent_form", clear_on_submit=True):
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                ag_name = st.text_input("اسم الوكيل / المعرض")
            with col_a2:
                ag_phone = st.text_input("رقم الهاتف")
            with col_a3:
                ag_balance = st.number_input("الرصيد السابق ($) [موجب = دين عليه، سالب = طلب له]", value=0.0)

            if st.form_submit_button("حفظ الوكيل"):
                if ag_name.strip():
                    st.session_state.agents[ag_name] = {"balance": ag_balance, "phone": ag_phone}
                    st.success(f"تم حفظ الوكيل ({ag_name}) بنجاح!")
                    st.rerun()

        st.divider()
        st.subheader("🗑️ حذف / تعديل بيانات وكيل")
        if st.session_state.agents:
            ag_to_del = st.selectbox("اختر الوكيل للتعديل أو الحذف:", options=list(st.session_state.agents.keys()))
            if st.button("🗑️ حذف هذا الوكيل", type="primary"):
                del st.session_state.agents[ag_to_del]
                st.success("تم الحذف بنجاح!")
                st.rerun()

    # 📋 3. كشف حسابات الديون
    with tab3:
        st.subheader("📊 كشف الديون والأرصدة الحالية لجميع الوكلاء")
        if st.session_state.agents:
            agent_data = [
                {"اسم الوكيل": k, "رقم الهاتف": v["phone"], "الرصيد المتبقي / الدين ($)": f"${v['balance']:,.2f}"}
                for k, v in st.session_state.agents.items()
            ]
            st.dataframe(pd.DataFrame(agent_data), use_container_width=True)
        else:
            st.info("لا يوجد وكلاء مسجلون حالياً.")

# --- 3. إدارة المواد الخام ---
elif menu == "إدارة المواد الخام (المخزن)":
    st.title("🏗️ إدارة المواد الخام بالمخزن")
    # (نفس الكود الخاص بالخام)
    col_a, col_b = st.columns(2)
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

    if st.session_state.raw_materials:
        raw_df = pd.DataFrame([
            {"اسم المادة الخام": k, "الكمية المتاحة": v["qty"], "الوحدة": v["unit"]} 
            for k, v in st.session_state.raw_materials.items()
        ])
        st.dataframe(raw_df, use_container_width=True)

# --- 4. إدارة موديلات البرادات ---
elif menu == "إدارة موديلات البرادات":
    st.title("📐 تصميم وتعديل وحذف موديلات البرادات")
    with st.expander("➕ إضافة موديل براد جديد وتحديد معايير تصنيعه", expanded=True):
        new_model_name = st.text_input("اسم موديل البراد الجديد")
        selected_recipe = {}
        if st.session_state.raw_materials:
            cols = st.columns(2)
            for idx, (mat, data) in enumerate(st.session_state.raw_materials.items()):
                col = cols[idx % 2]
                use_it = col.checkbox(f"استهلاك: {mat} ({data['unit']})", value=False, key=f"chk_{mat}")
                if use_it:
                    qty_needed = col.number_input(f"الكمية لـ ({mat}):", min_value=0.1, value=1.0, step=0.5, key=f"num_{mat}")
                    selected_recipe[mat] = qty_needed

        if st.button("حفظ الموديل الجديد", type="primary"):
            if new_model_name.strip() and selected_recipe:
                st.session_state.product_models[new_model_name] = {"recipe": selected_recipe, "stock": 0}
                st.success(f"🎉 تم حفظ الموديل ({new_model_name}) بنجاح!")
                st.rerun()

    if st.session_state.product_models:
        for model_name, info in list(st.session_state.product_models.items()):
            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                with st.expander(f"🔹 موديل: {model_name} (المخزون الحالي: {info['stock']} قطعة)"):
                    st.json(info["recipe"])
            with col_m2:
                if st.button(f"🗑️ حذف {model_name}", key=f"del_{model_name}", type="primary"):
                    del st.session_state.product_models[model_name]
                    st.rerun()

# --- 5. خط الإنتاج ---
elif menu == "خط الإنتاج والتصنيع":
    st.title("🏭 خط الإنتاج الفعلي")
    if st.session_state.product_models:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            selected_model = st.selectbox("اختر الموديل:", options=list(st.session_state.product_models.keys()))
        with col_p2:
            qty_to_build = st.number_input("العدد المطلوب تصنيعه:", min_value=1, value=5)

        recipe = st.session_state.product_models[selected_model]["recipe"]
        req_df_list = []
        can_produce = True
        
        for mat, amount_per_unit in recipe.items():
            tot_req = amount_per_unit * qty_to_build
            available = st.session_state.raw_materials.get(mat, {}).get("qty", 0)
            status = "✅ متوفر" if available >= tot_req else "❌ غير كافٍ"
            if available < tot_req:
                can_produce = False
            req_df_list.append({"المادة الخام": mat, "إجمالي المطلوب": tot_req, "المتاح بالمخزن": available, "الحالة": status})
            
        st.dataframe(pd.DataFrame(req_df_list), use_container_width=True)

        if st.button("🚀 بدء تصنيع الطلبية", type="primary"):
            if can_produce:
                for mat, amount_per_unit in recipe.items():
                    st.session_state.raw_materials[mat]["qty"] -= amount_per_unit * qty_to_build
                st.session_state.product_models[selected_model]["stock"] += qty_to_build
                st.balloons()
                st.success("تم التصنيع بنجاح!")
                st.rerun()

# --- 6. الحسابات والسندات الورقية العامة ---
elif menu == "الحسابات والسندات":
    st.title("💰 قسم الحسابات والسندات")
    st.subheader("📄 نموذج سند قبض ورقي فارغ")
    st.write("يمكنك طباعة سند فارغ تماماً للتعامل اليدوي المباشر.")
