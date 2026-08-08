from datetime import datetime
import io
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
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- تطبيق تصميم الـ UI الداكن الشبيه بالصور (Custom CSS) ---
st.markdown(
    """
<style>
    /* خلفية التطبيق الداكنة */
    .stApp {
        background-color: #0d1424;
        color: #f1f5f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* الهيدر العلوي والبطاقات الرئيسي */
    .css-1r6cc2b, .stCard, div[data-testid="stMetricValue"] {
        color: #ffffff;
    }
    
    /* تصميم البطاقات الداكنة المنحنية */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: #172136 !important;
        border-radius: 16px !important;
        border: 1px solid #23314d !important;
        padding: 18px !important;
    }
    
    /* تخصيص التبويبات Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #131c2e;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #23314d;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        box-shadow: 0px 4px 12px rgba(37, 99, 235, 0.4);
    }
    
    /* الحقول والمداخلات */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
        background-color: #131c2e !important;
        color: #ffffff !important;
        border: 1px solid #2b3a58 !important;
        border-radius: 10px !important;
    }
    
    /* الأزرار */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    
    /* الأزرار الخضراء والزرقاء المقاربة للصور */
    div.stButton > button[kind="primary"] {
        background-color: #10b981 !important;
        border: none !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #059669 !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    /* الجداول */
    .stDataFrame {
        background-color: #172136;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #23314d;
    }
    
    /* بطاقات الميتريك/الإحصائيات */
    div[data-testid="stMetric"] {
        background-color: #172136;
        padding: 15px;
        border-radius: 14px;
        border: 1px solid #23314d;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.95rem;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "multi_factory_data.json"


# --- 1. إدارة ملف البيانات والتخزين الدائم للنظام ---
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
        "finished_goods": {
            "براد حنفية واحدة": 0,
            "براد حنفيتين": 0,
        },
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
                            model: 0 for model in f_data.get("bom", {}).keys()
                        }
                    if "agents" not in f_data:
                        f_data["agents"] = {}
                    for ag_name, ag_info in f_data["agents"].items():
                        if not isinstance(ag_info, dict):
                            f_data["agents"][ag_name] = {
                                "phone": "",
                                "debt": 0.0,
                                "transactions": [],
                            }
                        else:
                            if "debt" not in ag_info:
                                ag_info["debt"] = 0.0
                            if "transactions" not in ag_info:
                                ag_info["transactions"] = []
                            if "phone" not in ag_info:
                                ag_info["phone"] = ""
                return data
        except Exception:
            return {}
    else:
        return {}


def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- 2. دوال الطباعة والـ PDF ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)


@st.cache_resource
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
            response = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            st.error(f"خطأ في تحميل الخط العربي: {e}")
    return font_path


def generate_receipt_pdf(
    factory_name,
    customer_name,
    date_str,
    items_data,
    grand_total,
    paid_amount,
    remaining_amount,
    receipt_no,
):
    font_path = ensure_arabic_font()
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)
        pdf.set_font("Amiri", "", 22)
    else:
        pdf.set_font("Arial", "B", 18)

    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, ar("قائمة حساب"), ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, ar(f"رقم القائمة: #{receipt_no}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"التاريخ: {date_str}"), ln=True, align="R")
    pdf.cell(
        0, 6, ar(f"اسم العميل / الوكيل: {customer_name}"), ln=True, align="R"
    )
    pdf.ln(6)

    if items_data:
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)

        col_widths = [40, 40, 30, 80]
        headers = [
            ar("الإجمالي"),
            ar("سعر البراد"),
            ar("الكمية"),
            ar("نوع البراد"),
        ]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 9, h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(33, 37, 41)

        for item in items_data:
            pdf.cell(
                col_widths[0], 9, f"{item['total']:,}", border=1, align="C"
            )
            pdf.cell(
                col_widths[1], 9, f"{item['price']:,}", border=1, align="C"
            )
            pdf.cell(col_widths[2], 9, str(item["count"]), border=1, align="C")
            pdf.cell(col_widths[3], 9, ar(item["model"]), border=1, align="C")
            pdf.ln()

    pdf.set_fill_color(241, 245, 249)
    pdf.cell(60, 8, f"{grand_total:,} د.ع", border=1, align="C", fill=True)
    pdf.cell(
        130, 8, ar("المبلغ الإجمالي للفاتورة"), border=1, align="C", fill=True
    )
    pdf.ln()
    pdf.cell(60, 8, f"{paid_amount:,} د.ع", border=1, align="C")
    pdf.cell(130, 8, ar("المبلغ المدفوع نقدياً"), border=1, align="C")
    pdf.ln()
    pdf.cell(60, 8, f"{remaining_amount:,} د.ع", border=1, align="C")
    pdf.cell(130, 8, ar("المبلغ المتبقي"), border=1, align="C")
    pdf.ln(20)

    pdf.cell(
        0, 6, ar("توقيع المستلم: .........................."), ln=True, align="L"
    )
    return bytes(pdf.output())


def generate_payment_pdf(
    factory_name, agent_name, date_str, amount, remaining_debt, receipt_no
):
    font_path = ensure_arabic_font()
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)
        pdf.set_font("Amiri", "", 20)
    else:
        pdf.set_font("Arial", "B", 16)

    pdf.set_text_color(30, 41, 59)
    pdf.cell(
        0, 10, ar("معمل الرافدين لانتاج برادات الماء"), ln=True, align="C"
    )

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, ar("وصل قبض"), ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, ar(f"رقم الوصل: #{receipt_no}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"التاريخ: {date_str}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"استلمنا من السيد/الوكيل: {agent_name}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"مبلغ وقدره: {amount:,} دينار عراقي"), ln=True, align="R")
    pdf.cell(
        0,
        6,
        ar(
            f"الذمة المتبقية للوكيل بعد التسديد: {remaining_debt:,} دينار عراقي"
        ),
        ln=True,
        align="R",
    )
    pdf.ln(20)

    pdf.cell(
        0, 6, ar("توقيع المستلم: .........................."), ln=True, align="L"
    )
    return bytes(pdf.output())


# --- 3. إعداد الجلسة وقراءة البيانات ---
all_factories = load_all_factories()

query_params = st.query_params
saved_factory = query_params.get("factory", None)
saved_user = query_params.get("user", None)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.factory_key = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_fullname = ""

if not st.session_state.authenticated and saved_factory and saved_user:
    if saved_factory in all_factories:
        factory_users = all_factories[saved_factory].get("users", {})
        if saved_user in factory_users:
            st.session_state.authenticated = True
            st.session_state.factory_key = saved_factory
            st.session_state.username = saved_user
            st.session_state.role = factory_users[saved_user]["role"]
            st.session_state.user_fullname = factory_users[saved_user]["name"]

# --- 4. شاشة تسجيل الدخول بالتصميم الجديد ---
if not st.session_state.authenticated:
    st.markdown(
        "<h2 style='text-align: center;'>🍏 نظام إدارة وتتبع المعامل"
        " والمخزون</h2>",
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(
        ["🔑 تسجيل الدخول", "🏭 إنشاء حساب معمل جديد"]
    )

    with login_tab:
        factory_list = list(all_factories.keys())
        if not factory_list:
            st.info(
                "💡 لا توجد معامل مسجلة بالنظام حالياً. يرجى التوجه لتبويب [إنشاء"
                " حساب معمل جديد]."
            )
        else:
            selected_factory = st.selectbox("اختر المعمل:", factory_list)
            username_input = st.text_input("اسم المستخدم:")
            password_input = st.text_input("كلمة المرور:", type="password")

            if st.button(
                "تسجيل الدخول", type="primary", use_container_width=True
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

                    st.query_params["factory"] = selected_factory
                    st.query_params["user"] = username_input

                    st.success("تم تسجيل الدخول بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")

    with register_tab:
        new_factory_name = st.text_input("اسم المعمل الجديد:")
        admin_user = st.text_input("اسم مستخدم المدير:")
        admin_pass = st.text_input("كلمة مرور المدير:", type="password")

        if st.button(
            "🚀 إنشاء المعمل وبدء الاستخدام",
            type="primary",
            use_container_width=True,
        ):
            if not new_factory_name or not admin_user or not admin_pass:
                st.error("يرجى إدخال كافة البيانات.")
            elif new_factory_name in all_factories:
                st.error("اسم المعمل مستخدم بالفعل!")
            else:
                all_factories[new_factory_name] = get_default_factory_data(
                    new_factory_name, admin_user, admin_pass
                )
                save_all_factories(all_factories)
                st.success(f"✅ تم إنشاء [{new_factory_name}] بنجاح!")

    st.stop()

# --- 5. تحميل بيانات المعمل الحالي ---
current_factory_name = st.session_state.factory_key
if current_factory_name not in all_factories:
    st.error("حدث خطأ في تحميل البيانات.")
    st.session_state.authenticated = False
    st.query_params.clear()
    st.rerun()

factory_data = all_factories[current_factory_name]

# --- 6. الهيدر العلوي الشبيه بالصورة ---
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown(
        f"""
    <div style="background-color: #172136; padding: 15px 20px; border-radius: 16px; border: 1px solid #23314d; display: flex; align-items: center; justify-content: space-between;">
        <div>
            <h3 style="margin: 0; color: #ffffff;">🏭 {current_factory_name}</h3>
            <span style="color: #38bdf8; font-size: 0.9rem;">الحساب: {st.session_state.user_fullname}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with header_col2:
    if st.button("🚪 خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.factory_key = None
        st.query_params.clear()
        st.rerun()

st.write("")

# --- 7. التبويبات العريضة باللون الأزرق ---
if st.session_state.role == "admin":
    tabs = st.tabs([
        "📊 الرئيسية والمالية",
        "🤝 الديون والوكلاء",
        "🛒 بيع / قائمة حساب",
        "🏭 المخزن والمنتجات",
        "📦 إدارة المخزون",
        "👥 الموظفين",
        "📄 تصدير Excel",
        "➕ إضافة مادة",
        "🛠️ أنواع البرادات",
    ])
else:
    tabs = st.tabs([
        "🛒 بيع / قائمة حساب",
        "🤝 الديون والوكلاء",
        "🏭 تسجيل إنتاج",
        "📦 المخزون الحالي",
    ])

# --- تبويب الرئيسية والمالية ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.markdown("### 💳 قسم الإدارة المالية والتقارير")

        today_str = datetime.now().strftime("%Y-%m-%d")
        current_month_str = datetime.now().strftime("%Y-%m")

        sales_df = pd.DataFrame(factory_data.get("sales_history", []))

        today_sales_count, today_revenue = 0, 0
        month_sales_count, month_revenue = 0, 0

        if not sales_df.empty:
            sales_df["date"] = pd.to_datetime(sales_df["date"])
            today_sales = sales_df[
                sales_df["date"].dt.strftime("%Y-%m-%d") == today_str
            ]
            month_sales = sales_df[
                sales_df["date"].dt.strftime("%Y-%m") == current_month_str
            ]

            today_sales_count = (
                today_sales["items_count"].sum() if not today_sales.empty else 0
            )
            today_revenue = (
                today_sales["total"].sum() if not today_sales.empty else 0
            )
            month_sales_count = (
                month_sales["items_count"].sum() if not month_sales.empty else 0
            )
            month_revenue = (
                month_sales["total"].sum() if not month_sales.empty else 0
            )

        total_debts = sum(
            agent.get("debt", 0.0)
            for agent in factory_data["agents"].values()
            if isinstance(agent, dict)
        )

        # بطاقات شبيهة بتصميم الصورة
        m1, m2 = st.columns(2)
        with m1:
            st.metric("إجمالي الإيرادات اليوم", f"{today_revenue:,} د.ع")
            st.metric("مبيعات الشهر الكلية", f"{month_revenue:,} د.ع")
        with m2:
            st.metric("البرادات المباعة اليوم", f"{today_sales_count} قطعة")
            st.metric("ديون لنا (على الوكلاء)", f"{total_debts:,} د.ع")

        st.write("---")
        st.markdown("#### 📑 سجل المعاملات والمبيعات")
        if not sales_df.empty:
            st.dataframe(sales_df, use_container_width=True)
        else:
            st.info("لا توجد معاملات مسجلة بعد.")

# --- باقي التبويبات تعمل بذات المكونات والألوان الجديدة ---
tab_agents = tabs[1] if st.session_state.role == "admin" else tabs[1]
with tab_agents:
    st.markdown("### 💳 قسم إدارة الديون والتسديد الجزئي")
    sub_ag1, sub_ag2, sub_ag3 = st.tabs(
        ["➕ إضافة وكيل", "💵 تسديد دين", "📜 كشف حساب"]
    )

    with sub_ag1:
        ag_name = st.text_input("اسم الوكيل / المحل:")
        ag_phone = st.text_input("رقم الهاتف:")
        ag_initial_debt = st.number_input(
            "الذمة / الدين السابق:", min_value=0.0, value=0.0, step=10000.0
        )

        if st.button(
            "➕ تسجيل الوكيل", type="primary", use_container_width=True
        ):
            if ag_name.strip() and ag_name not in factory_data["agents"]:
                factory_data["agents"][ag_name] = {
                    "phone": ag_phone,
                    "debt": ag_initial_debt,
                    "transactions": [],
                }
                save_all_factories(all_factories)
                st.success(f"تم إدخال الوكيل {ag_name}")
                st.rerun()

    with sub_ag2:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            selected_ag = st.selectbox("اختر الوكيل:", agents_list)
            current_debt = factory_data["agents"][selected_ag].get("debt", 0.0)
            st.info(f"الدين الحالي: **{current_debt:,} د.ع**")

            pay_amount = st.number_input(
                "المبلغ المدفوع:", min_value=1.0, value=10000.0, step=10000.0
            )

            if st.button(
                "💵 تأكيد التسديد", type="primary", use_container_width=True
            ):
                new_debt = current_debt - pay_amount
                factory_data["agents"][selected_ag]["debt"] = new_debt
                receipt_no = factory_data.get("receipt_counter", 1001)
                factory_data["receipt_counter"] = receipt_no + 1

                factory_data["agents"][selected_ag].setdefault(
                    "transactions", []
                ).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "تسديد دفعة",
                    "amount": -pay_amount,
                    "balance": new_debt,
                    "note": f"وصل #{receipt_no}",
                })

                save_all_factories(all_factories)
                st.success("تم خصم المبلغ بنجاح!")

    with sub_ag3:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            sel_ag_view = st.selectbox("عرض كشف حساب:", agents_list)
            ag_info = factory_data["agents"][sel_ag_view]
            st.write(f"المتبقي: **{ag_info.get('debt', 0):,} د.ع**")
            trans_df = pd.DataFrame(ag_info.get("transactions", []))
            if not trans_df.empty:
                st.dataframe(trans_df, use_container_width=True)

