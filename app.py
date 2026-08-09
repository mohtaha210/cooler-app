from datetime import datetime
import io
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات وتخطيط الصفحة ---
st.set_page_config(
    page_title="معاش - إدارة المعامل والديون",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- تنسيقات CSS المتجاوبة مع الهواتف الذكية والتصميم الداكن ---
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
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 1.3rem !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    .stSelectbox > div > div, .stTextInput input, .stNumberInput input {
        background-color: #111827 !important;
        color: #ffffff !important;
        border: 1px solid #2d3e5d !important;
        border-radius: 8px !important;
        text-align: right !important;
        direction: rtl !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        border: none !important;
        color: white !important;
    }
    .printable-receipt {
        background-color: #ffffff;
        color: #000000;
        padding: 20px;
        border-radius: 10px;
        direction: rtl;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    #MainMenu, footer, header {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "multi_factory_data.json"


def get_default_factory_data(factory_name, admin_user, admin_pass):
    return {
        "info": {"factory_name": factory_name},
        "users": {
            admin_user: {
                "password": admin_pass,
                "role": "admin",
                "name": f"مدير {factory_name}",
            }
        },
        "inventory": {
            "الحنفية": 100.0,
            "البانكة": 50.0,
            "الماطور": 50.0,
            "التوماتيك": 50.0,
            "الطواف": 50.0,
            "الراديتر": 50.0,
            "زواية القاعدة": 200.0,
            "المنيوم القاعدة 1.35m": 50.0,
            "الجكنة": 100.0,
            "واشر حديد": 100.0,
            "واشر بلاستك": 100.0,
            "زبانة": 100.0,
            "كبلري 1.7m": 50.0,
            "كويل": 50.0,
            "بوري ربع 1.5m": 50.0,
            "طبقة وربع بليت": 50.0,
        },
        "material_requests": [],
        "finished_goods": {"براد حنفية واحدة": 0, "براد حنفيتين": 0},
        "agents": {},
        "bom": {
            "براد حنفية واحدة": {
                "الحنفية": 1,
                "البانكة": 1,
                "الماطور": 1,
                "التوماتيك": 1,
                "الطواف": 1,
                "الراديتر": 1,
                "زواية القاعدة": 4,
                "المنيوم القاعدة 1.35m": 1,
                "الجكنة": 1,
                "واشر حديد": 1,
                "واشر بلاستك": 1,
                "زبانة": 1,
                "كبلري 1.7m": 1,
                "كويل": 1,
                "بوري ربع 1.5m": 1,
                "طبقة وربع بليت": 1.25,
            },
            "براد حنفيتين": {
                "الحنفية": 2,
                "البانكة": 1,
                "الماطور": 1,
                "التوماتيك": 1,
                "الطواف": 1,
                "الراديتر": 1,
                "زواية القاعدة": 4,
                "المنيوم القاعدة 1.35m": 1,
                "الجكنة": 2,
                "واشر حديد": 2,
                "واشر بلاستك": 2,
                "زبانة": 2,
                "كبلري 1.7m": 1,
                "كويل": 1,
                "بوري ربع 1.5m": 1,
                "طبقة وربع بليت": 1.25,
            },
        },
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": [],
    }


def load_all_factories():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for f_name, f_data in data.items():
                    if "finished_goods" not in f_data:
                        f_data["finished_goods"] = {
                            m: 0 for m in f_data.get("bom", {}).keys()
                        }
                    if "agents" not in f_data:
                        f_data["agents"] = {}
                    if "production_history" not in f_data:
                        f_data["production_history"] = []
                    if "material_requests" not in f_data:
                        f_data["material_requests"] = []
                return data
        except Exception:
            return {}
    return {}


def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


all_factories = load_all_factories()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.factory_key = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_fullname = ""

# --- واجهة تسجيل الدخول أو إنشاء معمل ---
if not st.session_state.authenticated:
    st.markdown(
        "<h2 style='text-align: center; color: #ffffff;'>🍏 نظام معاش لإدارة"
        " المعامل</h2>",
        unsafe_allow_html=True,
    )

    t1, t2 = st.tabs(["🔑 تسجيل الدخول", "🏭 إنشاء معمل جديد"])

    with t1:
        factory_list = list(all_factories.keys())
        if not factory_list:
            st.info("لا توجد معامل مسجلة حالياً. قم بإنشاء معمل جديد.")
        else:
            selected_factory = st.selectbox(
                "اختر المعمل:", factory_list, key="login_factory_select_new"
            )
            username_input = st.text_input(
                "اسم المستخدم:", key="login_username_new"
            )
            password_input = st.text_input(
                "كلمة المرور:", type="password", key="login_password_new"
            )

            if st.button(
                "تسجيل الدخول",
                type="primary",
                use_container_width=True,
                key="login_btn_new",
            ):
                factory_users = all_factories[selected_factory].get("users", {})
                if (
                    username_input in factory_users
                    and factory_users[username_input]["password"]
                    == password_input
                ):
                    st.session_state.authenticated = True
                    st.session_state.factory_key = selected_factory
                    st.session_state.username = username_input
                    st.session_state.role = factory_users[username_input][
                        "role"
                    ]
                    st.session_state.user_fullname = factory_users[
                        username_input
                    ]["name"]
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")

    with t2:
        new_f_name = st.text_input(
            "اسم المعمل الجديد:", key="new_factory_name_input"
        )
        admin_u = st.text_input(
            "اسم مستخدم المدير:", key="new_admin_user_input"
        )
        admin_p = st.text_input(
            "كلمة المرور:", type="password", key="new_admin_pass_input"
        )
        if st.button(
            "إنشاء وتفعيل المعمل",
            type="primary",
            use_container_width=True,
            key="create_factory_btn_new",
        ):
            if new_f_name and admin_u and admin_p:
                if new_f_name in all_factories:
                    st.error("اسم المعمل موجود مسبقاً!")
                else:
                    all_factories[new_f_name] = get_default_factory_data(
                        new_f_name, admin_u, admin_p
                    )
                    save_all_factories(all_factories)
                    st.success(
                        "تم إنشاء المعمل بنجاح! انتقل لتبويب تسجيل الدخول."
                    )
            else:
                st.warning("يرجى ملء جميع الحقول المطلوبة.")

    st.stop()

# --- لوحة التحكم الرئيسية بعد تسجيل الدخول ---
current_factory_name = st.session_state.factory_key
factory_data = all_factories[current_factory_name]

top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown(
        f"### 🍏 {current_factory_name}\n**المستخدم:**"
        f" `{st.session_state.user_fullname}`"
    )
with top_col2:
    if st.button("🚪 تسجيل خروج", key="logout_btn_main"):
        st.session_state.authenticated = False
        st.rerun()

st.divider()

# --- قائمة التنقل المتجاوبة ---
if st.session_state.role == "admin":
    available_tabs = [
        "📊 الرئيسية والمالية",
        "🤝 الديون والوكلاء",
        "🛒 بيع / قائمة حساب",
        "🏭 تسجيل إنتاج برادات",
        "📦 إدارة المخزون الخام",
        "📥 طلبات ونقص المواد",
        "👥 الموظفين والحسابات",
        "📄 تصدير تقارير Excel",
        "➕ إضافة مادة خام",
        "🛠️ أنواع البرادات (BOM)",
    ]
else:
    available_tabs = [
        "🛒 بيع / قائمة حساب",
        "🤝 الديون والوكلاء",
        "🏭 تسجيل إنتاج برادات",
        "📦 إدارة المخزون الخام",
        "📥 طلب ونقص المواد",
    ]

selected_tab = st.selectbox(
    "📂 الانتقال السريع للقسم:", available_tabs, key="main_nav_selector"
)
st.write("")

# -------------------------------------------------------------
# 1️⃣ الرئيسية والمالية
# -------------------------------------------------------------
if selected_tab == "📊 الرئيسية والمالية":
    st.markdown("### 💳 الإدارة المالية والإحصائيات")
    sales_history = factory_data.get("sales_history", [])
    sales_df = pd.DataFrame(sales_history)
    total_sales = sales_df["total"].sum() if not sales_df.empty else 0
    total_debts = sum(
        ag.get("debt", 0.0)
        for ag in factory_data["agents"].values()
        if isinstance(ag, dict)
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("إجمالي المبيعات", f"{total_sales:,} د.ع")
    with col2:
        st.metric("ديون لنا (على الوكلاء)", f"{total_debts:,} د.ع")

    st.markdown("#### 📜 سجل المعاملات والمبيعات العامة")
    if not sales_df.empty:
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")

# -------------------------------------------------------------
# 2️⃣ الديون والوكلاء (مع طباعة وصل القبض وكشف الحساب)
# -------------------------------------------------------------
elif selected_tab == "🤝 الديون والوكلاء":
    st.markdown("### 💳 إدارة الديون والوكلاء")
    sub_t1, sub_t2, sub_t3 = st.tabs(
        ["➕ إضافة وكيل", "💵 تسديد دين ووصل قبض", "📜 كشف حساب وطباعة"]
    )

    with sub_t1:
        ag_name = st.text_input("اسم الوكيل / المحل:", key="input_ag_name")
        ag_phone = st.text_input("رقم الهاتف:", key="input_ag_phone")
        ag_initial_debt = st.number_input(
            "الذمة / الدين السابق:",
            min_value=0.0,
            step=10000.0,
            key="input_ag_debt",
        )
        if st.button("➕ تسجيل الوكيل", type="primary", key="btn_save_agent"):
            if ag_name and ag_name not in factory_data["agents"]:
                factory_data["agents"][ag_name] = {
                    "phone": ag_phone,
                    "debt": ag_initial_debt,
                    "transactions": [],
                }
                save_all_factories(all_factories)
                st.toast("✅ تم إضافة الوكيل بنجاح!", icon="🎉")
                st.rerun()
            else:
                st.warning("اسم الوكيل موجود مسبقاً أو فارغ.")

    with sub_t2:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            selected_ag = st.selectbox(
                "اختر الوكيل للتسديد:", agents_list, key="select_pay_agent"
            )
            current_debt = factory_data["agents"][selected_ag].get("debt", 0.0)
            st.warning(f"الدين الحالي على الوكيل: **{current_debt:,} د.ع**")

            pay_amount = st.number_input(
                "المبلغ المدفوع:",
                min_value=1.0,
                value=50000.0,
                step=10000.0,
                key="input_pay_amount",
            )
            if st.button(
                "💵 تأكيد وتثبيت التسديد",
                type="primary",
                key="btn_confirm_payment",
            ):
                new_debt = current_debt - pay_amount
                factory_data["agents"][selected_ag]["debt"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)

                payment_record = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "تسديد دفعة",
                    "amount": pay_amount,
                    "balance": new_debt,
                    "note": f"وصل قبض #{receipt_no}",
                }
                factory_data["agents"][selected_ag].setdefault(
                    "transactions", []
                ).append(payment_record)
                factory_data["receipt_counter"] = receipt_no + 1
                save_all_factories(all_factories)

                st.toast(
                    "💵 تم تسجيل التسديد بنجاح وإصدار وصل القبض!", icon="✅"
                )
                st.success("تم تسجيل عملية التسديد بنجاح!")

                # معاينة وصل القبض الجاهز للطباعة
                st.markdown("---")
                st.markdown("#### 📄 معاينة وصل القبض للطباعة:")
                receipt_html = f"""
                <div class="printable-receipt">
                    <h3 style="text-align: center; margin-bottom: 5px;">{current_factory_name}</h3>
                    <h4 style="text-align: center; color: #555; margin-top: 0;">وصل قبض نقدي</h4>
                    <hr>
                    <p><b>رقم الوصل:</b> #{receipt_no}</p>
                    <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                    <p><b>استلمنا من السيد/المحل:</b> {selected_ag}</p>
                    <p><b>المبلغ الواصل:</b> <span style="font-size: 1.2em; color: #0d6efd;"><b>{pay_amount:,} د.ع</b></span></p>
                    <p><b>الرصيد المتبقي بالذمة:</b> {new_debt:,} د.ع</p>
                    <br>
                    <div style="display: flex; justify-content: space-between; margin-top: 30px;">
                        <p>توقيع المستلم: ........................</p>
                        <p>ختم المعمل: ........................</p>
                    </div>
                </div>
                """
                st.markdown(receipt_html, unsafe_allow_html=True)
                st.info(
                    "💡 يمكنك طباعة هذا الوصل مباشرة بالضغط على (Ctrl + P) في"
                    " المتصفح."
                )
        else:
            st.info("لا يوجد وكلاء مسجلون بعد.")

    with sub_t3:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            sel_ag_view = st.selectbox(
                "عرض تفاصيل حساب الوكيل:",
                agents_list,
                key="select_view_agent_acc",
            )
            ag_info = factory_data["agents"][sel_ag_view]
            st.info(f"المتبقي بالذمة: **{ag_info.get('debt', 0):,} د.ع**")
            trans_list = ag_info.get("transactions", [])
            if trans_list:
                st.dataframe(pd.DataFrame(trans_list), use_container_width=True)

                # زر معاينة كشف الحساب الكامل للطباعة
                if st.button("🖨️ تجهيز كشف الحساب للطباعة"):
                    statement_html = f"""
                    <div class="printable-receipt">
                        <h3 style="text-align: center;">{current_factory_name}</h3>
                        <h4 style="text-align: center; color: #555;">كشف حساب تفصيلي للوكيل: {sel_ag_view}</h4>
                        <hr>
                        <p><b>رقم الهاتف:</b> {ag_info.get('phone', 'غير متوفر')}</p>
                        <p><b>إجمالي الدين الحالي:</b> <span style="color: red;">{ag_info.get('debt', 0):,} د.ع</span></p>
                        <table border="1" style="width: 100%; border-collapse: collapse; text-align: center; margin-top: 10px;">
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding: 8px;">التاريخ</th>
                                <th style="padding: 8px;">الحركة</th>
                                <th style="padding: 8px;">المبلغ (د.ع)</th>
                                <th style="padding: 8px;">الرصيد المتبقي</th>
                                <th style="padding: 8px;">ملاحظات</th>
                            </tr>
                    """
                    for t in trans_list:
                        statement_html += f"""
                            <tr>
                                <td style="padding: 6px;">{t.get('date', '')}</td>
                                <td style="padding: 6px;">{t.get('type', '')}</td>
                                <td style="padding: 6px;">{t.get('amount', 0):,}</td>
                                <td style="padding: 6px;">{t.get('balance', 0):,}</td>
                                <td style="padding: 6px;">{t.get('note', '')}</td>
                            </tr>
                        """
                    statement_html += """
                        </table>
                    </div>
                    """
                    st.markdown(statement_html, unsafe_allow_html=True)
            else:
                st.info("لا توجد حركات مالية مسجلة لهذا الوكيل.")
        else:
            st.info("لا يوجد وكلاء مسجلون.")

# -------------------------------------------------------------
# 3️⃣ بيع / قائمة حساب
# -------------------------------------------------------------
elif selected_tab == "🛒 بيع / قائمة حساب":
    st.markdown("### 🛒 نقطة بيع البرادات")
    c_type = st.radio(
        "نوع المشتري:",
        ["مباشر (نقداً)", "وكيل مسجل"],
        horizontal=True,
        key="radio_buyer_type_main",
    )

    if c_type == "مباشر (نقداً)":
        customer_name = st.text_input(
            "اسم الزبون / المشتري:", key="input_direct_buyer_name"
        )
    else:
        agents_list = list(factory_data["agents"].keys())
        customer_name = (
            st.selectbox(
                "اختر الوكيل:", agents_list, key="select_buyer_agent_name"
            )
            if agents_list
            else ""
        )

    model_list = list(factory_data["bom"].keys())
    selected_items = []
    grand_total = 0

    for model in model_list:
        stock_available = factory_data["finished_goods"].get(model, 0)
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.write(f"**{model}** (المتوفر: {stock_available})")
        with c2:
            qty = st.number_input(
                "العدد:",
                min_value=0,
                max_value=max(0, stock_available),
                key=f"sale_qty_{model}",
            )
        with c3:
            price = st.number_input(
                "السعر للقطعة:", min_value=0, key=f"sale_price_{model}"
            )

        if qty > 0:
            total_p = qty * price
            grand_total += total_p
            selected_items.append(
                {"model": model, "count": qty, "price": price, "total": total_p}
            )

    st.markdown(f"#### الإجمالي الكلي للقائمة: `{grand_total:,}` د.ع")

    if st.button(
        "🛒 إتمام وإصدار قائمة البيع",
        type="primary",
        key="btn_complete_sale",
    ):
        if customer_name and selected_items:
            receipt_no = factory_data.get("receipt_counter", 1001)
            for item in selected_items:
                factory_data["finished_goods"][item["model"]] -= item["count"]

            # إذا كان البيع لوكيل، يتم تسجيله كدين أو مبيعات حسب النظام
            factory_data["sales_history"].append({
                "receipt_no": receipt_no,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "customer": customer_name,
                "items_count": len(selected_items),
                "total": grand_total,
            })
            factory_data["receipt_counter"] = receipt_no + 1
            save_all_factories(all_factories)

            st.toast("🛒 تمت عملية البيع بنجاح!", icon="🎉")
            st.success("تم إتمام عملية البيع وتحديث المخزون بنجاح!")

            # معاينة قائمة الحساب للطباعة
            invoice_html = f"""
            <div class="printable-receipt">
                <h3 style="text-align: center;">{current_factory_name}</h3>
                <h4 style="text-align: center; color: #555;">قائمة مبيعات / حساب</h4>
                <hr>
                <p><b>رقم القائمة:</b> #{receipt_no}</p>
                <p><b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p><b>اسم المشتري / الوكيل:</b> {customer_name}</p>
                <table border="1" style="width: 100%; border-collapse: collapse; text-align: center; margin-top: 10px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px;">المنتج</th>
                        <th style="padding: 8px;">العدد</th>
                        <th style="padding: 8px;">السعر المفرد</th>
                        <th style="padding: 8px;">الإجمالي</th>
                    </tr>
            """
            for itm in selected_items:
                invoice_html += f"""
                    <tr>
                        <td style="padding: 6px;">{itm['model']}</td>
                        <td style="padding: 6px;">{itm['count']}</td>
                        <td style="padding: 6px;">{itm['price']:,}</td>
                        <td style="padding: 6px;">{itm['total']:,}</td>
                    </tr>
                """
            invoice_html += f"""
                </table>
                <h3 style="text-align: left; margin-top: 15px;">المبلغ الإجمالي الكلي: {grand_total:,} د.ع</h3>
            </div>
            """
            st.markdown(invoice_html, unsafe_allow_html=True)
        else:
            st.warning("يرجى إدخال اسم المشتري وتحديد منتج واحد على الأقل.")

# -------------------------------------------------------------
# 4️⃣ تسجيل إنتاج برادات
# -------------------------------------------------------------
elif selected_tab == "📦 إدارة المخزون الخام":
    st.markdown("### 📦 أرصدة المواد الخام الحالية بالمخزن")
    inv_df = pd.DataFrame(
        list(factory_data["inventory"].items()),
        columns=["المادة الخام", "الكمية المتاحة"],
    )
    st.dataframe(inv_df, use_container_width=True)

# -------------------------------------------------------------
# 5️⃣ إدارة المخزون الخام
# -------------------------------------------------------------
elif selected_tab == "🏭 تسجيل إنتاج برادات":
    st.markdown("### 🏭 تسجيل وجبة إنتاج جديدة")
    model_to_produce = st.selectbox(
        "اختر نموذج البراد المراد تجميعه:",
        list(factory_data["bom"].keys()),
        key="select_prod_model_name",
    )
    produce_qty = st.number_input(
        "عدد الوحدات المصنعة:",
        min_value=1,
        value=1,
        key="input_production_quantity",
    )

    bom = factory_data["bom"].get(model_to_produce, {})
    can_produce = True
    missing_items = []

    for mat, needed_per_unit in bom.items():
        total_needed = needed_per_unit * produce_qty
        available = factory_data["inventory"].get(mat, 0.0)
        if available < total_needed:
            can_produce = False
            missing_items.append(
                f"{mat} (المطلوب: {total_needed} / المتوفر: {available})"
            )

    if not can_produce:
        st.error(
            "⚠️ لا يمكن إتمام الإنتاج لنقص المواد الخام التالية في المخزن:"
        )
        for mi in missing_items:
            st.write(f"- {mi}")
    else:
        if st.button(
            "🚀 تأكيد الإنتاج وخصم المواد الخام",
            type="primary",
            key="btn_confirm_production",
        ):
            for mat, needed_per_unit in bom.items():
                factory_data["inventory"][mat] -= needed_per_unit * produce_qty
            factory_data["finished_goods"][model_to_produce] = (
                factory_data["finished_goods"].get(model_to_produce, 0)
                + produce_qty
            )

            factory_data["production_history"].append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "model": model_to_produce,
                "qty": produce_qty,
            })
            save_all_factories(all_factories)
            st.toast(
                "🚀 تم إتمام عملية الإنتاج وتحديث المخزون بنجاح!", icon="✅"
            )
            st.success("✅ تم تسجيل الإنتاج وإضافته للمخزون بنجاح!")
            st.rerun()

