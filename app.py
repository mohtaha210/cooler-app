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

DATA_FILE = "multi_factory_data.json"

# --- 1. إدارة ملف البيانات وتحديث الهيكلية ---
def get_default_factory_data(factory_name, admin_user, admin_pass):
    return {
        "info": {"factory_name": factory_name},
        "exchange_rate": 150000.0,
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
        },
        "finished_goods": {
            "براد حنفية واحدة": 0,
            "براد حنفيتين": 0,
        },
        "bom": {
            "براد حنفية واحدة": {"الحنفية": 1, "البانكة": 1, "الماطور": 1},
            "براد حنفيتين": {"الحنفية": 2, "البانكة": 1, "الماطور": 1},
        },
        "agents": {},
        "agent_ledger": [],
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
                    if "exchange_rate" not in f_data:
                        f_data["exchange_rate"] = 150000.0
                    if "finished_goods" not in f_data:
                        f_data["finished_goods"] = {model: 0 for model in f_data.get("bom", {}).keys()}
                    if "agents" not in f_data:
                        f_data["agents"] = {}
                    if "agent_ledger" not in f_data:
                        f_data["agent_ledger"] = []
                    if "receipt_counter" not in f_data:
                        f_data["receipt_counter"] = 1001
                    for a_name, a_info in f_data.get("agents", {}).items():
                        if "address" not in a_info:
                            a_info["address"] = "-"
                        if "balance_iqd" not in a_info:
                            a_info["balance_iqd"] = a_info.get("balance", 0.0)
                        if "balance_usd" not in a_info:
                            a_info["balance_usd"] = 0.0
                return data
        except Exception:
            return {}
    else:
        return {}

def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. دوال الطباعة والـ PDF (سند القبض المحدث نصف A4) ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