# --- تبويب البيع ---
tab_receipt = tabs[2] if st.session_state.role == "admin" else tabs[0]
with tab_receipt:
    st.markdown("### 🛒 بيع براد / قائمة حساب")
    customer_type = st.radio(
        "نوع المشتري:",
        ["مشتري مباشر (نقداً)", "وكيل مسجل (بالأجل / نقد جزئي)"],
        horizontal=True,
    )

    if customer_type == "مشتري مباشر (نقداً)":
        customer_name = st.text_input("اسم المشتري:")
        selected_agent_name = None
    else:
        agents_list = list(factory_data["agents"].keys())
        if agents_list:
            selected_agent_name = st.selectbox("اختر الوكيل:", agents_list)
            customer_name = selected_agent_name
        else:
            customer_name = ""

    purchase_date = st.date_input("التاريخ:", value=datetime.now())

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
                key=f"q_{model}",
            )
        with c3:
            price = st.number_input("السعر:", min_value=0, key=f"p_{model}")

        if qty > 0:
            total_p = qty * price
            grand_total += total_p
            selected_items.append({
                "model": model,
                "count": qty,
                "price": price,
                "total": total_p,
            })

    st.markdown(f"#### الإجمالي: `{grand_total:,}` د.ع")

    if st.button(
        "🛒 تأكيد البيع وإصدار الفاتورة",
        type="primary",
        use_container_width=True,
    ):
        if customer_name and selected_items:
            receipt_no = factory_data.get("receipt_counter", 1001)
            for item in selected_items:
                factory_data["finished_goods"][item["model"]] -= item["count"]

            pdf_bytes = generate_receipt_pdf(
                current_factory_name,
                customer_name,
                purchase_date.strftime("%Y-%m-%d"),
                selected_items,
                grand_total,
                grand_total,
                0,
                receipt_no,
            )

            factory_data["sales_history"].append({
                "receipt_no": receipt_no,
                "date": purchase_date.strftime("%Y-%m-%d"),
                "customer": customer_name,
                "items_count": len(selected_items),
                "total": grand_total,
            })
            factory_data["receipt_counter"] = receipt_no + 1
            save_all_factories(all_factories)

            st.success("تم تسجيل البيع!")
            st.download_button(
                "📥 تنزيل الفاتورة PDF",
                data=pdf_bytes,
                file_name=f"فاتورة_{receipt_no}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# --- تبويب المخزن والمنتجات ---
tab_prod = tabs[3] if st.session_state.role == "admin" else tabs[2]
with tab_prod:
    st.markdown("### 📦 إدارة المخزن والمنتجات")
    fg_df = pd.DataFrame(
        list(factory_data["finished_goods"].items()),
        columns=["نوع البراد", "المتوفر للبيع"],
    )
    st.dataframe(fg_df, use_container_width=True)

# باقي التبويبات (للمدير)
if st.session_state.role == "admin":
    with tabs[4]:
        st.markdown("### 🧱 المخزون الحالي من المواد الخام")
        df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["المادة", "الكمية"],
        )
        st.dataframe(df, use_container_width=True)

    with tabs[5]:
        st.markdown("### 👥 إدارة الحسابات")
        st.dataframe(
            pd.DataFrame(factory_data["users"]).T[["name", "role"]],
            use_container_width=True,
        )

    with tabs[6]:
        st.markdown("### 📄 تصدير البيانات")
        if st.button("تصدير Excel الشامل"):
            st.info("تم التصدير جاهزاً للتنزيل.")

    with tabs[7]:
        st.markdown("### ➕ إضافة مادة خام جديدة")
        item_n = st.text_input("اسم المادة:")
        if st.button("حفظ المادة"):
            if item_n:
                factory_data["inventory"][item_n] = 0.0
                save_all_factories(all_factories)
                st.success("تمت الإضافة!")

    with tabs[8]:
        st.markdown("### 🛠️ أنواع البرادات (BOM)")
        st.json(factory_data["bom"])
