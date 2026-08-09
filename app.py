from datetime import datetime
import io
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات وتخطيط الصفحة ---
st.set_page_config(
    page_title="معاش - نظام إدارة معمل البرادات",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- تنسيقات CSS ---
st.markdown(
    """
<style>
    .stApp {
        background-color: #0b1120;
        color: #f1f5f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    div[data-testid="stMetric"] {
        background-color: #162032 !important;
        border: 1px solid #23324d !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 1.3rem !important;
    }
    .stSelectbox > div > div, .stTextInput input, .stNumberInput input {
        background-color: #111827 !important;
        color: #ffffff !important;
        border: 1px solid #2d3e5d !important;
        border-radius: 8px !important;
        text-align: right !important;
        direction: rtl !important;
    }
    #MainMenu, footer, header {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "maash_factory_data.json"


def get_default_data():
    return {
        "inventory": {},  # المواد الخام
        "bom": {},  # وصفة مواد البراد (ما يحتاجه كل براد)
        "finished_goods": {},  # البرادات الجاهزة بالمخزن
        "agents": {},  # الوكلاء وديونهم
        "sales_history": [],  # سجل المبيعات
        "production_history": [],  # سجل الإنتاج
        "receipt_counter": 1001,
    }


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return get_default_data()
    return get_default_data()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


db = load_data()

st.markdown(
    "<h2 style='text-align: center; color: #ffffff;'>🍏 نظام معاش لإدارة معمل"
    " البرادات</h2>",
    unsafe_allow_html=True,
)
st.divider()

# --- القائمة الرئيسية للتنقل ---
tabs = st.tabs([
    "📦 المواد الخام",
    "🛠️ وصفات البرادات (BOM)",
    "🏭 الإنتاج والتصنيع",
    "🤝 الوكلاء والديون",
    "🛒 المبيعات والفواتير",
    "📊 التقارير المالية",
])

# -------------------------------------------------------------
# 1. إدخال وإدارة المواد الخام
# -------------------------------------------------------------
with tabs[0]:
    st.markdown("### 📦 إدارة المخزون من المواد الخام")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### إضافة مادة خام جديدة أو تحديث رصيد")
        mat_name = st.text_input("اسم المادة الخام:")
        mat_qty = st.number_input(
            "الكمية الواردة:", min_value=0.0, step=1.0, value=0.0
        )
        if st.button("➕ حفظ وإضافة للمخزن", type="primary"):
            if mat_name:
                db["inventory"][mat_name] = (
                    db["inventory"].get(mat_name, 0.0) + mat_qty
                )
                save_data(db)
                st.success(f"تم تحديث مخزون '{mat_name}' بنجاح!")
                st.rerun()
            else:
                st.warning("يرجى إدخال اسم المادة.")

    with col2:
        st.markdown("#### المواد الخام الحالية بالمخزن")
        if db["inventory"]:
            inv_df = pd.DataFrame(
                list(db["inventory"].items()),
                columns=["المادة الخام", "الكمية المتوفرة"],
            )
            st.dataframe(inv_df, use_container_width=True)
        else:
            st.info("لا توجد مواد خام مسجلة بعد.")

# -------------------------------------------------------------
# 2. وصفات تصنيع البرادات (BOM)
# -------------------------------------------------------------
with tabs[1]:
    st.markdown("### 🛠️ تحديد احتياجات كل براد من المواد الخام")

    if not db["inventory"]:
        st.warning("الرجاء إضافة مواد خام أولاً لكي تتمكن من اختيارها للبراد.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            model_name = st.text_input("اسم نموذج البراد (مثال: براد حنفية):")
            st.markdown("#### المواد المطلوبة لتصنيع وحدة واحدة:")

            if "temp_bom" not in st.session_state:
                st.session_state.temp_bom = {}

            selected_mat = st.selectbox(
                "اختر مادة خام:", list(db["inventory"].keys())
            )
            needed_qty = st.number_input(
                "الكمية المطلوبة للوحدة:", min_value=0.1, value=1.0
            )

            if st.button("➕ إضافة المادة للوصفة"):
                st.session_state.temp_bom[selected_mat] = needed_qty
                st.success(f"تمت إضافة {selected_mat} للوصفة.")

            if st.session_state.temp_bom:
                st.write(
                    "**المواد المحددة للبراد حتى الآن:**",
                    st.session_state.temp_bom,
                )
                if st.button("💾 حفظ وصفة البراد النهائية", type="primary"):
                    if model_name:
                        db["bom"][model_name] = st.session_state.temp_bom
                        db["finished_goods"].setdefault(model_name, 0)
                        save_data(db)
                        st.session_state.temp_bom = {}
                        st.success(f"تم حفظ وصفة البراد '{model_name}' بنجاح!")
                        st.rerun()
                    else:
                        st.warning("يرجى إدخال اسم نموذج البراد.")

        with col2:
            st.markdown("#### النماذج والوصفات المحفوظة")
            if db["bom"]:
                st.json(db["bom"])
            else:
                st.info("لم يتم إعداد أي وصفة براد بعد.")

# -------------------------------------------------------------
# 3. الإنتاج والتصنيع (خصم تلقائي من المخزن)
# -------------------------------------------------------------
with tabs[2]:
    st.markdown("### 🏭 تسجيل وجبة إنتاج برادات")

    if not db["bom"]:
        st.info("الرجاء تحديد وصفات البرادات (BOM) أولاً.")
    else:
        prod_model = st.selectbox("اختر نموذج البراد للتصنيع:", list(db["bom"].keys()))
        prod_count = st.number_input(
            "عدد الوحدات المراد إنتاجها:", min_value=1, value=1
        )

        # التحقق من توفر المواد الخام
        bom_recipe = db["bom"][prod_model]
        can_produce = True
        missing_materials = []

        for mat, req in bom_recipe.items():
            total_req = req * prod_count
            available = db["inventory"].get(mat, 0.0)
            if available < total_req:
                can_produce = False
                missing_materials.append(
                    f"{mat} (المطلوب: {total_req} | المتوفر: {available})"
                )

        if not can_produce:
            st.error(
                "⚠️ لا يمكن إتمام الإنتاج لنقص المواد الخام التالية في المخزن:"
            )
            for m in missing_materials:
                st.write(f"- {m}")
        else:
            st.success("✅ جميع المواد الخام متوفرة وكافية للإنتاج.")
            if st.button("🚀 تأكيد الإنتاج وخصم المواد الخام", type="primary"):
                # خصم المواد الخام
                for mat, req in bom_recipe.items():
                    db["inventory"][mat] -= req * prod_count
                # زيادة عدد البرادات الجاهزة
                db["finished_goods"][prod_model] = (
                    db["finished_goods"].get(prod_model, 0) + prod_count
                )
                # تسجيل العملية
                db["production_history"].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "model": prod_model,
                    "qty": prod_count,
                })
                save_data(db)
                st.success("تم الإنتاج بنجاح وتحديث أرصدة المخزن!")
                st.rerun()

# -------------------------------------------------------------
# 4. الوكلاء والديون
# -------------------------------------------------------------
with tabs[3]:
    st.markdown("### 🤝 إدارة الوكلاء والحسابات والديون")
    sub_t1, sub_t2 = st.tabs(["إضافة وكيل جديد", "كشف حساب وتسديدات"])

    with sub_t1:
        agent_name = st.text_input("اسم الوكيل / المحل:")
        agent_phone = st.text_input("رقم الهاتف:")
        initial_debt = st.number_input(
            "الدين أو الرصيد السابق (إن وجدت):", min_value=0.0, step=10000.0
        )

        if st.button("➕ حفظ الوكيل", type="primary"):
            if agent_name:
                db["agents"][agent_name] = {
                    "phone": agent_phone,
                    "debt": initial_debt,
                    "transactions": [],
                }
                save_data(db)
                st.success("تم إضافة الوكيل بنجاح!")
                st.rerun()
            else:
                st.warning("يرجى إدخال اسم الوكيل.")

    with sub_t2:
        if db["agents"]:
            selected_agent = st.selectbox(
                "اختر الوكيل:", list(db["agents"].keys())
            )
            ag_data = db["agents"][selected_agent]
            st.info(f"الذمة المالية الحالية على الوكيل: **{ag_data['debt']:,} د.ع**")

            pay_amt = st.number_input(
                "مبلغ التسديد الواصل:", min_value=0.0, step=10000.0
            )
            if st.button("💵 تثبيت التسديد وإصدار وصل قبض"):
                ag_data["debt"] -= pay_amt
                receipt_no = db["receipt_counter"]
                db["receipt_counter"] += 1

                ag_data["transactions"].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "تسديد",
                    "amount": pay_amt,
                    "balance": ag_data["debt"],
                })
                save_data(db)
                st.success(
                    f"تم تسجيل التسديد بنجاح! الرصيد المتبقي: {ag_data['debt']:,} د.ع"
                )

                # عرض وصل القبض
                st.markdown(
                    f"""
                <div style="background: #ffffff; color: #1e293b; padding: 20px; border-radius: 10px; border-top: 5px solid #059669; margin-top: 15px;">
                    <h3>وصل قبض نقدي #{receipt_no}</h3>
                    <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                    <p><b>اسم الوكيل:</b> {selected_agent}</p>
                    <p><b>المبلغ الواصل:</b> {pay_amt:,} د.ع</p>
                    <p><b>المتبقي بالذمة:</b> {ag_data['debt']:,} د.ع</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("لا يوجد وكلاء مسجلون.")

# -------------------------------------------------------------
# 5. المبيعات والفواتير (عميل مباشر أو وكيل)
# -------------------------------------------------------------
with tabs[4]:
    st.markdown("### 🛒 نقطة بيع البرادات وإصدار الفواتير")

    buyer_type = st.radio(
        "نوع المشتري:", ["عميل مباشر", "وكيل مسجل"], horizontal=True
    )

    buyer_name = ""
    if buyer_type == "عميل مباشر":
        buyer_name = st.text_input("اسم العميل المباشر:")
        payment_method = st.selectbox("طريقة البيع:", ["مباشر (نقداً)", "أقساط"])
    else:
        if db["agents"]:
            buyer_name = st.selectbox("اختر الوكيل:", list(db["agents"].keys()))
        else:
            st.warning("لا توجد وكلاء مسجلين.")

    st.markdown("#### تحديد المنتجات المباعة:")
    cart_items = []
    total_invoice = 0

    if db["finished_goods"]:
        for model, stock in db["finished_goods"].items():
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"**{model}** (المتوفر بالمخزن: {stock})")
            with c2:
                q = st.number_input(
                    "العدد:", min_value=0, max_value=max(0, stock), key=f"s_{model}"
                )
            with c3:
                p = st.number_input(
                    "السعر للقطعة:", min_value=0.0, key=f"p_{model}"
                )

            if q > 0:
                t = q * p
                total_invoice += t
                cart_items.append({"model": model, "qty": q, "price": p, "total": t})

        st.markdown(f"#### الإجمالي الكلي للفاتورة: `{total_invoice:,}` د.ع")

        if st.button("📄 إتمام البيع وإصدار قائمة الحساب", type="primary"):
            if buyer_name and cart_items:
                receipt_no = db["receipt_counter"]
                db["receipt_counter"] += 1

                # خصم المخزن الجاهز
                for item in cart_items:
                    db["finished_goods"][item["model"]] -= item["qty"]

                # لو كان وكيل، يضاف المبلغ إلى دينه
                if buyer_type == "وكيل مسجل":
                    db["agents"][buyer_name]["debt"] += total_invoice
                    db["agents"][buyer_name]["transactions"].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "type": "شراء بضاعة",
                        "amount": total_invoice,
                        "balance": db["agents"][buyer_name]["debt"],
                    })

                db["sales_history"].append({
                    "receipt_no": receipt_no,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "buyer": buyer_name,
                    "type": buyer_type,
                    "total": total_invoice,
                })
                save_data(db)

                st.success("تم إتمام عملية البيع بنجاح وتحديث السجلات!")

                # عرض قائمة الحساب والفاتورة للطباعة
                invoice_rows = "".join(
                    [
                        f"<tr><td>{i['model']}</td><td>{i['qty']}</td><td>{i['price']:,} د.ع</td><td><b>{i['total']:,} د.ع</b></td></tr>"
                        for i in cart_items
                    ]
                )
                st.markdown(
                    f"""
                <div style="background: #ffffff; color: #1e293b; padding: 25px; border-radius: 12px; border-top: 6px solid #0284c7; margin-top: 20px; direction: rtl;">
                    <h3>قائمة حساب / مبيعات #{receipt_no}</h3>
                    <p><b>اسم المشتري:</b> {buyer_name} ({buyer_type})</p>
                    <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;"><th style="padding: 8px; text-align: right;">المنتج</th><th style="padding: 8px; text-align: right;">العدد</th><th style="padding: 8px; text-align: right;">السعر المفرد</th><th style="padding: 8px; text-align: right;">الإجمالي</th></tr>
                        {invoice_rows}
                    </table>
                    <h4 style="text-align: left; margin-top: 15px; color: #059669;">المبلغ الإجمالي: {total_invoice:,} د.ع</h4>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("يرجى إدخال اسم المشتري وتحديد منتج واحد على الأقل.")
    else:
        st.info("لا توجد برادات جاهزة بالمخزن حالياً للبيع.")

# -------------------------------------------------------------
# 6. التقارير المالية
# -------------------------------------------------------------
with tabs[5]:
    st.markdown("### 📊 التقارير العامة وسجل المبيعات")
    if db["sales_history"]:
        st.dataframe(pd.DataFrame(db["sales_history"]), use_container_width=True)
    else:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
