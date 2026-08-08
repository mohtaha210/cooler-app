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

# --- 1. إدارة ملف البيانات ---
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
        "agents": {},
        "agent_ledger": [],
        "receipt_counter": 1001,
    }

def load_all_factories():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_all_factories(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. دوال الطباعة والـ PDF (مضبوطة على نصف ورقة A4) ---
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
    
    # A5 بحجم أفقي (Landscape) هو العرض المطابق تماماً لـ نصف ورقة A4 (210mm x 148mm)
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # إطار أبعاد نصف الورقة A4 (عرض 210 ملم × ارتفاع 148 ملم)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_linewidth(0.5)
    pdf.rect(6, 6, 198, 136) # إطار خارجي متناسق مع حواف الصفحة

    # عنوان المستند
    pdf.set_font("Amiri", "", 22)
    pdf.set_xy(10, 10)
    pdf.cell(190, 10, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 11)

    # --- الجدول الأول (تاريخ المستند، رقم المستند، العملة) ---
    start_y = 26
    
    pdf.set_xy(12, start_y)
    pdf.cell(62, 8, ar("العملة"), border=1, align="C")
    pdf.cell(62, 8, ar("رقم المستند"), border=1, align="C")
    pdf.cell(62, 8, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(12, start_y + 8)
    pdf.cell(62, 9, ar(currency_name), border=1, align="C")
    pdf.cell(62, 9, str(doc_no), border=1, align="C")
    pdf.cell(62, 9, str(doc_date), border=1, align="C")

    # --- الجدول الثاني (السيد، المبلغ) ---
    start_y_2 = start_y + 23

    pdf.set_xy(12, start_y_2)
    pdf.cell(124, 8, ar("السيد"), border=1, align="C")
    pdf.cell(62, 8, ar("المبلغ"), border=1, align="C")

    pdf.set_xy(12, start_y_2 + 8)
    pdf.cell(124, 10, ar(agent_name), border=1, align="C")
    pdf.cell(62, 10, f"{amount_num:,.2f}", border=1, align="C")

    # تفقيط المبلغ كتابةً
    pdf.set_xy(12, start_y_2 + 18)
    pdf.cell(186, 10, ar(f"المبلغ كتابةً: {amount_text}"), border=1, align="R")

    # --- الجدول الثالث (الرصيد السابق / الرصيد بعد التسديد) ---
    start_y_3 = start_y_2 + 35

    pdf.set_xy(12, start_y_3)
    pdf.cell(93, 8, ar("الرصيد بعد التسديد"), border=1, align="C")
    pdf.cell(93, 8, ar("الرصيد السابق"), border=1, align="C")

    pdf.set_xy(12, start_y_3 + 8)
    pdf.cell(93, 10, f"{new_balance:,.2f}", border=1, align="C")
    pdf.cell(93, 10, f"{prev_balance:,.2f}", border=1, align="C")

    # ملاحظات إن وجدت
    if notes:
        pdf.set_xy(12, start_y_3 + 20)
        pdf.cell(186, 8, ar(f"الملاحظات: {notes}"), border=1, align="R")

    # التوقيعات
    pdf.set_xy(15, start_y_3 + 32)
    pdf.cell(80, 8, ar("توقيع المستلم: ...................."), align="L")
    pdf.set_xy(115, start_y_3 + 32)
    pdf.cell(80, 8, ar("توقيع المسلّم: ...................."), align="R")

    return bytes(pdf.output())

# --- 3. واجهة التطبيق بـ Streamlit ---
st.set_page_config(page_title="نظام إصدار سندات القبض", page_icon="📝", layout="wide")

all_factories = load_all_factories()

if "factory_key" not in st.session_state:
    st.session_state.factory_key = "معمل النظام"

if st.session_state.factory_key not in all_factories:
    all_factories[st.session_state.factory_key] = get_default_factory_data(st.session_state.factory_key, "admin", "123456")
    save_all_factories(all_factories)

factory_data = all_factories[st.session_state.factory_key]

st.title("📝 إصدار سند قبض (قياس نصف A4)")

col1, col2 = st.columns(2)

with col1:
    next_counter = int(factory_data.get("receipt_counter", 1001))
    doc_no = st.number_input("رقم المستند:", value=next_counter, step=1)
    doc_date = st.date_input("تاريخ المستند:", value=datetime.now())
    currency_name = st.selectbox("العملة:", ["دولار", "دينار عراقي"])
    agent_name = st.text_input("السيد (اسم الزبون / المعمل):", value="", placeholder="ادخل اسم الشخص أو المعمل...")

with col2:
    amount_num = st.number_input("المبلغ (رقماً):", value=0.0, step=10.0)
    amount_text = st.text_input("المبلغ (كتابةً):", value="", placeholder="مثال: مئة وخمسون دولار فقط...")
    prev_balance = st.number_input("الرصيد السابق:", value=0.0, step=10.0)
    
    calc_new_bal = max(0.0, prev_balance - amount_num)
    new_balance = st.number_input("الرصيد بعد التسديد (يحتسب تلقائياً):", value=float(calc_new_bal), step=10.0)

notes = st.text_input("الملاحظات (اختياري):", value="", placeholder="أي ملاحظات إضافية...")

st.write("---")

if st.button("🖨️ إنشاء وطباعة سند القبض (PDF)", type="primary", use_container_width=True):
    if not agent_name.strip():
        st.error("⚠️ يرجى إدخال اسم السيد / العميل أولاً!")
    elif amount_num <= 0:
        st.error("⚠️ يرجى إدخال مبلغ أكبر من صفر!")
    else:
        pdf_bytes = generate_sanad_qabd_pdf(
            doc_no=doc_no,
            doc_date=doc_date.strftime("%d-%m-%Y"),
            currency_name=currency_name,
            agent_name=agent_name,
            amount_num=amount_num,
            amount_text=amount_text,
            prev_balance=prev_balance,
            new_balance=new_balance,
            notes=notes
        )

        factory_data["receipt_counter"] = doc_no + 1
        save_all_factories(all_factories)

        st.success(f"✅ تم إنشاء سند القبض رقم #{doc_no} بنجاح!")
        st.download_button(
            label=f"📥 تنزيل سند القبض رقم #{doc_no} (PDF)",
            data=pdf_bytes,
            file_name=f"سند_قبض_{doc_no}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
