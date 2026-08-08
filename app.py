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
                        f_data["finished_goods"] = {model: 0 for model in f_data.get("bom", {}).keys()}
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

def generate_receipt_pdf(factory_name, customer_name, date_str, items_data, grand_total, receipt_no):
    font_path = ensure_arabic_font()
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists(font_path):
        pdf.add_font("Amiri", "", font_path)
        pdf.set_font("Amiri", "", 20)
    else:
        pdf.set_font("Arial", "B", 16)

    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, ar(factory_name), ln=True, align="C")

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, ar("وصل قبض ومبيعات / Receipt"), ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Amiri" if os.path.exists(font_path) else "Arial", "", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, ar(f"رقم الوصل: #{receipt_no}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"التاريخ: {date_str}"), ln=True, align="R")
    pdf.cell(0, 6, ar(f"اسم المشتري: {customer_name}"), ln=True, align="R")
    pdf.ln(6)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)

    col_widths = [40, 40, 30, 80]
    headers = [ar("الإجمالي"), ar("سعر البراد"), ar("الكمية"), ar("نوع البراد")]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 9, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(33, 37, 41)

    for item in items_data:
        pdf.cell(col_widths[0], 9, f"{item['total']:,}", border=1, align="C")
        pdf.cell(col_widths[1], 9, f"{item['price']:,}", border=1, align="C")
        pdf.cell(col_widths[2], 9, str(item["count"]), border=1, align="C")
        pdf.cell(col_widths[3], 9, ar(item["model"]), border=1, align="C")
        pdf.ln()

    pdf.set_fill_color(241, 245, 249)
    pdf.cell(col_widths[0], 10, f"{grand_total:,}", border=1, align="C", fill=True)
    pdf.cell(
        sum(col_widths[1:]),
        10,
        ar("المبلغ الإجمالي الكلي"),
        border=1,
        align="C",
        fill=True,
    )
    pdf.ln(20)

    pdf.cell(0, 6, ar("توقيع / ختم المعمل: .........................."), ln=True, align="L")
    return bytes(pdf.output())