# -------------------------------------------------------------
# 6️⃣ طلبات ونقص المواد (زيادة المواد عند نفادها)
# -------------------------------------------------------------
elif (
    selected_tab == "📥 طلبات ونقص المواد"
    or selected_tab == "📥 طلب ونقص المواد"
):
    st.markdown("### 📥 قسم نقص المواد الخام وطلبات التوريد")
    st.info(
        "هنا يمكنك رفع طلب بتوفير مواد خام ناقصة للمخزن أو إضافتها بشكل مباشر إذا"
        " وصلت شحنة جديدة."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📝 إرسال طلب نقص مادة جديدة")
        req_material = st.selectbox(
            "اختر المادة الناقصة:",
            list(factory_data["inventory"].keys()),
            key="req_mat_select",
        )
        req_qty = st.number_input(
            "الكمية المطلوبة:", min_value=1.0, value=50.0, key="req_mat_qty"
        )
        req_note = st.text_input("ملاحظات إضافية:", key="req_mat_note")

        if st.button("📤 إرسال طلب التوريد", key="send_req_btn"):
            factory_data.setdefault("material_requests", []).append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "material": req_material,
                "qty": req_qty,
                "note": req_note,
                "status": "قيد الانتظار",
            })
            save_all_factories(all_factories)
            st.toast("📤 تم إرسال طلب المادة بنجاح!", icon="🔔")
            st.success("تم إرسال الطلب بنجاح للإدارة.")

    with col2:
        st.markdown("#### 📋 سجل الطلبات السابقة")
        requests_list = factory_data.get("material_requests", [])
        if requests_list:
            st.dataframe(pd.DataFrame(requests_list), use_container_width=True)
        else:
            st.info("لا توجد طلبات توريد مسجلة.")

