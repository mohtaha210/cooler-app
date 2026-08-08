from datetime import datetime
import json
import os
import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF
import pandas as pd
import requests
import streamlit as st

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="نظام إدارة المعامل والمخزون",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- تطبيق تصميم الـ UI الداكن الحديث مع تبويبات أنيقة ---
st.markdown(
    """
<style>
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* الهيدر العلوي */
    .header-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px 25px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* أزرار الراديو المصممة كـ Segmented Tabs حداثية */
    div[data-testid="stRadio"] > div {
        background-color: #1e293b;
        padding: 6px;
        border-radius: 14px;
        border: 1px solid #334155;
        display: flex;
        gap: 6px;
    }
    
    div[data-testid="stRadio"] label {
        background-color: transparent;
        color: #94a3b8 !important;
        padding: 10px 16px !important;
        border-radius: 10px !important;
        border: none !important;
        flex: 1;
        text-align: center;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease-in-out;
    }
    
    div[data-testid="stRadio"] label:hover {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.05);
    }

    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    
    /* إخفاء دائرة الاختيار الأصلية للـ Radio */
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* بطاقات الأقسام المخصصة */
    .content-card {
        background-color: #151e32;
        border-radius: 16px;
        border: 1px solid #24324d;
        padding: 24px;
        margin-top: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }

    /* الحقول والمداخلات */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
        background-color: #0f172a !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }
    
    /* الأزرار الرئيسية */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
    }

    /* بطاقات الميتريك/الإحصائيات */
    div[data-testid="stMetric"] {
        background-color: #151e32;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #24324d;
    }
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "multi_factory_data.json"


# --- 1. إدارة ملف البيانات والتخزين الدائم ---
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
                return data
        except Exception:
            return {}
    return {}


def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- 2. إعداد الجلسة وقراءة البيانات ---
all_factories = load_all_factories()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.factory_key = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_fullname = ""

# --- 3. تسجيل الدخول ---
if not st.session_state.authenticated:
    st.markdown(
        "<h2 style='text-align: center; margin-top: 50px;'>🍏 نظام إدارة"
        " المعامل الذكي</h2>",
        unsafe_allow_html=True,
    )

    auth_action = st.radio(
        "", ["🔑 تسجيل الدخول", "🏭 إنشاء معمل جديد"], horizontal=True
    )

    with st.container():
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        if auth_action == "🔑 تسجيل الدخول":
            factory_list = list(all_factories.keys())
            if not factory_list:
                st.info("لا توجد معامل مسجلة. قم بإنشاء حساب جديد.")
            else:
                selected_factory = st.selectbox("اختر المعمل:", factory_list)
                username_input = st.text_input("اسم المستخدم:")
                password_input = st.text_input("كلمة المرور:", type="password")

                if st.button(
                    "دخول النظام", type="primary", use_container_width=True
                ):
                    factory_users = all_factories[selected_factory].get(
                        "users", {}
                    )
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
                        st.error("خطأ في البيانات!")
        else:
            new_f_name = st.text_input("اسم المعمل:")
            admin_u = st.text_input("اسم مستخدم المدير:")
            admin_p = st.text_input("كلمة المرور:", type="password")
            if st.button(
                "إنشاء وتفعيل", type="primary", use_container_width=True
            ):
                if new_f_name and admin_u and admin_p:
                    all_factories[new_f_name] = get_default_factory_data(
                        new_f_name, admin_u, admin_p
                    )
                    save_all_factories(all_factories)
                    st.success("تم الإنشاء بنجاح!")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. تحميل المعمل الحالي ---
current_factory_name = st.session_state.factory_key
factory_data = all_factories[current_factory_name]

# --- 5. الهيدر العلوي الحديث ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown(
        f"""
    <div class="header-card" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #ffffff;">🍏 {current_factory_name}</h2>
            <span style="color: #38bdf8;">مرحباً، {st.session_state.user_fullname}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with header_col2:
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 6. نظام التبويبات الحديث المطور (Segmented Control Navigation) ---
if st.session_state.role == "admin":
    main_menu = [
        "📊 المالية والتقارير",
        "🤝 إدارة الوكلاء والديون",
        "🛒 بيع وفواتير",
        "📦 المخزون والمنتجات",
        "👥 الإعدادات والموظفين",
    ]
else:
    main_menu = [
        "🛒 بيع وفواتير",
        "🤝 إدارة الوكلاء والديون",
        "📦 المخزون والمنتجات",
    ]

# شريط التصفح الرئيسي المنزلق
selected_tab = st.radio("", main_menu, horizontal=True)

st.markdown('<div class="content-card">', unsafe_allow_html=True)

# -------------------------------------------------------------
# 1️⃣ قسم المالية والتقارير
# -------------------------------------------------------------
if selected_tab == "📊 المالية والتقارير":
    st.subheader("📊 لوحة المتابعة الإحصائية والمالية")

    total_debts = sum(
        ag.get("debt", 0.0)
        for ag in factory_data["agents"].values()
        if isinstance(ag, dict)
    )
    sales_df = pd.DataFrame(factory_data.get("sales_history", []))

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            "إجمالي المبيعات",
            f"{sales_df['total'].sum() if not sales_df.empty else 0:,} د.ع",
        )
    with m2:
        st.metric(
            "عدد الفواتير الصادرة", f"{len(sales_df) if not sales_df.empty else 0}"
        )
    with m3:
        st.metric("ديون لنا لدى الوكلاء", f"{total_debts:,} د.ع")

    st.write("---")
    st.markdown("##### 📜 سجل الفواتير والمبيعات الأخيرة")
    if not sales_df.empty:
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")