# --- 3. إعداد الصفحة والجلسة ---
st.set_page_config(
    page_title="نظام إدارة المخزون والمعامل",
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

# إعادة التسجيل تلقائياً عند التحديث
if not st.session_state.authenticated and saved_factory and saved_user:
    if saved_factory in all_factories:
        factory_users = all_factories[saved_factory].get("users", {})
        if saved_user in factory_users:
            st.session_state.authenticated = True
            st.session_state.factory_key = saved_factory
            st.session_state.username = saved_user
            st.session_state.role = factory_users[saved_user]["role"]
            st.session_state.user_fullname = factory_users[saved_user]["name"]

# --- 4. شاشة تسجيل الدخول أو إنشاء حساب جديد ---
if not st.session_state.authenticated:
    st.title("❄️ نظام إدارة وتتبع المعامل والمخزون")

    login_tab, register_tab = st.tabs(["🔑 تسجيل الدخول لمعمل", "🏭 إنشاء حساب معمل جديد"])

    with login_tab:
        st.subheader("دخول إلى حساب المعمل")
        factory_list = list(all_factories.keys())
        if not factory_list:
            st.info("💡 لا توجد معامل مسجلة بالنظام حالياً. يرجى التوجه لتبويب [إنشاء حساب معمل جديد] في الأعلى.")
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

                    st.success("تم تسجيل الدخول بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")

    with register_tab:
        st.subheader("تسجيل معمل جديد بالنظام")
        new_factory_name = st.text_input("اسم المعمل الجديد:")
        admin_user = st.text_input("اسم مستخدم المدير (الذي ستدخل به):")
        admin_pass = st.text_input("كلمة مرور المدير:", type="password")

        if st.button("🚀 إنشاء المعمل وبدء الاستخدام", type="primary", use_container_width=True):
            if not new_factory_name or not admin_user or not admin_pass:
                st.error("يرجى إدخال اسم المعمل، واسم المستخدم، وكلمة المرور.")
            elif new_factory_name in all_factories:
                st.error("اسم هذا المعمل مستخدم بالفعل! اختر اسماً آخر.")
            else:
                all_factories[new_factory_name] = get_default_factory_data(new_factory_name, admin_user, admin_pass)
                save_all_factories(all_factories)
                st.success(f"✅ تم إنشاء [{new_factory_name}] بنجاح! يمكنك الآن تسجيل الدخول.")

    st.stop()

# --- 5. تحميل بيانات المعمل الحالي ---
current_factory_name = st.session_state.factory_key
if current_factory_name not in all_factories:
    st.error("حدث خطأ في تحميل بيانات المعمل.")
    st.session_state.authenticated = False
    st.query_params.clear()
    st.rerun()

factory_data = all_factories[current_factory_name]
if "finished_goods" not in factory_data:
    factory_data["finished_goods"] = {model: 0 for model in factory_data.get("bom", {}).keys()}

# --- 6. الواجهة الرئيسية وشريط المستخدم ---
st.title(f"❄️ {current_factory_name}")

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
    role_badge = "👑 مدير المعمل (صلاحيات كاملة)" if st.session_state.role == "admin" else "👷 موظف (مبيعات وإنتاج)"
    st.info(f"المستخدم الحالي: **{st.session_state.user_fullname}** | {role_badge}")
with col_u2:
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.factory_key = None
        st.query_params.clear()
        st.rerun()

st.write("---")

# --- 7. التبويبات بحسب الصلاحيات ---
if st.session_state.role == "admin":
    tabs = st.tabs([
        "📊 التقارير الشاملة",
        "🛒 بيع براد / وصل قبض",
        "🏭 تسجيل إنتاج براد",
        "📦 إدارة المخزون",
        "👥 إدارة الحسابات والموظفين",
        "📄 تصدير Excel",
        "➕ إضافة مادة جديدة",
        "🛠️ أنواع البرادات (BOM)",
    ])
else:
    tabs = st.tabs([
        "🛒 بيع براد / وصل قبض",
        "🏭 تسجيل إنتاج براد",
        "📦 المخزون الحالي",
    ])

# --- تبويب التقارير (للمدير فقط) ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.header("📊 التقارير الشاملة والإحصائيات")

        today_str = datetime.now().strftime("%Y-%m-%d")
        current_month_str = datetime.now().strftime("%Y-%m")

        sales_df = pd.DataFrame(factory_data.get("sales_history", []))
        prod_df = pd.DataFrame(factory_data.get("production_history", []))

        today_sales_count, today_revenue = 0, 0
        month_sales_count, month_revenue = 0, 0

        if not sales_df.empty:
            sales_df["date"] = pd.to_datetime(sales_df["date"])
            today_sales = sales_df[sales_df["date"].dt.strftime("%Y-%m-%d") == today_str]
            month_sales = sales_df[sales_df["date"].dt.strftime("%Y-%m") == current_month_str]

            today_sales_count = today_sales["items_count"].sum() if not today_sales.empty else 0
            today_revenue = today_sales["total"].sum() if not today_sales.empty else 0
            month_sales_count = month_sales["items_count"].sum() if not month_sales.empty else 0
            month_revenue = month_sales["total"].sum() if not month_sales.empty else 0

        today_prod_count, month_prod_count = 0, 0
        if not prod_df.empty:
            prod_df["date"] = pd.to_datetime(prod_df["date"])
            today_prod = prod_df[prod_df["date"].dt.strftime("%Y-%m-%d") == today_str]
            month_prod = prod_df[prod_df["date"].dt.strftime("%Y-%m") == current_month_str]

            today_prod_count = today_prod["count"].sum() if not today_prod.empty else 0
            month_prod_count = month_prod["count"].sum() if not month_prod.empty else 0

        st.subheader("📅 ملخص حركة اليوم والشهر")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("البرادات المباعة اليوم", f"{today_sales_count} براد")
        c2.metric("إيراد اليوم الكلي", f"{today_revenue:,} د.ع")
        c3.metric("مبيعات الشهر الكلية", f"{month_sales_count} براد")
        c4.metric("إيراد الشهر الكلي", f"{month_revenue:,} د.ع")

        st.write("---")
        c5, c6 = st.columns(2)
        c5.metric("البرادات المنتجة اليوم", f"{today_prod_count} براد")
        c6.metric("البرادات المنتجة هذا الشهر", f"{month_prod_count} براد")

        st.write("---")
        st.subheader("🧊 المخزون الجاهز من البرادات (المتبقي للبيع)")
        fg_df = pd.DataFrame(
            list(factory_data.get("finished_goods", {}).items()),
            columns=["نوع البراد", "الكمية المتاحة للبيع"],
        )
        st.dataframe(fg_df, use_container_width=True)

        st.write("---")
        st.subheader("🛠️ تقرير المواد المستعملة في الإنتاج والمتبقية في المخزن")
        
        used_materials = {item: 0.0 for item in factory_data["inventory"].keys()}
        for prod in factory_data.get("production_history", []):
            model = prod.get("model")
            p_count = prod.get("count", 0)
            if model in factory_data["bom"]:
                for m_item, m_qty in factory_data["bom"][model].items():
                    if m_item in used_materials:
                        used_materials[m_item] += m_qty * p_count

        mat_report = [
            {
                "المادة الخام": item,
                "الكمية المستعملة في الإنتاج": used_materials.get(item, 0.0),
                "الكمية المتبقية في المخزن": current_qty,
            }
            for item, current_qty in factory_data["inventory"].items()
        ]
        st.dataframe(pd.DataFrame(mat_report), use_container_width=True)

# --- تبويب بيع البرادات وإصدار وصل قبض ---
tab_receipt = tabs[1] if st.session_state.role == "admin" else tabs[0]
with tab_receipt:
    st.header("🛒 بيع البرادات الجاهزة وإصدار وصل قبض")
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        customer_name = st.text_input("اسم المشتري (الزبون):", value="")
    with col_rec2:
        purchase_date = st.date_input("تاريخ الشراء:", value=datetime.now())

    model_list = list(factory_data["bom"].keys())
    if not model_list:
        st.warning("لا توجد أنواع برادات معرفة بالنظام.")
    else:
        selected_items = []
        grand_total, total_units = 0, 0
        stock_error = False

        st.subheader("اختر البرادات المباعة:")
        for model in model_list:
            stock_available = factory_data["finished_goods"].get(model, 0)
            col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
            with col_m1:
                st.write(f"**{model}** (المتوفر بالمخزن: `{stock_available}` براد)")
            with col_m2:
                qty = st.number_input(
                    "العدد المباع:", min_value=0, max_value=max(0, stock_available), value=0, key=f"rec_qty_{model}"
                )
            with col_m3:
                price = st.number_input(
                    "سعر البراد الواحد:", min_value=0, value=0, step=5000, key=f"rec_price_{model}"
                )

            if qty > stock_available:
                stock_error = True

            if qty > 0:
                total_p = qty * price
                grand_total += total_p
                total_units += qty
                selected_items.append({"model": model, "count": qty, "price": price, "total": total_p})

        st.markdown(f"### 💰 المبلغ الإجمالي الكلي: `{grand_total:,}` د.ع")

        if st.button("🛒 تأكيد البيع وتوليد وصل القبض (PDF)", type="primary", use_container_width=True):
            if stock_error:
                st.error("❌ لا يمكنك بيع عدد أكثر من البرادات المتاحة في المخزن!")
            elif not customer_name.strip():
                st.error("يرجى إدخال اسم المشتري أولاً.")
            elif not selected_items:
                st.error("يرجى تحديد كمية براد واحد على الأقل للبيع.")
            else:
                receipt_no = factory_data.get("receipt_counter", 1001)
                
                for item in selected_items:
                    factory_data["finished_goods"][item["model"]] -= item["count"]

                pdf_bytes = generate_receipt_pdf(
                    factory_name=current_factory_name,
                    customer_name=customer_name,
                    date_str=purchase_date.strftime("%Y-%m-%d"),
                    items_data=selected_items,
                    grand_total=grand_total,
                    receipt_no=receipt_no,
                )

                factory_data["sales_history"].append({
                    "receipt_no": receipt_no,
                    "date": purchase_date.strftime("%Y-%m-%d"),
                    "customer": customer_name,
                    "items_count": total_units,
                    "total": grand_total,
                })

                factory_data["receipt_counter"] = receipt_no + 1
                save_all_factories(all_factories)

                st.success("✅ تم تسجيل عملية البيع وخصم البرادات المباعة بنجاح!")
                st.download_button(
                    label="📥 تنزيل وصل القبض PDF",
                    data=pdf_bytes,
                    file_name=f"وصل_قبض_{receipt_no}_{customer_name}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

# --- تبويب تسجيل الإنتاج ---
tab_prod = tabs[2] if st.session_state.role == "admin" else tabs[1]
with tab_prod:
    st.header("🏭 تسجيل عملية إنتاج براد جديد")
    model_list = list(factory_data["bom"].keys())
    if not model_list:
        st.warning("لا توجد أنواع برادات معروفة في النظام حالياً.")
    else:
        model = st.selectbox("اختر نوع البراد المصنوع:", model_list)
        count = st.number_input("عدد البرادات المصنعة:", min_value=1, value=1, step=1)

        if st.button("🚀 خصم المواد الأولية وزيادة البرادات الجاهزة", type="primary", use_container_width=True):
            required_bom = factory_data["bom"][model]
            missing_items = []

            for item, qty in required_bom.items():
                needed = qty * count
                available = factory_data["inventory"].get(item, 0)
                if available < needed:
                    missing_items.append(f"- **{item}**: المطلوب ({needed})، المتوفر بالمخزن ({available})")

            if missing_items:
                st.error("❌ لا يوجد مخزون مواد أولية كافٍ لإتمام التصنيع!")
                for m in missing_items:
                    st.write(m)
            else:
                for item, qty in required_bom.items():
                    factory_data["inventory"][item] -= qty * count

                if model not in factory_data["finished_goods"]:
                    factory_data["finished_goods"][model] = 0
                factory_data["finished_goods"][model] += count

                factory_data["production_history"].append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "model": model,
                    "count": count,
                })

                save_all_factories(all_factories)
                st.success(f"✅ تم إنتاج ({count}) من [{model}] وإضافتها إلى مخزون البرادات الجاهزة للبيع!")
                st.rerun()