# -------------------------------------------------------------
# 7️⃣ الموظفين والحسابات
# -------------------------------------------------------------
elif selected_tab == "👥 الموظفين والحسابات":
    st.markdown("### 👥 إدارة المستخدمين وصلاحيات المعمل")
    users_dict = factory_data.get("users", {})
    if users_dict:
        users_df = pd.DataFrame(users_dict).T[["name", "role"]]
        st.dataframe(users_df, use_container_width=True)
    else:
        st.info("لا توجد حسابات مسجلة.")

# -------------------------------------------------------------
# 8️⃣ تصدير تقارير Excel
# -------------------------------------------------------------
elif selected_tab == "📄 تصدير تقارير Excel":
    st.markdown("### 📄 تصدير البيانات والتقارير")
    sales_history = factory_data.get("sales_history", [])
    sales_df = pd.DataFrame(sales_history)

    if not sales_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sales_df.to_excel(writer, sheet_name="المبيعات", index=False)

        st.download_button(
            label="📊 تنزيل ملف تقرير المبيعات (Excel)",
            data=buffer.getvalue(),
            file_name=f"تقرير_مبيعات_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel",
            type="primary",
            key="download_excel_report_btn",
        )
    else:
        st.info("لا توجد مبيعات كافية لتصديرها في تقرير Excel.")