# -------------------------------------------------------------
# 2️⃣ قسم إدارة الوكلاء والديون (مصمم بتبويبات فرعية أنيقة)
# -------------------------------------------------------------
elif selected_tab == "🤝 إدارة الوكلاء والديون":
    st.subheader("🤝 مركز إدارة الوكلاء والتسديدات")

    # تبويبات فرعية حديثة داخل قسم الوكلاء
    agent_action = st.radio(
        "اختر الإجراء المطلوبة:",
        ["➕ إضافة وكيل جديد", "💵 تسديد دفعات الديون", "📜 كشف حساب وكيل"],
        horizontal=True,
        key="agent_sub_tab",
    )

    st.write("---")

    if agent_action == "➕ إضافة وكيل جديد":
        c1, c2 = st.columns(2)
        with c1:
            ag_name = st.text_input("اسم الوكيل / المحل:")
            ag_phone = st.text_input("رقم الهاتف:")
        with c2:
            ag_initial_debt = st.number_input(
                "الذمة / الدين الأول:", min_value=0.0, step=10000.0
            )

        if st.button("حفظ وتسجيل الوكيل", type="primary"):
            if ag_name.strip() and ag_name not in factory_data["agents"]:
                factory_data["agents"][ag_name] = {
                    "phone": ag_phone,
                    "debt": ag_initial_debt,
                    "transactions": [],
                }
                save_all_factories(all_factories)
                st.success(f"✅ تم إضافة الوكيل [{ag_name}] بنجاح!")
                st.rerun()
            else:
                st.error("الاسم أدخل بشكل خاطئ أو مسجل سابقاً.")

    elif agent_action == "💵 تسديد دفعات الديون":
        agents_list = list(factory_data["agents"].keys())
        if not agents_list:
            st.info("لا يوجد وكلاء مسجلين حالياً.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                selected_ag = st.selectbox("اختر الوكيل:", agents_list)
                current_debt = factory_data["agents"][selected_ag].get(
                    "debt", 0.0
                )
                st.warning(f"💰 الدين الحالي الذمة: **{current_debt:,} د.ع**")

            with c2:
                pay_amount = st.number_input(
                    "المبلغ المدفوع (د.ع):",
                    min_value=1.0,
                    value=50000.0,
                    step=25000.0,
                )

            if st.button(
                "تأكيد وخصم الدفعة", type="primary", use_container_width=True
            ):
                new_debt = current_debt - pay_amount
                factory_data["agents"][selected_ag]["debt"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)

                factory_data["agents"][selected_ag].setdefault(
                    "transactions", []
                ).append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "تسديد دفعة",
                    "amount": -pay_amount,
                    "balance": new_debt,
                    "note": f"وصل قبض #{receipt_no}",
                })
                factory_data["receipt_counter"] = receipt_no + 1
                save_all_factories(all_factories)
                st.success("✅ تم خصم المبلغ وتحديث الحساب!")
                st.rerun()

    elif agent_action == "📜 كشف حساب وكيل":
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            sel_ag_view = st.selectbox(
                "عرض سجل التعاملات للوكيل:", agents_list
            )
            ag_info = factory_data["agents"][sel_ag_view]
            st.info(
                f"👤 الهاتف: {ag_info.get('phone', 'غير محدد')} | 💳 الرصيد"
                f" المتبقي: **{ag_info.get('debt', 0):,} د.ع**"
            )

            trans_df = pd.DataFrame(ag_info.get("transactions", []))
            if not trans_df.empty:
                st.dataframe(trans_df, use_container_width=True)
            else:
                st.info("لا يوجد سجل حركة مالية لهذا الوكيل.")