# --- تبويب المخزون ---
tab_inv = tabs[3] if st.session_state.role == "admin" else tabs[2]
with tab_inv:
    if st.session_state.role == "admin":
        st.header("📦 حالة المخزون (المواد والبرادات الجاهزة)")
        
        st.subheader("🧊 البرادات الجاهزة بالمخزن")
        fg_df = pd.DataFrame(
            list(factory_data["finished_goods"].items()),
            columns=["نوع البراد", "العدد المتوفر للبيع"],
        )
        st.dataframe(fg_df, use_container_width=True)

        st.subheader("🧱 المواد الأولية الخام")
        df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية المتوفرة"],
        )
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 حفظ التعديلات على مواد المخزن", use_container_width=True):
                new_inv = {}
                for _, row in edited_df.iterrows():
                    if row["اسم المادة الخام"]:
                        new_inv[row["اسم المادة الخام"]] = float(row["الكمية المتوفرة"])
                factory_data["inventory"] = new_inv
                save_all_factories(all_factories)
                st.success("✅ تم تحديث بيانات المخزون وحفظها بنجاح!")
                st.rerun()

        with col_btn2:
            with st.popover("⚠️ تصفير جميع المواد"):
                st.warning("هل أنت متأكد؟ سيتم جعل جميع المواد الأولية (0)!")
                if st.button("نعم، أؤكد تصفير كافة المواد", type="primary", use_container_width=True):
                    for item in factory_data["inventory"]:
                        factory_data["inventory"][item] = 0.0
                    save_all_factories(all_factories)
                    st.success("⚠️ تم تصفير كافة الكميات!")
                    st.rerun()
    else:
        st.header("📦 المخزون الحالي")
        st.subheader("🧊 البرادات الجاهزة للبيع")
        fg_df = pd.DataFrame(
            list(factory_data["finished_goods"].items()),
            columns=["نوع البراد", "العدد المتوفر للبيع"],
        )
        st.dataframe(fg_df, use_container_width=True)

        st.subheader("🧱 كميات المواد الخام المتوفرة")
        df = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية المتوفرة"],
        )
        st.dataframe(df, use_container_width=True)

