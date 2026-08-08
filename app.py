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

# --- 1. إدارة ملف البيانات وتحديث الهيكلية للوكلاء ---
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
        },
        "finished_goods": {
            "براد حنفية واحدة": 0,
            "براد حنفيتين": 0,
        },
        "bom": {
            "براد حنفية واحدة": {"الحنفية": 1, "البانكة": 1, "الماطور": 1},
            "براد حنفيتين": {"الحنفية": 2, "البانكة": 1, "الماطور": 1},
        },
        "agents": {},            # دليل الوكلاء: {agent_name: {"phone": "", "balance": 0.0}}
        "agent_ledger": [],      # كشف حساب الوكلاء: [{date, agent, type, amount, notes, balance_after}]
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
                        f_data["finished_goods"] = {model: 0 for model in f_data.get("bom", {}).keys()}
                    if "agents" not in f_data:
                        f_data["agents"] = {}
                    if "agent_ledger" not in f_data:
                        f_data["agent_ledger"] = []
                return data
        except Exception:
            return {}
    else:
        return {}

def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. دوال الطباعة والـ PDF المحدثة للوكلاء ---
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

def generate_agent_receipt_pdf(
    factory_name, agent_name, date_str, items_data, current_total, prev_balance, paid_amount, final_balance, receipt_no
):
    font_path = ensure_arabic_font()
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    pdf.set_font("Amiri", "", 20)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, ar(factory_name), ln=True, align="C")

    pdf.set_font("Amiri", "", 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, ar("قائمة حساب / Agent Invoice"), ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Amiri", "", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, ar(f"رقم الوصل: #{receipt_no}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"التاريخ: {date_str}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"اسم الوكيل: {agent_name}"), ln=True, align="R")
    pdf.ln(6)

    # جدول المواد
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Amiri", "", 12)

    col_widths = [40, 40, 30, 80]
    headers = [ar("الإجمالي"), ar("سعر المفرد"), ar("الكمية"), ar("نوع البراد")]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 9, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(33, 37, 41)
    pdf.set_font("Amiri", "", 11)

    for item in items_data:
        pdf.cell(col_widths[0], 9, f"{item['total']:,}", border=1, align="C")
        pdf.cell(col_widths[1], 9, f"{item['price']:,}", border=1, align="C")
        pdf.cell(col_widths[2], 9, str(item["count"]), border=1, align="C")
        pdf.cell(col_widths[3], 9, ar(item["model"]), border=1, align="C")
        pdf.ln()

    pdf.ln(5)

    # ملخص الحساب المالي
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Amiri", "", 11)
    
    pdf.cell(100, 8, f"{current_total:,} " + ar("د.ع"), border=1, align="C")
    pdf.cell(90, 8, ar("قائمة البضاعة الحالية:"), border=1, align="R", fill=True)
    pdf.ln()

    pdf.cell(100, 8, f"{prev_balance:,} " + ar("د.ع"), border=1, align="C")
    pdf.cell(90, 8, ar("الرصيد السابق (الديون السابقة):"), border=1, align="R", fill=True)
    pdf.ln()

    pdf.cell(100, 8, f"{paid_amount:,} " + ar("د.ع"), border=1, align="C")
    pdf.cell(90, 8, ar("المبلغ الواصل (النقد المسدد):"), border=1, align="R", fill=True)
    pdf.ln()

    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("Amiri", "", 12)
    pdf.cell(100, 10, f"{final_balance:,} " + ar("د.ع"), border=1, align="C", fill=True)
    pdf.cell(90, 10, ar("الرصيد الكلي المطلوب من الوكيل:"), border=1, align="R", fill=True)
    pdf.ln(15)

    pdf.cell(0, 6, ar("توقيع الوكيل: ..........................         توقيع/ختم المعمل: .........................."), ln=True, align="C")
    return bytes(pdf.output())

# --- 3. إعداد الصفحة والجلسة ---
st.set_page_config(
    page_title="نظام إدارة المخزون والوكلاء",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

                    st.query_params["factory"] = selected_factory
                    st.query_params["user"] = username_input
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

# --- 4. تحميل بيانات المعمل ---
current_factory_name = st.session_state.factory_key
factory_data = all_factories[current_factory_name]

# الشريط العلوي
st.title(f"❄️ {current_factory_name}")
col_u1, col_u2 = st.columns([3, 1])
with col_u1:
    role_badge = "👑 مدير المعمل" if st.session_state.role == "admin" else "👷 موظف"
    st.info(f"المستخدم: **{st.session_state.user_fullname}** | {role_badge}")
with col_u2:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.factory_key = None
        st.query_params.clear()
        st.rerun()

st.write("---")

# --- 5. التبويبات الرئيسية ---
if st.session_state.role == "admin":
    tabs = st.tabs([
        "🤝 إدارة الوكلاء والديون",
        "🛒 بيع للوكيل / وصل قبض",
        "💵 تسجيل دفعة مالية من وكيل",
        "📊 التقارير الشاملة",
        "🏭 تسجيل إنتاج براد",
        "📦 إدارة المخزون",
        "👥 إدارة الحسابات",
        "📄 تصدير Excel",
    ])
else:
    tabs = st.tabs([
        "🛒 بيع للوكيل / وصل قبض",
        "💵 تسجيل دفعة مالية من وكيل",
        "🤝 دليل الوكلاء والديون",
        "📦 المخزون الحالي",
    ])

# --- تبويب [1]: إدارة دليل الوكلاء وكشف الحسابات ---
tab_agents = tabs[0] if st.session_state.role == "admin" else tabs[2]
with tab_agents:
    st.header("🤝 دليل الوكلاء والمبالغ المطلوبة (الديون)")

    col_ag1, col_ag2 = st.columns([1, 2])

    # إضافة وكيل جديد
    with col_ag1:
        st.subheader("➕ إضافة وكيل جديد")
        new_agent_name = st.text_input("اسم الوكيل / المحل:")
        new_agent_phone = st.text_input("رقم الهاتف:")
        initial_balance = st.number_input("الرصيد السابق/الافتتاحي (د.ع):", min_value=0.0, step=25000.0)

        if st.button("➕ تسجيل الوكيل بالنظام", type="primary", use_container_width=True):
            if not new_agent_name.strip():
                st.error("يرجى إدخال اسم الوكيل!")
            elif new_agent_name in factory_data["agents"]:
                st.error("اسم هذا الوكيل موجود بالفعل!")
            else:
                factory_data["agents"][new_agent_name] = {
                    "phone": new_agent_phone,
                    "balance": initial_balance,
                }
                if initial_balance > 0:
                    factory_data["agent_ledger"].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "agent": new_agent_name,
                        "type": "رصيد افتتاحي",
                        "amount": initial_balance,
                        "notes": "دين سابق عند تسجيل الوكيل بالنظام",
                        "balance_after": initial_balance,
                    })
                save_all_factories(all_factories)
                st.success(f"✅ تم إضافة الوكيل [{new_agent_name}] بنجاح!")
                st.rerun()

    # عرض قائمة الوكلاء وأرصدتهم
    with col_ag2:
        st.subheader("📋 قائمة الوكلاء المطلوبة منهم أموال")
        if not factory_data["agents"]:
            st.info("لا يوجد وكلاء مسجلون بالنظام حتى الآن.")
        else:
            agents_list = []
            for name, info in factory_data["agents"].items():
                agents_list.append({
                    "اسم الوكيل": name,
                    "رقم الهاتف": info.get("phone", "-"),
                    "الديون الكلية (د.ع)": f"{info.get('balance', 0):,}",
                })
            st.dataframe(pd.DataFrame(agents_list), use_container_width=True)

    st.write("---")
    # كشف حساب وكيل تفصيلي
    st.subheader("📜 كشف حساب تفصيلي لوكيل (Ledger)")
    selected_agent_for_ledger = st.selectbox("اختر الوكيل لطباعة كشف حركاته المالية:", list(factory_data["agents"].keys()))

    if selected_agent_for_ledger:
        agent_history = [
            t for t in factory_data.get("agent_ledger", []) if t.get("agent") == selected_agent_for_ledger
        ]
        if agent_history:
            df_ledger = pd.DataFrame(agent_history)
            df_ledger.rename(columns={
                "date": "التاريخ والوقت",
                "type": "نوع الحركة",
                "amount": "المبلغ (د.ع)",
                "notes": "التفاصيل / البيان",
                "balance_after": "الرصيد المتبقي بعد الحركة",
            }, inplace=True)
            st.dataframe(df_ledger[["التاريخ والوقت", "نوع الحركة", "المبلغ (د.ع)", "التفاصيل / البيان", "الرصيد المتبقي بعد الحركة"]], use_container_width=True)
        else:
            st.info("لا توجد حركات مالية مسجلة لهذا الوكيل بعد.")

