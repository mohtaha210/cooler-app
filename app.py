import os
import requests
import streamlit as st
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- دالة معالجة النصوص العربية ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

# --- دالة تنزيل الخط العربي ---
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# --- دالة إنشاء ملف الـ PDF ---
def generate_sanad_qabd_pdf(
    doc_no, doc_date, currency_name, agent_name, 
    amount_num, amount_text, prev_balance, new_balance, notes=""
):
    font_path = ensure_arabic_font()
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # عنوان السند
    pdf.set_font("Amiri", "", 24)
    pdf.set_xy(10, 10)
    pdf.cell(190, 12, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 11)

    # الصف الأول
    y = 26
    pdf.set_xy(105, y)
    pdf.cell(65, 9, str(doc_no), border=1, align="C")
    pdf.cell(30, 9, ar("رقم المستند"), border=1, align="C")
    
    pdf.set_xy(10, y)
    pdf.cell(65, 9, ar(currency_name), border=1, align="C")
    pdf.cell(30, 9, ar("العملة"), border=1, align="C")

    # الصف الثاني
    y_2 = y + 9
    pdf.set_xy(105, y_2)
    pdf.cell(65, 9, str(doc_date), border=1, align="C")
    pdf.cell(30, 9, ar("تاريخ المستند"), border=1, align="C")
    
    pdf.set_xy(10, y_2)
    pdf.cell(65, 9, ar(agent_name), border=1, align="R")
    pdf.cell(30, 9, ar("السيد"), border=1, align="C")

    # الصف الثالث
    y_3 = y_2 + 9
    pdf.set_xy(10, y_3)
    pdf.cell(95, 9, ar(amount_text), border=1, align="R")
    
    amt_str = f"{float(amount_num):,.2f}" if amount_num else ""
    pdf.cell(65, 9, amt_str, border=1, align="C")
    pdf.cell(30, 9, ar("المبلغ"), border=1, align="C")

    # الصف الرابع
    y_4 = y_3 + 9
    pdf.set_xy(10, y_4)
    pdf.cell(160, 10, ar(notes), border=1, align="R")
    pdf.cell(30, 10, ar("الملاحظات"), border=1, align="C")

    # جدول الأرصدة
    y_5 = y_4 + 11
    p_bal_str = f"{float(prev_balance):,.2f}" if prev_balance else ""
    pdf.set_xy(105, y_5)
    pdf.cell(65, 8, p_bal_str, border=1, align="C")
    pdf.cell(30, 8, ar("الرصيد السابق"), border=1, align="C")

    n_bal_str = f"{float(new_balance):,.2f}" if new_balance else ""
    pdf.set_xy(105, y_5 + 8)
    pdf.cell(65, 8, n_bal_str, border=1, align="C")
    pdf.cell(30, 8, ar("الرصيد بعد التسديد"), border=1, align="C")

    pdf_out = pdf.output()
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin1')
    return bytes(pdf_out)


# --- واجهة تطبيق Streamlit ---
st.set_page_config(page_title="سند قبض - معمل الرافدين", layout="centered")

st.markdown("<h2 style='text-align: center;'>نظام طباعة سند القبض</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    doc_no = st.text_input("رقم المستند", value="3290")
    doc_date = st.text_input("تاريخ المستند", value="13-07-2026")
    amount_num = st.number_input("المبلغ رقماً", value=143.00, step=1.0)
    prev_balance = st.number_input("الرصيد السابق", value=143.00, step=1.0)

with col2:
    currency_name = st.text_input("العملة", value="دولار")
    agent_name = st.text_input("السيد / الجهة", value="صدام الهواش ابو كوار /معمل الرافدين")
    amount_text = st.text_input("المبلغ كتابةً", value="مئة و ثلاثة و اربعون دولارا أمريكا")
    new_balance = st.number_input("الرصيد بعد التسديد", value=0.0, step=1.0)

notes = st.text_input("الملاحظات", value="")

if st.button("إنشاء سند القبض PDF", type="primary"):
    pdf_bytes = generate_sanad_qabd_pdf(
        doc_no=doc_no,
        doc_date=doc_date,
        currency_name=currency_name,
        agent_name=agent_name,
        amount_num=amount_num,
        amount_text=amount_text,
        prev_balance=prev_balance,
        new_balance=new_balance if new_balance != 0 else "",
        notes=notes
    )
    
    st.download_button(
        label="📥 تحميل السند (PDF)",
        data=pdf_bytes,
        file_name=f"Sanad_{doc_no}.pdf",
        mime="application/pdf"
    )
