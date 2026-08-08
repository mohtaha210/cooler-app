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

DATA_FILE = "factory_data.json"

# --- 1. إدارة ملف البيانات والتخزين الدائم ---
def get_default_data():
  return {
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


def load_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "sales_history" not in data:
          data["sales_history"] = []
        if "production_history" not in data:
          data["production_history"] = []
        return data
    except Exception:
      return get_default_data()
  else:
    data = get_default_data()
    save_data(data)
    return data


def save_data(data=None):
  if data is None:
    data = {
        "inventory": st.session_state.inventory,
        "bom": st.session_state.bom,
        "receipt_counter": st.session_state.receipt_counter,
        "sales_history": st.session_state.sales_history,
        "production_history": st.session_state.production_history,
    }
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# --- 2. دوال معالجة النصوص والـ PDF ---
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


def generate_receipt_pdf(
    customer_name, date_str, items_data, grand_total, receipt_no
):
  font_path = ensure_arabic_font()
  pdf = FPDF()
  pdf.add_page()
  pdf.add_font("Amiri", "", font_path)

  pdf.set_font("Amiri", "", 20)
  pdf.set_text_color(30, 41, 59)
  pdf.cell(0, 10, ar("معمل برادات الرافدين"), ln=True, align="C")

  pdf.set_font("Amiri", "", 12)
  pdf.set_text_color(100, 116, 139)
  pdf.cell(0, 6, ar("وصل قبض ومبيعات / Receipt"), ln=True, align="C")
  pdf.ln(8)

  pdf.set_font("Amiri", "", 11)
  pdf.set_text_color(51, 65, 85)
  pdf.cell(0, 6, ar(f"رقم الوصل: #{receipt_no}"), ln=True, align="R")
  pdf.cell(0, 6, ar(f"التاريخ: {date_str}"), ln=True, align="R")
  pdf.cell(0, 6, ar(f"اسم المشتري: {customer_name}"), ln=True, align="R")
  pdf.ln(6)

  pdf.set_fill_color(30, 41, 59)
  pdf.set_text_color(255, 255, 255)
  pdf.set_font("Amiri", "", 12)

  col_widths = [40, 40, 30, 80]
  headers = [ar("الإجمالي"), ar("سعر البراد"), ar("الكمية"), ar("نوع البراد")]
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

  pdf.cell(
      0,
      6,
      ar("توقيع / ختم المعمل: .........................."),
      ln=True,
      align="L",
  )
  return bytes(pdf.output())


# --- 3. ضبط الصفحة وتحميل البيانات ---
st.set_page_config(
    page_title="نظام معمل برادات الرافدين",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "inventory" not in st.session_state:
  saved_data = load_data()
  st.session_state.inventory = saved_data["inventory"]
  st.session_state.bom = saved_data["bom"]
  st.session_state.receipt_counter = saved_data.get("receipt_counter", 1001)
  st.session_state.sales_history = saved_data.get("sales_history", [])
  st.session_state.production_history = saved_data.get(
      "production_history", []
  )

# --- 4. نظام تسجيل الدخول والصلاحيات ---
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False
  st.session_state.role = None
  st.session_state.user_fullname = ""

USERS = {
    "admin": {
        "password": "123",
        "role": "admin",
        "name": "المدير العام",
    },
    "staff": {
        "password": "123",
        "role": "staff",
        "name": "موظف المبيعات والإنتاج",
    },
}

if not st.session_state.authenticated:
  st.title("🔒 تسجيل الدخول - معمل برادات الرافدين")
  username = st.text_input("اسم المستخدم")
  password = st.text_input("كلمة المرور", type="password")

  if st.button("تسجيل الدخول", type="primary", use_container_width=True):
    if username in USERS and USERS[username]["password"] == password:
      st.session_state.authenticated = True
      st.session_state.role = USERS[username]["role"]
      st.session_state.user_fullname = USERS[username]["name"]
      st.rerun()
    else:
      st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
  st.stop()

# --- 5. الواجهة الرئيسية وشريط المستخدم ---
st.title("❄️ معمل برادات الرافدين - نظام إدارة وتتبع المخزون والمبيعات")

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
  role_badge = (
      "👑 مدير النظام (صلاحيات كاملة)"
      if st.session_state.role == "admin"
      else "👷 موظف (مبيعات وإنتاج فقط)"
  )
  st.info(f"مرحباً بك: **{st.session_state.user_fullname}** | {role_badge}")
with col_u2:
  if st.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.role = None
    st.rerun()

st.write("---")

# --- 6. التبويبات بحسب الصلاحيات ---
if st.session_state.role == "admin":
  tabs = st.tabs([
      "📊 التقارير الشاملة",
      "🧾 إصدار وصل قبض (PDF)",
      "🏭 تسجيل إنتاج",
      "📦 إدارة وتعديل المخزون",
      "📄 تصدير Excel",
      "➕ إضافة مادة جديدة",
      "🛠️ أنواع البرادات (BOM)",
  ])
else:
  tabs = st.tabs([
      "🧾 إصدار وصل قبض (PDF)",
      "🏭 تسجيل إنتاج",
      "📦 المخزون الحالي",
  ])

# --- تبويب التقارير (للمدير فقط) ---
if st.session_state.role == "admin":
  with tabs[0]:
    st.header("📊 التقارير الشاملة والإحصائيات")

    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month_str = datetime.now().strftime("%Y-%m")

    # حساب مبيعات اليوم والشهر
    sales_df = pd.DataFrame(st.session_state.sales_history)
    prod_df = pd.DataFrame(st.session_state.production_history)

    today_sales_count = 0
    today_revenue = 0
    month_sales_count = 0
    month_revenue = 0

    if not sales_df.empty:
      sales_df["date"] = pd.to_datetime(sales_df["date"])
      today_sales = sales_df[sales_df["date"].dt.strftime("%Y-%m-%d") == today_str]
      month_sales = sales_df[
          sales_df["date"].dt.strftime("%Y-%m") == current_month_str
      ]

      today_sales_count = today_sales["items_count"].sum() if not today_sales.empty else 0
      today_revenue = today_sales["total"].sum() if not today_sales.empty else 0

      month_sales_count = month_sales["items_count"].sum() if not month_sales.empty else 0
      month_revenue = month_sales["total"].sum() if not month_sales.empty else 0

    # حساب إنتاج اليوم والشهر
    today_prod_count = 0
    month_prod_count = 0

    if not prod_df.empty:
      prod_df["date"] = pd.to_datetime(prod_df["date"])
      today_prod = prod_df[prod_df["date"].dt.strftime("%Y-%m-%d") == today_str]
      month_prod = prod_df[
          prod_df["date"].dt.strftime("%Y-%m") == current_month_str
      ]

      today_prod_count = today_prod["count"].sum() if not today_prod.empty else 0
      month_prod_count = month_prod["count"].sum() if not month_prod.empty else 0

    # عرض كروت الإحصائيات
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
    st.subheader("📦 حالة كافة المواد المتوفرة في المخزن")
    inv_df = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية الحالية"],
    )
    st.dataframe(inv_df, use_container_width=True)

# --- تبويب إصدار وصل قبض ---
tab_receipt = tabs[1] if st.session_state.role == "admin" else tabs[0]
with tab_receipt:
  st.header("🧾 إصدار وصل قبض وطباعة الفاتورة")
  col_rec1, col_rec2 = st.columns(2)
  with col_rec1:
    customer_name = st.text_input("اسم المشتري (الزبون):", value="")
  with col_rec2:
    purchase_date = st.date_input("تاريخ الشراء:", value=datetime.now())

  model_list = list(st.session_state.bom.keys())
  if not model_list:
    st.warning("لا توجد أنواع برادات معرفة بالنظام.")
  else:
    selected_items = []
    grand_total = 0
    total_units = 0

    for model in model_list:
      col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
      with col_m1:
        st.write(f"**{model}**")
      with col_m2:
        qty = st.number_input(
            "العدد المشتري:", min_value=0, value=0, key=f"rec_qty_{model}"
        )
      with col_m3:
        price = st.number_input(
            "سعر البراد الواحد:",
            min_value=0,
            value=0,
            step=5000,
            key=f"rec_price_{model}",
        )

      if qty > 0:
        total_p = qty * price
        grand_total += total_p
        total_units += qty
        selected_items.append({
            "model": model,
            "count": qty,
            "price": price,
            "total": total_p,
        })

    st.markdown(f"### 💰 المبلغ الإجمالي الكلي: `{grand_total:,}`")

    if st.button(
        "📄 توليد وصل القبض (PDF)", type="primary", use_container_width=True
    ):
      if not customer_name.strip():
        st.error("يرجى إدخال اسم المشتري أولاً.")
      elif not selected_items:
        st.error("يرجى تحديد كمية براد واحد على الأقل.")
      else:
        pdf_bytes = generate_receipt_pdf(
            customer_name=customer_name,
            date_str=purchase_date.strftime("%Y-%m-%d"),
            items_data=selected_items,
            grand_total=grand_total,
            receipt_no=st.session_state.receipt_counter,
        )

        # تسجيل السجل في التاريخ
        st.session_state.sales_history.append({
            "receipt_no": st.session_state.receipt_counter,
            "date": purchase_date.strftime("%Y-%m-%d"),
            "customer": customer_name,
            "items_count": total_units,
            "total": grand_total,
        })

        st.session_state.receipt_counter += 1
        save_data()

        st.success("✅ تم تجهيز الوصل وتسجيل المبيعات في التقرير بنجاح!")
        st.download_button(
            label="📥 تنزيل وصل القبض PDF",
            data=pdf_bytes,
            file_name=(
                f"وصل_قبض_{st.session_state.receipt_counter - 1}_{customer_name}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

# --- تبويب تسجيل الإنتاج ---
tab_prod = tabs[2] if st.session_state.role == "admin" else tabs[1]
with tab_prod:
  st.header("تسجيل عملية إنتاج براد")
  model_list = list(st.session_state.bom.keys())
  if not model_list:
    st.warning("لا توجد أنواع برادات معروفة في النظام حالياً.")
  else:
    model = st.selectbox("اختر نوع البراد المصنوع:", model_list)
    count = st.number_input(
        "عدد البرادات المصنعة:", min_value=1, value=1, step=1
    )

    if st.button(
        "🚀 خصم المواد وتأكيد الإنتاج",
        type="primary",
        use_container_width=True,
    ):
      required_bom = st.session_state.bom[model]
      missing_items = []

      for item, qty in required_bom.items():
        needed = qty * count
        available = st.session_state.inventory.get(item, 0)
        if available < needed:
          missing_items.append(
              f"- **{item}**: المطلوب ({needed})، المتوفر ({available})"
          )

      if missing_items:
        st.error("❌ لا يوجد مخزون كافٍ لإتمام العملية!")
        for m in missing_items:
          st.write(m)
      else:
        for item, qty in required_bom.items():
          st.session_state.inventory[item] -= qty * count

        # تسجيل الإنتاج في السجل
        st.session_state.production_history.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "model": model,
            "count": count,
        })

        save_data()
        st.success(f"✅ تم تسجيل إنتاج ({count}) من [{model}] بنجاح!")
        st.rerun()

# --- تبويب المخزون ---
tab_inv = tabs[3] if st.session_state.role == "admin" else tabs[2]
with tab_inv:
  if st.session_state.role == "admin":
    st.header("عرض وتعديل كميات المخزون الحالية")
    df = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة"],
    )
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
      if st.button("💾 حفظ التعديلات على الجدول", use_container_width=True):
        new_inv = {}
        for _, row in edited_df.iterrows():
          if row["اسم المادة الخام"]:
            new_inv[row["اسم المادة الخام"]] = float(row["الكمية المتوفرة"])
        st.session_state.inventory = new_inv
        save_data()
        st.success("✅ تم تحديث بيانات المخزون وحفظها بنجاح!")
        st.rerun()

    with col_btn2:
      with st.popover("⚠️ تصفير جميع المواد في المخزن"):
        st.warning("هل أنت متأكد؟ سيتم جعل جميع الكميات (0)!")
        if st.button(
            "نعم، أؤكد تصفير كافة الكميات",
            type="primary",
            use_container_width=True,
        ):
          for item in st.session_state.inventory:
            st.session_state.inventory[item] = 0.0
          save_data()
          st.success("⚠️ تم تصفير كافة الكميات!")
          st.rerun()
  else:
    st.header("📦 كميات المواد المتوفرة حالياً بالمخزن")
    df = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة"],
    )
    st.dataframe(df, use_container_width=True)