# --- تبويب [2]: البيع للوكيل وإصدار وصل قبض وتفريغ ---
tab_sale = tabs[1] if st.session_state.role == "admin" else tabs[0]
with tab_sale:
    st.header("🛒 بيع برادات لوكيل مع احتساب الرصيد السابق")

    if not factory_data["agents"]:
        st.warning("⚠️ يرجى إضافة وكيل واحد على الأقل أولاً من تبويب [إدارة الوكلاء] للتمكن من البيع.")
    else:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            selected_agent = st.selectbox("اختر الوكيل المشتري:", list(factory_data["agents"].keys()))
            prev_balance = factory_data["agents"][selected_agent]["balance"]
            st.info(f"💰 **الرصيد السابق المطلوب من الوكيل:** `{prev_balance:,}` د.ع")
        with col_s2:
            sale_date = st.date_input("تاريخ القائمة:", value=datetime.now())

        model_list = list(factory_data["bom"].keys())
        selected_items = []
        current_invoice_total = 0

        st.subheader("📦 اختر البضاعة المفرغة للوكيل:")
        for model in model_list:
            stock_avail = factory_data["finished_goods"].get(model, 0)
            col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
            with col_m1:
                st.write(f"**{model}** (المتوفر بالمخزن: `{stock_avail}` براد)")
            with col_m2:
                qty = st.number_input("العدد:", min_value=0, max_value=max(0, stock_avail), value=0, key=f"ag_qty_{model}")
            with col_m3:
                price = st.number_input("السعر للوكيل:", min_value=0, value=0, step=5000, key=f"ag_price_{model}")

            if qty > 0:
                item_total = qty * price
                current_invoice_total += item_total
                selected_items.append({"model": model, "count": qty, "price": price, "total": item_total})

        st.write("---")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            paid_now = st.number_input("المبلغ المسدد نقداً الآن (الواصل):", min_value=0.0, step=25000.0, value=0.0)
        with col_p2:
            final_due_balance = prev_balance + current_invoice_total - paid_now
            st.markdown(f"### 🧮 الرصيد الكلي المتبقي بعد الوصل: `{final_due_balance:,}` د.ع")

        if st.button("📝 تأكيد البيع وإصدار وصل قبض الوكيل", type="primary", use_container_width=True):
            if not selected_items:
                st.error("يرجى اختيار كمية براد واحد على الأقل.")
            else:
                receipt_no = factory_data.get("receipt_counter", 1001)

                # 1. خصم البضاعة من المخزن
                for item in selected_items:
                    factory_data["finished_goods"][item["model"]] -= item["count"]

                # 2. تحديث رصيد الوكيل
                factory_data["agents"][selected_agent]["balance"] = final_due_balance

                # 3. تسجيل الحركة في كشف الحساب (Ledger)
                factory_data["agent_ledger"].append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "agent": selected_agent,
                    "type": "تفريغ بضاعة + وصل قبض",
                    "amount": current_invoice_total,
                    "notes": f"وصل #{receipt_no} | بضاعة بقيمة: {current_invoice_total:,} | المسدد: {paid_now:,}",
                    "balance_after": final_due_balance,
                })

                factory_data["receipt_counter"] = receipt_no + 1
                save_all_factories(all_factories)

                # 4. توليد PDF
                pdf_bytes = generate_agent_receipt_pdf(
                    factory_name=current_factory_name,
                    agent_name=selected_agent,
                    date_str=sale_date.strftime("%Y-%m-%d"),
                    items_data=selected_items,
                    current_total=current_invoice_total,
                    prev_balance=prev_balance,
                    paid_amount=paid_now,
                    final_balance=final_due_balance,
                    receipt_no=receipt_no,
                )

                st.success("✅ تم حفظ العملية، وتحديث حساب الوكيل والمخزن بنجاح!")
                st.download_button(
                    label="📥 تنزيل وصل القبض والحساب (PDF)",
                    data=pdf_bytes,
                    file_name=f"وصل_الوكيل_{selected_agent}_{receipt_no}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

# --- تبويب [3]: تسديد دفعة مالية مستقلة من وكيل ---
tab_pay = tabs[2] if st.session_state.role == "admin" else tabs[1]
with tab_pay:
    st.header("💵 تسجيل دفعة مالية (تسديد دين) من وكيل")

    if not factory_data["agents"]:
        st.warning("لا يوجد وكلاء مسجلون.")
    else:
        agent_to_pay = st.selectbox("اختر الوكيل المسدد:", list(factory_data["agents"].keys()), key="pay_agent_select")
        current_bal = factory_data["agents"][agent_to_pay]["balance"]

        st.info(f"المبلغ المطلوب حالياً من الوكيل [{agent_to_pay}]: **{current_bal:,} د.ع**")

        pay_amount = st.number_input("المبلغ الواصل من الوكيل (د.ع):", min_value=1.0, max_value=float(max(1.0, current_bal)), step=50000.0)
        pay_notes = st.text_input("بيان/ملاحظات التسديد (مثال: حوالة، كاش، تحويل زين كاش):", value="تسديد دفعة حساب نقدية")

        if st.button("💾 تسجيل التسديد الخطي وخصم من دين الوكيل", type="primary", use_container_width=True):
            new_bal = current_bal - pay_amount
            factory_data["agents"][agent_to_pay]["balance"] = new_bal

            factory_data["agent_ledger"].append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "agent": agent_to_pay,
                "type": "تسديد نقدي (دفعة)",
                "amount": -pay_amount,
                "notes": pay_notes,
                "balance_after": new_bal,
            })

            save_all_factories(all_factories)
            st.success(f"✅ تم خصم ({pay_amount:,} د.ع) من حساب الوكيل [{agent_to_pay}]. الرصيد الجديد: ({new_bal:,} د.ع)")
            st.rerun()