# -------------------------------------------------------------
# 9️⃣ إضافة مادة خام
# -------------------------------------------------------------
elif selected_tab == "➕ إضافة مادة خام":
    st.markdown("### ➕ إضافة مادة خام جديدة أو زيادة رصيد الشحنات")
    new_mat_name = st.text_input(
        "اسم المادة الخام:", key="input_new_material_name"
    )
    add_qty = st.number_input(
        "الكمية الواردة للمخزن:", min_value=0.0, key="input_add_material_qty"
    )

    if st.button(
        "حفظ وتحديث المخزن", type="primary", key="btn_save_new_material"
    ):
        if new_mat_name:
            curr = factory_data["inventory"].get(new_mat_name, 0.0)
            factory_data["inventory"][new_mat_name] = curr + add_qty
            save_all_factories(all_factories)
            st.toast("📦 تم تحديث المخزون وإضافة المواد بنجاح!", icon="✅")
            st.success(f"تم تحديث مخزون المادة '{new_mat_name}' بنجاح!")
            st.rerun()
        else:
            st.warning("يرجى كتابة اسم المادة الخام.")

# -------------------------------------------------------------
# 🔟 أنواع البرادات (BOM)
# -------------------------------------------------------------
elif selected_tab == "🛠️ أنواع البرادات (BOM)":
    st.markdown(
        "### 🛠️ مكونات التصنيع المعيارية للبرادات (Bill of Materials)"
    )
    st.json(factory_data.get("bom", {}))