# --- تبويبات الإدارة المتقدمة (للمدير فقط) ---
if st.session_state.role == "admin":
  # تصدير Excel
  with tabs[4]:
    st.header("تصدير تقرير جرد المخزون إلى Excel")
    df_export = pd.DataFrame(
        list(st.session_state.inventory.items()),
        columns=["اسم المادة الخام", "الكمية المتوفرة حالياً"],
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
      df_export.to_excel(writer, index=False, sheet_name="جرد_المخزون")

    st.download_button(
        label="📥 تنزيل تقرير المخزون (Excel)",
        data=buffer.getvalue(),
        file_name="جرد_مخزون_المعمل.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.dataframe(df_export, use_container_width=True)

  # إضافة مادة
  with tabs[5]:
    st.header("إضافة مادة خام جديدة كلياً")
    new_item_name = st.text_input("اسم المادة الخام الجديدة:")
    initial_qty = st.number_input("الكمية الأولية:", min_value=0.0, value=0.0)

    if st.button(
        "➕ إضافة المادة للمخزن", type="primary", use_container_width=True
    ):
      if new_item_name:
        if new_item_name in st.session_state.inventory:
          st.warning("هذه المادة موجودة بالفعل بالمخزن!")
        else:
          st.session_state.inventory[new_item_name] = initial_qty
          save_data()
          st.success(f"✅ تمت إضافة المادة [{new_item_name}] بنجاح!")
          st.rerun()
      else:
        st.error("يرجى إدخال اسم المادة.")

  # مكونات البرادات
  with tabs[6]:
    st.header("تعريف نموذج براد جديد وقائمة مكوناته")
    new_model_name = st.text_input("اسم نموذج البراد الجديد:")
    selected_ingredients = {}

    for item in st.session_state.inventory.keys():
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
        st.session_state.bom[new_model_name] = selected_ingredients
        save_data()
        st.success(f"✅ تم تعريف النموذج [{new_model_name}] بنجاح!")
        st.rerun()
      else:
        st.error("يرجى تحديد اسم النموذج واختيار مادة واحدة على الأقل!")