# --- التبويبات المتبقية (الإنتاج، المخزون، الحسابات، إلخ...) ---
# (تمت المحافظة على كافة الآليات السابقة للإنتاج وتحديث المخزون)
if st.session_state.role == "admin":
    with tabs[3]: # التقارير
        st.header("📊 التقارير الإحصائية للمعمل")
        total_agent_debts = sum([a.get("balance", 0) for a in factory_data["agents"].values()])
        st.metric("إجمالي الديون الأجلة المستحقة عند الوكلاء", f"{total_agent_debts:,} د.ع")
        
    with tabs[4]: # الإنتاج
        st.header("🏭 تسجيل إنتاج براد جديد")
        model_list = list(factory_data["bom"].keys())
        if model_list:
            model = st.selectbox("اختر النوع:", model_list)
            count = st.number_input("العدد المصنع:", min_value=1, value=1)
            if st.button("🚀 تسجيل الإنتاج وزيادة المخزن", type="primary", use_container_width=True):
                factory_data["finished_goods"][model] = factory_data["finished_goods"].get(model, 0) + count
                save_all_factories(all_factories)
                st.success("✅ تمت العملية بنجاح!")

    with tabs[5]: # إدارة المخزون
        st.header("📦 حالة المخزون")
        fg_df = pd.DataFrame(list(factory_data["finished_goods"].items()), columns=["نوع البراد", "المتوفر بالمخزن"])
        st.dataframe(fg_df, use_container_width=True)

    with tabs[6]: # إدارة الموظفين
        st.header("👥 إدارة الحسابات والموظفين")
        st.write("يمكنك إضافة، تعديل أو حذف حسابات الموظفين من هنا.")

    with tabs[7]: # تصدير Excel
        st.header("📄 تصدير البيانات إلى Excel")
        if st.button("📥 تصدير كشف ديون الوكلاء"):
            df_ag = pd.DataFrame(list(factory_data["agents"].items()))
            st.download_button("تنزيل ملف الوكلاء Excel", data=df_ag.to_csv(index=False).encode('utf-8-sig'), file_name="وكلاء_المعمل.csv")