# -------------------------------------------------------------
# 3️⃣ قسم البيع والفواتير
# -------------------------------------------------------------
elif selected_tab == "🛒 بيع وفواتير":
    st.subheader("🛒 نقطة البيع وإصدار الفواتير")

    customer_type = st.radio(
        "نوع العميل:", ["مباشر (نقداً)", "وكيل معتمد (أجل/جزئي)"], horizontal=True
    )

    if customer_type == "مباشر (نقداً)":
        customer_name = st.text_input("اسم المشتري:")
    else:
        agents_list = list(factory_data["agents"].keys())
        customer_name = (
            st.selectbox("اختر الوكيل:", agents_list) if agents_list else ""
        )

    st.write("---")
    st.markdown("##### 📦 اختر الكميات والأسعار:")

    model_list = list(factory_data["bom"].keys())
    selected_items = []
    grand_total = 0

    for model in model_list:
        stock_available = factory_data["finished_goods"].get(model, 0)
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.write(f"**{model}** (المتوفر: `{stock_available}`)")
        with c2:
            qty = st.number_input(
                "العدد:", min_value=0, max_value=max(0, stock_available), key=f"q_{model}"
            )
        with c3:
            price = st.number_input(
                "سعر القطعة:", min_value=0, value=250000, key=f"p_{model}"
            )

        if qty > 0:
            total_p = qty * price
            grand_total += total_p
            selected_items.append(
                {"model": model, "count": qty, "price": price, "total": total_p}
            )

    st.markdown(f"### 💳 المبلغ الإجمالي: `{grand_total:,}` د.ع")

    if st.button(
        "تأكيد عملية البيع", type="primary", use_container_width=True
    ):
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

            st.success("✅ تم حفظ الفاتورة وتحديث المخزون!")
            st.rerun()

# -------------------------------------------------------------
# 4️⃣ قسم المخزون والمنتجات
# -------------------------------------------------------------
elif selected_tab == "📦 المخزون والمنتجات":
    st.subheader("📦 حالة المخزن والتجميع")

    inv_tab = st.radio(
        "القسم الفرعي:",
        ["❄️ المنتجات الجاهزة", "🧱 مواد الخام والمكونات"],
        horizontal=True,
    )

    st.write("---")
    if inv_tab == "❄️ المنتجات الجاهزة":
        fg_df = pd.DataFrame(
            list(factory_data["finished_goods"].items()),
            columns=["الموديل / نوع البراد", "الكمية المتاحة للبيع"],
        )
        st.dataframe(fg_df, use_container_width=True)
    else:
        raw_df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية بالمخزن"],
        )
        st.dataframe(raw_df, use_container_width=True)

# -------------------------------------------------------------
# 5️⃣ قسم الإعدادات والموظفين
# -------------------------------------------------------------
elif selected_tab == "👥 الإعدادات والموظفين":
    st.subheader("⚙️ إعدادات النظام والمستخدمين")
    users_df = pd.DataFrame(factory_data["users"]).T[["name", "role"]]
    st.dataframe(users_df, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)