def generate_sanad_qabd_pdf(
    doc_no, doc_date, currency_name, agent_name, 
    amount_num, amount_text, prev_balance, new_balance, notes=""
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # إطار خارجي للسند
    pdf.set_draw_color(0, 0, 0)
    pdf.set_linewidth(0.5)
    pdf.rect(6, 6, 198, 136)

    # عنوان المستند
    pdf.set_font("Amiri", "", 22)
    pdf.set_xy(10, 10)
    pdf.cell(190, 10, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 11)

    # الجدول الأول
    start_y = 26
    pdf.set_xy(12, start_y)
    pdf.cell(62, 8, ar("العملة"), border=1, align="C")
    pdf.cell(62, 8, ar("رقم المستند"), border=1, align="C")
    pdf.cell(62, 8, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(12, start_y + 8)
    pdf.cell(62, 9, ar(currency_name), border=1, align="C")
    pdf.cell(62, 9, str(doc_no), border=1, align="C")
    pdf.cell(62, 9, str(doc_date), border=1, align="C")

    # الجدول الثاني
    start_y_2 = start_y + 23
    pdf.set_xy(12, start_y_2)
    pdf.cell(124, 8, ar("السيد"), border=1, align="C")
    pdf.cell(62, 8, ar("المبلغ"), border=1, align="C")

    pdf.set_xy(12, start_y_2 + 8)
    pdf.cell(124, 10, ar(agent_name), border=1, align="C")
    pdf.cell(62, 10, f"{amount_num:,.2f}", border=1, align="C")

    pdf.set_xy(12, start_y_2 + 18)
    pdf.cell(186, 10, ar(f"المبلغ كتابةً: {amount_text}"), border=1, align="R")

    # الجدول الثالث
    start_y_3 = start_y_2 + 35
    pdf.set_xy(12, start_y_3)
    pdf.cell(93, 8, ar("الرصيد بعد التسديد"), border=1, align="C")
    pdf.cell(93, 8, ar("الرصيد السابق"), border=1, align="C")

    pdf.set_xy(12, start_y_3 + 8)
    pdf.cell(93, 10, f"{new_balance:,.2f}", border=1, align="C")
    pdf.cell(93, 10, f"{prev_balance:,.2f}", border=1, align="C")

    if notes:
        pdf.set_xy(12, start_y_3 + 20)
        pdf.cell(186, 8, ar(f"الملاحظات: {notes}"), border=1, align="R")

    # التوقيعات
    pdf.set_xy(15, start_y_3 + 32)
    pdf.cell(80, 8, ar("توقيع المستلم: ...................."), align="L")
    pdf.set_xy(115, start_y_3 + 32)
    pdf.cell(80, 8, ar("توقيع المسلّم: ...................."), align="R")

    return bytes(pdf.output())

# --- 3. إعداد الصفحة والجلسة (نظام تسجيل الدخول) ---
st.set_page_config(
    page_title="نظام إدارة المخزون والوكلاء",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

all_factories = load_all_factories()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.factory_key = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_fullname = ""

if not st.session_state.authenticated:
    st.title("❄️ نظام إدارة وتتبع المعامل والمخزون والوكلاء")
    login_tab, register_tab = st.tabs(["🔑 تسجيل الدخول لمعمل", "🏭 إنشاء حساب معمل جديد"])

    with login_tab:
        factory_list = list(all_factories.keys())
        if not factory_list:
            st.info("💡 لا توجد معامل مسجلة بالنظام حالياً.")
        else:
            selected_factory = st.selectbox("اختر المعمل:", factory_list)
            username_input = st.text_input("اسم المستخدم:")
            password_input = st.text_input("كلمة المرور:", type="password")

            if st.button("تسجيل الدخول", type="primary", use_container_width=True):
                factory_users = all_factories[selected_factory].get("users", {})
                if username_input in factory_users and factory_users[username_input]["password"] == password_input:
                    st.session_state.authenticated = True
                    st.session_state.factory_key = selected_factory
                    st.session_state.username = username_input
                    st.session_state.role = factory_users[username_input]["role"]
                    st.session_state.user_fullname = factory_users[username_input]["name"]
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")

    with register_tab:
        new_factory_name = st.text_input("اسم المعمل الجديد:")
        admin_user = st.text_input("اسم مستخدم المدير:")
        admin_pass = st.text_input("كلمة مرور المدير:", type="password")

        if st.button("🚀 إنشاء المعمل وبدء الاستخدام", type="primary", use_container_width=True):
            if not new_factory_name or not admin_user or not admin_pass:
                st.error("يرجى إدخال البيانات كاملة.")
            elif new_factory_name in all_factories:
                st.error("اسم المعمل موجود بالفعل.")
            else:
                all_factories[new_factory_name] = get_default_factory_data(new_factory_name, admin_user, admin_pass)
                save_all_factories(all_factories)
                st.success("✅ تم إنشاء المعمل بنجاح!")

    st.stop()

# --- 4. تحميل بيانات المعمل والواجهة الرئيسية ---
current_factory_name = st.session_state.factory_key
factory_data = all_factories[current_factory_name]

# الشريط العلوي
st.title(f"❄️ {current_factory_name}")
col_u1, col_u2, col_u3 = st.columns([2, 1.5, 1])
with col_u1:
    role_badge = "👑 مدير المعمل" if st.session_state.role == "admin" else "👷 موظف"
    st.info(f"المستخدم: **{st.session_state.user_fullname}** | {role_badge}")

with col_u2:
    current_rate = factory_data.get("exchange_rate", 150000.0)
    if st.session_state.role == "admin":
        new_rate = st.number_input("💵 سعر صرف 100$ بالدينار:", value=float(current_rate), step=500.0)
        if new_rate != current_rate:
            factory_data["exchange_rate"] = new_rate
            save_all_factories(all_factories)
    else:
        st.metric("سعر صرف 100$", f"{current_rate:,.0f} د.ع")

with col_u3:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.factory_key = None
        st.rerun()

st.write("---")

# --- 5. التبويبات الرئيسية للنظام ---
if st.session_state.role == "admin":
    tabs = st.tabs([
        "📝 إصدار سند قبض",
        "🤝 إدارة الوكلاء",
        "🔄 تحويل العملات",
        "📊 التقارير",
        "🏭 تسجيل إنتاج",
        "📦 المخزون",
    ])
else:
    tabs = st.tabs([
        "📝 إصدار سند قبض",
        "🤝 دليل الوكلاء",
        "📦 المخزون الحالي",
    ])

# ==========================================
# التبويب 1: إصدار سند قبض (الجديد المدمج)
# ==========================================
tab_pay = tabs[0]
with tab_pay:
    st.header("📝 إصدار سند قبض (قياس نصف A4)")
    st.info("💡 يمكنك اختيار وكيل مسجل ليتم سحب رصيده تلقائياً، أو كتابة اسم وكيل جديد يدوياً.")

    agent_list = ["-- إدخال يدوي حر --"] + list(factory_data["agents"].keys())
    selected_agent = st.selectbox("اختر الوكيل (أو اختر إدخال حر):", agent_list)

    col_p1, col_p2 = st.columns(2)

    with col_p1:
        next_counter = int(factory_data.get("receipt_counter", 1001))
        doc_no = st.number_input("رقم المستند:", value=next_counter, step=1)
        doc_date = st.date_input("تاريخ المستند:", value=datetime.now())
        currency_name = st.selectbox("العملة:", ["دولار", "دينار عراقي"])
        
        # إذا كان الإدخال حر، نظهر حقل نصي، وإلا نستخدم اسم الوكيل المختار
        if selected_agent == "-- إدخال يدوي حر --":
            agent_name_input = st.text_input("السيد (اسم الزبون):", value="", placeholder="ادخل اسم الشخص...")
        else:
            agent_name_input = st.text_input("السيد (اسم الزبون):", value=selected_agent, disabled=True)

    with col_p2:
        amount_num = st.number_input("المبلغ الواصل (رقماً):", value=0.0, step=10.0)
        amount_text = st.text_input("المبلغ (كتابةً):", value="", placeholder="مثال: مئة دولار فقط...")
        
        # سحب الرصيد السابق تلقائياً إذا كان وكيل مسجل
        if selected_agent != "-- إدخال يدوي حر --":
            if currency_name == "دولار":
                auto_prev_balance = factory_data["agents"][selected_agent].get("balance_usd", 0.0)
            else:
                auto_prev_balance = factory_data["agents"][selected_agent].get("balance_iqd", 0.0)
            prev_balance = st.number_input("الرصيد السابق:", value=float(auto_prev_balance), step=10.0)
        else:
            prev_balance = st.number_input("الرصيد السابق:", value=0.0, step=10.0)

        calc_new_bal = prev_balance - amount_num
        new_balance = st.number_input("الرصيد بعد التسديد:", value=float(calc_new_bal), step=10.0)

    notes = st.text_input("الملاحظات (اختياري):", value="", placeholder="أي ملاحظات إضافية...")

    if st.button("🖨️ تسجيل وحفظ وطباعة السند (PDF)", type="primary", use_container_width=True):
        if not agent_name_input.strip():
            st.error("⚠️ يرجى إدخال اسم السيد / العميل!")
        elif amount_num <= 0:
            st.error("⚠️ يرجى إدخال مبلغ أكبر من صفر!")
        else:
            # توليد الـ PDF
            pdf_bytes = generate_sanad_qabd_pdf(
                doc_no=doc_no,
                doc_date=doc_date.strftime("%d-%m-%Y"),
                currency_name=currency_name,
                agent_name=agent_name_input,
                amount_num=amount_num,
                amount_text=amount_text,
                prev_balance=prev_balance,
                new_balance=new_balance,
                notes=notes
            )

            # تحديث حساب الوكيل في النظام إذا كان مسجلاً
            if selected_agent != "-- إدخال يدوي حر --":
                if currency_name == "دولار":
                    factory_data["agents"][selected_agent]["balance_usd"] = new_balance
                else:
                    factory_data["agents"][selected_agent]["balance_iqd"] = new_balance

            # تحديث العداد
            factory_data["receipt_counter"] = doc_no + 1
            save_all_factories(all_factories)

            st.success(f"✅ تم إصدار سند القبض رقم #{doc_no} وتحديث الحسابات بنجاح!")
            st.download_button(
                label=f"📥 تنزيل سند القبض (PDF)",
                data=pdf_bytes,
                file_name=f"سند_قبض_{doc_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ==========================================
# التبويب 2: إدارة الوكلاء
# ==========================================
tab_agents = tabs[1]
with tab_agents:
    st.header("🤝 إدارة الوكلاء (الديون بالدينار والدولار)")
    col_ag1, col_ag2 = st.columns([1, 2])

    if st.session_state.role == "admin":
        with col_ag1:
            st.subheader("➕ إضافة وكيل جديد")
            new_agent_name = st.text_input("اسم الوكيل / المحل:")
            new_agent_address = st.text_input("عنوان الوكيل:")
            init_iqd = st.number_input("الرصيد الافتتاحي (دينار د.ع):", value=0.0, step=50000.0)
            init_usd = st.number_input("الرصيد الافتتاحي (دولار $):", value=0.0, step=100.0)

            if st.button("➕ تسجيل الوكيل بالنظام", type="primary", use_container_width=True):
                if not new_agent_name.strip():
                    st.error("يرجى إدخال اسم الوكيل!")
                elif new_agent_name in factory_data["agents"]:
                    st.error("اسم هذا الوكيل موجود بالفعل!")
                else:
                    factory_data["agents"][new_agent_name] = {
                        "address": new_agent_address if new_agent_address.strip() else "-",
                        "balance_iqd": init_iqd,
                        "balance_usd": init_usd,
                    }
                    save_all_factories(all_factories)
                    st.success("✅ تم إضافة الوكيل بنجاح!")
                    st.rerun()

    with col_ag2:
        st.subheader("📋 قائمة الوكلاء والأرصدة")
        if not factory_data["agents"]:
            st.info("لا يوجد وكلاء مسجلون بالنظام حتى الآن.")
        else:
            agents_list = []
            for name, info in factory_data["agents"].items():
                agents_list.append({
                    "اسم الوكيل": name,
                    "عنوان الوكيل": info.get("address", "-"),
                    "الديون (بالدينار د.ع)": f"{info.get('balance_iqd', 0.0):,.0f}",
                    "الديون (بالدولار $)": f"{info.get('balance_usd', 0.0):,.2f}",
                })
            st.dataframe(pd.DataFrame(agents_list), use_container_width=True)

# باقي التبويبات (متروكة كعناوين لتضيف فيها المنطق الخاص بك كما كان)
if st.session_state.role == "admin":
    with tabs[2]: st.header("🔄 تحويل العملات")
    with tabs[3]: st.header("📊 التقارير الشاملة")
    with tabs[4]: st.header("🏭 تسجيل الإنتاج")
    with tabs[5]: st.header("📦 إدارة المخزون")
else:
    with tabs[2]: st.header("📦 المخزون الحالي")