# --- تبويبات الإدارة المتقدمة (للمدير فقط) ---
if st.session_state.role == "admin":
    with tabs[4]:
        st.header("👥 إدارة الحسابات والموظفين")

        # 1. إضافة حساب جديد
        st.subheader("➕ إضافة حساب موظف/مدير جديد")
        col_u_a1, col_u_a2 = st.columns(2)
        with col_u_a1:
            new_emp_user = st.text_input("اسم المستخدم الجديد (Username):")
            new_emp_name = st.text_input("اسم الموظف الثلاثي:")
        with col_u_a2:
            new_emp_pass = st.text_input("كلمة المرور:", type="password")
            new_emp_role = st.selectbox(
                "الصلاحية:",
                ["staff", "admin"],
                format_func=lambda x: "👷 موظف" if x == "staff" else "👑 مدير",
            )

        if st.button("➕ إنشاء حساب جديد", type="primary", use_container_width=True):
            if not new_emp_user or not new_emp_pass or not new_emp_name:
                st.error("يرجى ملء كافة البيانات.")
            elif new_emp_user in factory_data["users"]:
                st.error("اسم المستخدم هذا موجود بالفعل!")
            else:
                factory_data["users"][new_emp_user] = {
                    "password": new_emp_pass,
                    "role": new_emp_role,
                    "name": new_emp_name,
                }
                save_all_factories(all_factories)
                st.success(f"✅ تم إضافة الحساب للموظف [{new_emp_name}] بنجاح!")
                st.rerun()

        st.write("---")

        # 2. تعديل بيانات حساب موجود
        st.subheader("✏️ تعديل بيانات حساب (اسم المستخدم / كلمة السر)")
        user_list = list(factory_data["users"].keys())
        selected_user_to_edit = st.selectbox("اختر الحساب المراد تعديله:", user_list)

        if selected_user_to_edit:
            u_data = factory_data["users"][selected_user_to_edit]
            
            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                edit_new_username = st.text_input("اسم المستخدم الجديد:", value=selected_user_to_edit, key="edit_uname")
                edit_fullname = st.text_input("الاسم الكامل:", value=u_data.get("name", ""), key="edit_fname")
            with col_ed2:
                edit_password = st.text_input("كلمة المرور الجديدة:", value=u_data.get("password", ""), key="edit_pass")
                edit_role = st.selectbox(
                    "الصلاحية:",
                    ["staff", "admin"],
                    index=0 if u_data.get("role") == "staff" else 1,
                    format_func=lambda x: "👷 موظف" if x == "staff" else "👑 مدير",
                    key="edit_role"
                )

            if st.button("💾 حفظ التعديلات على الحساب", use_container_width=True):
                if not edit_new_username or not edit_password or not edit_fullname:
                    st.error("لا يمكن إبقاء الحقول فارغة!")
                elif edit_new_username != selected_user_to_edit and edit_new_username in factory_data["users"]:
                    st.error("اسم المستخدم الجديد مأخوذ بالفعل!")
                else:
                    factory_data["users"][edit_new_username] = {
                        "password": edit_password,
                        "role": edit_role,
                        "name": edit_fullname
                    }
                    if edit_new_username != selected_user_to_edit:
                        del factory_data["users"][selected_user_to_edit]
                        if st.session_state.username == selected_user_to_edit:
                            st.session_state.username = edit_new_username
                            st.query_params["user"] = edit_new_username
                    
                    save_all_factories(all_factories)
                    st.success("✅ تم تعديل بيانات الحساب بنجاح!")
                    st.rerun()

        st.write("---")

        # 3. إزالة الحسابات غير المرغوب فيها
        st.subheader("🗑️ إزالة الحسابات غير المرغوب فيها")
        user_to_delete = st.selectbox("اختر الحساب المراد حذفه نهائياً:", user_list, key="del_user_select")
        
        if user_to_delete:
            if user_to_delete == st.session_state.username:
                st.warning("⚠️ لا يمكنك حذف الحساب الذي تسجل الدخول به حالياً!")
            else:
                with st.popover(f"❌ تأكيد حذف الحساب [{user_to_delete}]"):
                    st.write(f"هل أنت متأكد من حذف الحساب ({user_to_delete}) نهائياً؟")
                    if st.button("نعم، احذف الحساب الآن", type="primary", use_container_width=True):
                        del factory_data["users"][user_to_delete]
                        save_all_factories(all_factories)
                        st.success(f"✅ تم حذف الحساب [{user_to_delete}] بنجاح!")
                        st.rerun()

        st.write("---")

        # 4. حذف معمل/مخزن بالكامل
        st.subheader("🏚️ إدارة المعامل والمخازن المسجلة بالنظام")
        st.write("يمكنك حذف أي معمل أو مخزن زائد بالنظام لتنظيف القائمة في شاشة تسجيل الدخول.")
        
        all_factories_list = list(all_factories.keys())
        factory_to_delete = st.selectbox("اختر المعمل/المخزن المراد حذفه نهائياً:", all_factories_list, key="del_factory_select")

        with st.popover(f"🚨 حذف المعمل [{factory_to_delete}] بالكامل"):
            st.error(f"تحذير: هذا الخيار سيحذف المعمل ({factory_to_delete}) وجميع بياناته ومستخدميه ولا يمكن استرجاعها!")
            if st.button("نعم، احذف هذا المعمل نهائياً", type="primary", use_container_width=True):
                del all_factories[factory_to_delete]
                save_all_factories(all_factories)
                if factory_to_delete == current_factory_name:
                    st.session_state.authenticated = False
                    st.session_state.factory_key = None
                    st.query_params.clear()
                st.success(f"✅ تم حذف المعمل [{factory_to_delete}] بنجاح!")
                st.rerun()

    with tabs[5]:
        st.header("تصدير تقرير جرد المخزون والبرادات إلى Excel")
        df_export = pd.DataFrame(
            list(factory_data["inventory"].items()),
            columns=["اسم المادة الخام", "الكمية المتوفرة حالياً"],
        )
        df_fg_export = pd.DataFrame(
            list(factory_data["finished_goods"].items()),
            columns=["نوع البراد الجاهز", "العدد المتوفر"],
        )

        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False, sheet_name="جرد_المواد_الخام")
                df_fg_export.to_excel(writer, index=False, sheet_name="البرادات_الجاهزة")

            st.download_button(
                label="📥 تنزيل تقرير المخزون الشامل (Excel)",
                data=buffer.getvalue(),
                file_name=f"جرد_{current_factory_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error("يرجى التأكد من تثبيت مكتبة openpyxl لتصدير Excel.")

    with tabs[6]:
        st.header("إضافة مادة خام جديدة كلياً")
        new_item_name = st.text_input("اسم المادة الخام الجديدة:")
        initial_qty = st.number_input("الكمية الأولية:", min_value=0.0, value=0.0)

        if st.button("➕ إضافة المادة للمخزن", type="primary", use_container_width=True):
            if new_item_name:
                if new_item_name in factory_data["inventory"]:
                    st.warning("هذه المادة موجودة بالفعل بالمخزن!")
                else:
                    factory_data["inventory"][new_item_name] = initial_qty
                    save_all_factories(all_factories)
                    st.success(f"✅ تمت إضافة المادة [{new_item_name}] بنجاح!")
                    st.rerun()

    with tabs[7]:
        st.header("تعريف نموذج براد جديد وقائمة مكوناته")
        new_model_name = st.text_input("اسم نموذج البراد الجديد:")
        selected_ingredients = {}

        for item in factory_data["inventory"].keys():
            use_item = st.checkbox(f"يدخل فيه: {item}", key=f"chk_{item}")
            if use_item:
                qty_needed = st.number_input(
                    f"الكمية المطلوبة من [{item}]:",
                    min_value=0.1,
                    value=1.0,
                    key=f"qty_{item}",
                )
                selected_ingredients[item] = qty_needed

        if st.button("🛠️ حفظ النموذج الجديد", use_container_width=True):
            if new_model_name and selected_ingredients:
                factory_data["bom"][new_model_name] = selected_ingredients
                if new_model_name not in factory_data["finished_goods"]:
                    factory_data["finished_goods"][new_model_name] = 0
                save_all_factories(all_factories)
                st.success(f"✅ تم تعريف النموذج [{new_model_name}] بنجاح!")
                st.rerun()
