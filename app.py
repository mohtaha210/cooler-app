from datetime import datetime
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات وتخطيط الصفحة ---
st.set_page_config(
    page_title="معاش - نظام إدارة معمل الرافدين للبرادات",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- تنسيقات CSS ---
st.markdown(
    """
<style>
    .stApp { background-color: #0b1120; color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 700 !important; font-size: 1.3rem !important; }
    .stSelectbox > div > div, .stTextInput input, .stNumberInput input { background-color: #111827 !important; color: #ffffff !important; border: 1px solid #2d3e5d !important; border-radius: 8px !important; text-align: right !important; direction: rtl !important; }
    #MainMenu, footer, header {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "rafidain_factory_data.json"


def get_default_data():
    return {
        "inventory": {},
        "bom": {},
        "finished_goods": {},
        "agents": {},
        "sales_history": [],
        "production_history": [],
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
    "<h2 style='text-align: center; color: #ffffff;'>🍏 نظام معاش - معمل"
    " الرافدين للبرادات</h2>",
    unsafe_allow_html=True,
)
st.divider()

tabs = st.tabs([
    "📦 المواد الخام",
    "🛠️ وصفات البرادات",
    "🏭 الإنتاج",
    "🤝 الوكلاء والديون",
    "🛒 المبيعات والفواتير",
    "📊 التقارير",
])

# 1. المواد الخام
with tabs[0]:
    st.markdown("### 📦 إدارة المخزون الخام")
    c1, c2 = st.columns(2)
    with c1:
        mat_name = st.text_input("اسم المادة الخام:", key="m_name")
        mat_qty = st.number_input(
            "الكمية الواردة:",
            min_value=0.0,
            step=1.0,
            value=0.0,
            key="m_qty",
        )
        if st.button(
            "➕ إضافة للمخزن", type="primary", key="btn_add_mat_unique"
        ):
            if mat_name:
                db["inventory"][mat_name] = (
                    db["inventory"].get(mat_name, 0.0) + mat_qty
                )
                save_data(db)
                st.success(f"تم تحديث مخزون '{mat_name}' بنجاح!")
                st.rerun()
    with c2:
        if db["inventory"]:
            st.dataframe(
                pd.DataFrame(
                    list(db["inventory"].items()),
                    columns=["المادة", "الكمية المتوفرة"],
                ),
                use_container_width=True,
            )
        else:
            st.info("لا توجد مواد خام مسجلة.")

# 2. وصفات البرادات
with tabs[1]:
    st.markdown("### 🛠️ تحديد وصفات البرادات (BOM)")
    if not db["inventory"]:
        st.warning("أضف مواد خام أولاً.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            model_name = st.text_input("اسم نموذج البراد:", key="mod_name")
            if "temp_bom" not in st.session_state:
                st.session_state.temp_bom = {}

            sel_mat = st.selectbox(
                "اختر مادة خام:",
                list(db["inventory"].keys()),
                key="sel_mat_bom_unique",
            )
            need_q = st.number_input(
                "الكمية المطلوبة للوحدة:",
                min_value=0.1,
                value=1.0,
                key="need_q_unique",
            )
            if st.button(
                "➕ إضافة مادة للوصفة", key="btn_add_bom_item_unique"
            ):
                st.session_state.temp_bom[sel_mat] = need_q
                st.success("تمت الإضافة للوصفة المؤقتة.")

            if st.session_state.temp_bom:
                st.write(st.session_state.temp_bom)
                if st.button(
                    "💾 حفظ وصفة البراد",
                    type="primary",
                    key="btn_save_bom_final",
                ):
                    if model_name:
                        db["bom"][model_name] = st.session_state.temp_bom
                        db["finished_goods"].setdefault(model_name, 0)
                        save_data(db)
                        st.session_state.temp_bom = {}
                        st.success("تم حفظ الوصفة!")
                        st.rerun()
        with c2:
            if db["bom"]:
                st.json(db["bom"])

# 3. الإنتاج
with tabs[2]:
    st.markdown("### 🏭 تسجيل الإنتاج")
    if db["bom"]:
        p_mod = st.selectbox(
            "نموذج البراد:", list(db["bom"].keys()), key="p_mod_unique"
        )
        p_qty = st.number_input(
            "عدد الوحدات:", min_value=1, value=1, key="p_qty_unique"
        )

        bom_rec = db["bom"][p_mod]
        can_p = True
        for m, req in bom_rec.items():
            if db["inventory"].get(m, 0) < req * p_qty:
                can_p = False

        if not can_p:
            st.error("⚠️ مواد المخزن غير كافية للإنتاج!")
        else:
            if st.button(
                "🚀 تأكيد الإنتاج", type="primary", key="btn_confirm_prod_unique"
            ):
                for m, req in bom_rec.items():
                    db["inventory"][m] -= req * p_qty
                db["finished_goods"][p_mod] = (
                    db["finished_goods"].get(p_mod, 0) + p_qty
                )
                save_data(db)
                st.success("تم الإنتاج وخصم المواد بنجاح!")
                st.rerun()
    else:
        st.info("لا توجد وصفات برادات مسجلة.")

# 4. الوكلاء والديون
with tabs[3]:
    st.markdown("### 🤝 الوكلاء والديون")
    a_name = st.text_input("اسم الوكيل / المحل:", key="ag_n_unique")
    a_debt = st.number_input(
        "الدين السابق (إن وجد):",
        min_value=0.0,
        value=0.0,
        key="ag_d_unique",
    )
    if st.button("➕ حفظ الوكيل", type="primary", key="btn_save_agent_unique"):
        if a_name:
            db["agents"][a_name] = {"debt": a_debt, "transactions": []}
            save_data(db)
            st.success("تم حفظ الوكيل!")
            st.rerun()

# 5. المبيعات والفواتير والوصلين
with tabs[4]:
    st.markdown("### 🛒 نقطة بيع البرادات وإصدار الوثائق")
    b_type = st.radio(
        "نوع المشتري:",
        ["عميل مباشر", "وكيل مسجل"],
        horizontal=True,
        key="b_type_unique",
    )

    buyer = ""
    if b_type == "عميل مباشر":
        buyer = st.text_input("اسم العميل:", key="dir_buyer_unique")
    else:
        if db["agents"]:
            buyer = st.selectbox(
                "اختر الوكيل:", list(db["agents"].keys()), key="sel_ag_sale_unique"
            )

    pay_method = st.selectbox(
        "طريقة البيع:", ["مباشر (نقداً)", "آجل", "أقساط"], key="pay_method_unique"
    )

    cart = []
    tot_inv = 0.0
    if db["finished_goods"]:
        for m, stock in db["finished_goods"].items():
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"**{m}** (المتوفر: {stock})")
            with c2:
                q = st.number_input(
                    "العدد:",
                    min_value=0,
                    max_value=stock,
                    value=0,
                    key=f"q_{m}_unique",
                )
            with c3:
                p = st.number_input(
                    "السعر:",
                    min_value=0.0,
                    value=0.0,
                    key=f"p_{m}_unique",
                )
            if q > 0:
                t = float(q) * float(p)
                tot_inv += t
                cart.append(
                    {"model": m, "qty": q, "price": p, "total": t}
                )

        st.markdown(f"#### الإجمالي الكلي: `{tot_inv:,.2f}` د.ع")
        
        paid_now = st.number_input(
            "المبلغ المدفوع الآن:",
            min_value=0.0,
            max_value=float(tot_inv),
            value=0.0,
            key="paid_now_unique",
        )
        remaining = float(tot_inv) - float(paid_now)

        if st.button(
            "📄 إتمام البيع وإصدار الوثائق",
            type="primary",
            key="btn_complete_sale_unique",
        ):
            if buyer and cart:
                r_no = db["receipt_counter"]
                db["receipt_counter"] += 1

                for item in cart:
                    db["finished_goods"][item["model"]] -= item["qty"]

                prev_debt = 0.0
                if b_type == "وكيل مسجل":
                    prev_debt = float(db["agents"][buyer]["debt"])
                    db["agents"][buyer]["debt"] = prev_debt + remaining

                save_data(db)
                st.success("تم إتمام البيع بنجاح!")

                rows_html = "".join(
                    [
                        f"<tr><td>{i['model']}</td><td>{i['qty']}</td><td>{i['price']:,.2f}</td><td><b>{i['total']:,.2f}</b></td></tr>"
                        for i in cart
                    ]
                )

                # 1. قائمة الحسابات
                invoice_html = f"""
                <!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>قائمة حسابات #{r_no}</title>
                <style>body{{font-family:Tahoma; padding:20px;}} .card{{background:#fff; padding:20px; border-radius:10px; border-top:5px solid #0284c7; max-width:600px; margin:auto;}} table{{width:100%; border-collapse:collapse; margin-top:15px;}} th,td{{padding:8px; border-bottom:1px solid #ddd; text-align:right;}}</style>
                </head><body><div class="card">
                <h2>معمل الرافدين للبرادات</h2>
                <h3>قائمة حسابات #{r_no}</h3>
                <p><b>الاسم:</b> {buyer} ({b_type} - {pay_method})</p>
                <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <table><tr><th>المنتج</th><th>العدد</th><th>السعر</th><th>الإجمالي</th></tr>{rows_html}</table>
                <p><b>الإجمالي:</b> {tot_inv:,.2f} د.ع</p>
                <p><b>المدفوع:</b> {paid_now:,.2f} د.ع</p>
                <p><b>المتبقي:</b> {remaining:,.2f} د.ع</p>
                </div></body></html>
                """

                # 2. وصل القبض
                receipt_html = f"""
                <!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>وصل قبض #{r_no}</title>
                <style>body{{font-family:Tahoma; padding:20px;}} .card{{background:#fff; padding:20px; border-radius:10px; border-top:5px solid #059669; max-width:600px; margin:auto;}}</style>
                </head><body><div class="card">
                <h2>معمل الرافدين للبرادات</h2>
                <h3>وصل قبض نقدي #{r_no}</h3>
                <p><b>الاسم:</b> {buyer}</p>
                <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p><b>الرصيد / الدين السابق:</b> {prev_debt:,.2f} د.ع</p>
                <p><b>المبلغ المسدد الآن:</b> {paid_now:,.2f} د.ع</p>
                <p><b>المتبقي في الذمة:</b> {prev_debt + remaining:,.2f} د.ع</p>
                </div></body></html>
                """

                st.download_button(
                    "📥 تحميل قائمة الحسابات (HTML / PDF)",
                    data=invoice_html.encode("utf-8"),
                    file_name=f"قائمة_حسابات_{r_no}.html",
                    mime="text/html",
                )
                st.download_button(
                    "📥 تحميل وصل القبض (HTML / PDF)",
                    data=receipt_html.encode("utf-8"),
                    file_name=f"وصل_قبض_{r_no}.html",
                    mime="text/html",
                )
            else:
                st.warning("يرجى إدخال اسم المشتري وتحديد منتج واحد على الأقل.")
    else:
        st.info("لا توجد برادات جاهزة بالمخزن.")
