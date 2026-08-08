from datetime import datetime
import io
import json
import os
import pandas as pd
import streamlit as st

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="منصة ادارة بيانات معمل الرافدين",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS مخصص للتجاوب التام مع الهواتف الذكية + التصميم الداكن الأصلي ---
st.markdown(
    """
<style>
    .stApp {
        background-color: #0b1120;
        color: #f1f5f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    div[data-testid="stMetric"], .stCard {
        background-color: #162032 !important;
        border: 1px solid #23324d !important;
        border-radius: 14px !important;
        padding: 15px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    .stSelectbox > div > div, .stTextInput input, .stNumberInput input {
        background-color: #111827 !important;
        color: #ffffff !important;
        border: 1px solid #2d3e5d !important;
        border-radius: 10px !important;
        text-align: right !important;
        direction: rtl !important;
    }
    .stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #111827;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #23324d;
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
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
            "طبقة وربع بليت": 1.25,
        },
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

# --- الشاشة الأولى: تسجيل الدخول ---
if not st.session_state.authenticated:
    st.markdown(
        "<h2 style='text-align: center; color: #ffffff;'>🏭 منصة ادارة بيانات"
        " معمل الرافدين</h2>",
        unsafe_allow_html=True,
    )

    t1, t2 = st.tabs(["🔑 تسجيل الدخول", "🏭 إنشاء معمل جديد"])

    with t1:
        factory_list = list(all_factories.keys())
        if not factory_list:
            st.info("لا توجد معامل مسجلة. قم بإنشاء معمل جديد أولاً.")
        else:
            selected_factory = st.selectbox(
                "اختر المعمل:", factory_list, key="login_factory_select"
            )
            username_input = st.text_input(
                "اسم المستخدم:", key="login_username"
            )
            password_input = st.text_input(
                "كلمة المرور:", type="password", key="login_password"
            )

            if st.button(
                "تسجيل الدخول",
                type="primary",
                use_container_width=True,
                key="login_btn",
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
        new_f_name = st.text_input("اسم المعمل الجديد:", key="new_factory_name")
        admin_u = st.text_input("اسم مستخدم المدير:", key="new_admin_user")
        admin_p = st.text_input(
            "كلمة المرور:", type="password", key="new_admin_pass"
        )
        if st.button(
            "إنشاء وتفعيل المعمل",
            type="primary",
            use_container_width=True,
            key="create_factory_btn",
        ):
            if new_f_name and admin_u and admin_p:
                all_factories[new_f_name] = get_default_factory_data(
                    new_f_name, admin_u, admin_p
                )
                save_all_factories(all_factories)
                st.success("تم الإنشاء بنجاح! يمكنك الآن تسجيل الدخول.")

    st.stop()

# --- بيانات المعمل الحالي والتطبيق الرئيسي ---
current_factory_name = st.session_state.factory_key
factory_data = all_factories[current_factory_name]

h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(
        f"### 🍏 {current_factory_name}\n**المستخدم:**"
        f" `{st.session_state.user_fullname}`"
    )
with h2:
    if st.button("🚪 خروج", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

st.divider()

# --- القائمة المنسدلة للتنقل ---
if st.session_state.role == "admin":
    all_tabs = [
        "📊 الرئيسية والمالية",
        "🤝 الديون والوكلاء",
        "🛒 بيع / قائمة حساب",
        "🏭 تسجيل إنتاج برادات",
        "📦 إدارة المخزون الخام",
        "👥 الموظفين والحسابات",
        "📄 تصدير تقارير Excel",
        "➕ إضافة مادة خام",
        "🛠️ أنواع البرادات (BOM)",
    ]
else:
    all_tabs = [
        "🛒 بيع / قائمة حساب",
        "🤝 الديون والوكلاء",
        "🏭 تسجيل إنتاج برادات",
        "📦 إدارة المخزون الخام",
    ]

selected_tab = st.selectbox(
    "📂 الانتقال للقسم:", all_tabs, key="main_nav_select"
)
st.write("")

# -------------------------------------------------------------
# 1️⃣ الرئيسية والمالية
# -------------------------------------------------------------
if selected_tab == "📊 الرئيسية والمالية":
    st.markdown("### 💳 قسم الإدارة المالية والتقارير")
    sales_df = pd.DataFrame(factory_data.get("sales_history", []))
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

    st.markdown("#### 📜 سجل المعاملات والمبيعات")
    if not sales_df.empty:
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")

# -------------------------------------------------------------
# 2️⃣ الديون والوكلاء
# -------------------------------------------------------------
elif selected_tab == "🤝 الديون والوكلاء":
    st.markdown("### 💳 قسم إدارة الديون والتسديد الجزئي")
    sub1, sub2, sub3 = st.tabs(
        ["➕ إضافة وكيل", "💵 تسديد دين", "📜 كشف حساب"]
    )

    with sub1:
        ag_name = st.text_input("اسم الوكيل / المحل:", key="ag_name_input")
        ag_phone = st.text_input("رقم الهاتف:", key="ag_phone_input")
        ag_initial_debt = st.number_input(
            "الذمة / الدين السابق:",
            min_value=0.0,
            step=10000.0,
            key="ag_initial_debt",
        )
        if st.button("➕ تسجيل الوكيل", type="primary", key="add_ag_btn"):
            if ag_name and ag_name not in factory_data["agents"]:
                factory_data["agents"][ag_name] = {
                    "phone": ag_phone,
                    "debt": ag_initial_debt,
                    "transactions": [],
                }
                save_all_factories(all_factories)
                st.success("تم إضافة الوكيل بنجاح!")
                st.rerun()

    with sub2:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            selected_ag = st.selectbox(
                "اختر الوكيل:", agents_list, key="pay_ag_select"
            )
            current_debt = factory_data["agents"][selected_ag].get("debt", 0.0)
            st.warning(f"الدين الحالي: **{current_debt:,} د.ع**")

            pay_amount = st.number_input(
                "المبلغ المدفوع:",
                min_value=1.0,
                value=50000.0,
                step=10000.0,
                key="pay_amount_input",
            )
            if st.button(
                "💵 تأكيد التسديد", type="primary", key="confirm_pay_btn"
            ):
                new_debt = current_debt - pay_amount
                factory_data["agents"][selected_ag]["debt"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)

                factory_data["agents"][selected_ag].setdefault(
                    "transactions", []
                ).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "تسديد دفعة",
                    "amount": -pay_amount,
                    "balance": new_debt,
                    "note": f"وصل #{receipt_no}",
                })
                factory_data["receipt_counter"] = receipt_no + 1
                save_all_factories(all_factories)
                st.success("تم تسديد المبلغ وخصمه من الدين!")
                st.rerun()

    with sub3:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            sel_ag_view = st.selectbox(
                "عرض كشف حساب الوكيل:", agents_list, key="view_ag_select"
            )
            ag_info = factory_data["agents"][sel_ag_view]
            st.info(f"المتبقي بالذمة: **{ag_info.get('debt', 0):,} د.ع**")
            st.dataframe(
                pd.DataFrame(ag_info.get("transactions", [])),
                use_container_width=True,
            )

# -------------------------------------------------------------
# 3️⃣ بيع / قائمة حساب
# -------------------------------------------------------------
elif selected_tab == "🛒 بيع / قائمة حساب":
    st.markdown("### 🛒 بيع براد / قائمة حساب")
    c_type = st.radio(
        "نوع المشتري:",
        ["مباشر (نقداً)", "وكيل مسجل"],
        horizontal=True,
        key="buyer_type_radio",
    )

    if c_type == "مباشر (نقداً)":
        customer_name = st.text_input(
            "اسم المشتري:", key="direct_customer_name"
        )
    else:
        agents_list = list(factory_data["agents"].keys())
        customer_name = (
            st.selectbox("اختر الوكيل:", agents_list, key="sale_agent_select")
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
                key=f"qty_{model}",
            )
        with c3:
            price = st.number_input("السعر:", min_value=0, key=f"price_{model}")

        if qty > 0:
            total_p = qty * price
            grand_total += total_p
            selected_items.append(
                {"model": model, "count": qty, "price": price, "total": total_p}
            )

    st.markdown(f"#### الإجمالي النهائي: `{grand_total:,}` د.ع")

    if st.button("🛒 تأكيد عملية البيع", type="primary", key="confirm_sale_btn"):
        if customer_name and selected_items:
            receipt_no = factory_data.get("receipt_counter", 1001)
            for item in selected_items:
                factory_data["finished_goods"][item["model"]] -= item["count"]

            factory_data["sales_history"].append({
                "receipt_no": receipt_no,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "customer": customer_name,
                "items_count": len(selected_items),
                "total": grand_total,
            })
            factory_data["receipt_counter"] = receipt_no + 1
            save_all_factories(all_factories)
            st.success("تم تسجيل المبيعات وخصم البرادات من المخزون!")
            st.rerun()

# -------------------------------------------------------------
# 4️⃣ تسجيل إنتاج برادات
# -------------------------------------------------------------
elif selected_tab == "🏭 تسجيل إنتاج برادات":
    st.markdown("### 🏭 تسجيل وجبة إنتاج جديدة")
    model_to_produce = st.selectbox(
        "اختر نوع البراد المراد تصنيعه:",
        list(factory_data["bom"].keys()),
        key="prod_model_select",
    )
    produce_qty = st.number_input(
        "الكمية المصنعة:", min_value=1, value=1, key="prod_qty_input"
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
            "⚠️ لا يمكن تصنيع الوجبة لعدم توفر المواد الخام التالية بالمخزن:"
        )
        for mi in missing_items:
            st.write(f"- {mi}")
    else:
        if st.button(
            "🚀 تأكيد التصنيع وخصم المواد",
            type="primary",
            key="confirm_prod_btn",
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
            st.success("✅ تم إضافة الإنتاج للمخزون وخصم قطع الغيار بنجاح!")
            st.rerun()

# -------------------------------------------------------------
# 5️⃣ إدارة المخزون الخام
# -------------------------------------------------------------
elif selected_tab == "📦 إدارة المخزون الخام":
    st.markdown("### 📦 كميات المواد الخام الحالية بالمخزن")
    inv_df = pd.DataFrame(
        list(factory_data["inventory"].items()),
        columns=["المادة الخام", "الكمية المتاحة"],
    )
    st.dataframe(inv_df, use_container_width=True)

# -------------------------------------------------------------
# 6️⃣ الموظفين والحسابات
# -------------------------------------------------------------
elif selected_tab == "👥 الموظفين والحسابات":
    st.markdown("### 👥 إدارة الموظفين والمستخدمين")
    users_df = pd.DataFrame(factory_data["users"]).T[["name", "role"]]
    st.dataframe(users_df, use_container_width=True)

# -------------------------------------------------------------
# 7️⃣ تصدير تقارير Excel
# -------------------------------------------------------------
elif selected_tab == "📄 تصدير تقارير Excel":
    st.markdown("### 📄 تصدير البيانات الشاملة")
    sales_df = pd.DataFrame(factory_data.get("sales_history", []))

    if not sales_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sales_df.to_excel(writer, sheet_name="المبيعات", index=False)

        st.download_button(
            label="📊 تنزيل تقرير المبيعات (Excel)",
            data=buffer.getvalue(),
            file_name=f"sales_report_{current_factory_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("لا توجد بيانات مبيعات كافية للتصدير.")

# -------------------------------------------------------------
# 8️⃣ إضافة مادة خام
# -------------------------------------------------------------
elif selected_tab == "➕ إضافة مادة خام":
    st.markdown("### ➕ إضافة مواد جديدة أو زيادة كميات المخزن")

    action_type = st.radio(
        "نوع الإضافة:",
        ["زيادة كمية مادة موجودة", "إضافة مادة خام جديدة"],
        horizontal=True,
        key="mat_action_radio",
    )

    inventory_dict = factory_data.get("inventory", {})

    if action_type == "زيادة كمية مادة موجودة":
        if inventory_dict:
            mat_choice = st.selectbox(
                "اختر المادة الخام:",
                list(inventory_dict.keys()),
                key="existing_mat_select",
            )
            current_qty = inventory_dict.get(mat_choice, 0.0)
            st.info(
                f"الكمية الحالية في المخزن لـ ({mat_choice}):"
                f" **{current_qty}**"
            )

            add_qty = st.number_input(
                "الكمية المراد إضافتها:",
                min_value=0.1,
                step=1.0,
                key="add_existing_qty",
            )

            if st.button(
                "🚀 تحديث وزيادة المخزن", type="primary", key="update_mat_btn"
            ):
                factory_data["inventory"][mat_choice] = current_qty + add_qty
                save_all_factories(all_factories)
                st.success(
                    f"✅ تم إضافة {add_qty} بنجاح إلى ({mat_choice}). المخزن"
                    f" الجديد أصبح: {factory_data['inventory'][mat_choice]}"
                )
                st.rerun()
        else:
            st.warning("لا توجد مواد خام مسجلة حالياً.")

    else:
        new_mat_name = st.text_input(
            "اسم المادة الخام الجديدة:", key="new_mat_name_input"
        )
        initial_qty = st.number_input(
            "الكمية الأولية للمادة:",
            min_value=0.0,
            step=1.0,
            key="new_mat_qty_input",
        )

        if st.button(
            "🚀 حفظ وإضافة المادة الجديدة",
            type="primary",
            key="save_new_mat_btn",
        ):
            if new_mat_name.strip():
                if new_mat_name in inventory_dict:
                    st.error(
                        "⚠️ هذه المادة موجودة مسبقاً! يمكنك اختيار 'زيادة كمية"
                        " مادة موجودة' لتحديثها."
                    )
                else:
                    factory_data["inventory"][new_mat_name] = initial_qty
                    save_all_factories(all_factories)
                    st.success(
                        "✅ تم إضافة المادة الجديدة"
                        f" ({new_mat_name}) برصيد: {initial_qty}"
                    )
                    st.rerun()
            else:
                st.error("الرجاء إدخال اسم المادة بشكل صحيح.")

# -------------------------------------------------------------
# 9️⃣ أنواع البرادات (BOM)
# -------------------------------------------------------------
elif selected_tab == "🛠️ أنواع البرادات (BOM)":
    st.markdown("### 🛠️ وصفات ومكونات البرادات (BOM)")
    for model, bom_items in factory_data["bom"].items():
        with st.expander(f"مكونات براد: {model}"):
            bom_df = pd.DataFrame(
                list(bom_items.items()),
                columns=["المادة الخام المطلوبة", "الكمية للوحدة الواحدة"],
            )
            st.dataframe(bom_df, use_container_width=True)
