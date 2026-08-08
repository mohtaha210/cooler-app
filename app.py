import os
import requests
from flask import Flask, render_template_string, request, make_response
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# --- دالة معالجة النصوص العربية ---
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

# --- دالة التحقق من وجود الخط العربي وتنزيله تلقائياً ---
def ensure_arabic_font():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# --- دالة إنشاء ملف الـ PDF طبق الأصل ---
def generate_sanad_qabd_pdf(
    doc_no, doc_date, currency_name, agent_name, 
    amount_num, amount_text, prev_balance, new_balance, notes=""
):
    font_path = ensure_arabic_font()
    
    # استخدام الاتجاه الأفقي Landscape (L) بقياس A5 (نفس حجم ورقة السند الورقي)
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.add_font("Amiri", "", font_path)

    # عنوان السند بالمنتصف
    pdf.set_font("Amiri", "", 24)
    pdf.set_xy(10, 10)
    pdf.cell(190, 12, ar("سند قبض"), align="C")

    pdf.set_font("Amiri", "", 11)

    # --- الصف الأول: رقم المستند (يمين) | العملة (يسار) ---
    y = 26
    # رقم المستند
    pdf.set_xy(105, y)
    pdf.cell(65, 9, str(doc_no), border=1, align="C")
    pdf.cell(30, 9, ar("رقم المستند"), border=1, align="C")
    # العملة
    pdf.set_xy(10, y)
    pdf.cell(65, 9, ar(currency_name), border=1, align="C")
    pdf.cell(30, 9, ar("العملة"), border=1, align="C")

    # --- الصف الثاني: تاريخ المستند (يمين) | السيد (يسار) ---
    y_2 = y + 9
    # تاريخ المستند
    pdf.set_xy(105, y_2)
    pdf.cell(65, 9, str(doc_date), border=1, align="C")
    pdf.cell(30, 9, ar("تاريخ المستند"), border=1, align="C")
    # السيد
    pdf.set_xy(10, y_2)
    pdf.cell(65, 9, ar(agent_name), border=1, align="R")
    pdf.cell(30, 9, ar("السيد"), border=1, align="C")

    # --- الصف الثالث: المبلغ (رقماً وكتابة) ---
    y_3 = y_2 + 9
    # المبلغ كتابة يستغل باقي الصف
    pdf.set_xy(10, y_3)
    pdf.cell(95, 9, ar(amount_text), border=1, align="R")
    # المبلغ رقماً
    pdf.cell(65, 9, f"{float(amount_num):,.2f}" if amount_num else "", border=1, align="C")
    # عنوان الخانة (المبلغ)
    pdf.cell(30, 9, ar("المبلغ"), border=1, align="C")

    # --- الصف الرابع: الملاحظات ---
    y_4 = y_3 + 9
    pdf.set_xy(10, y_4)
    pdf.cell(160, 10, ar(notes), border=1, align="R")
    pdf.cell(30, 10, ar("الملاحظات"), border=1, align="C")

    # --- جدول الأرصدة (الجهة اليمنى أسفل الجدول الرئيسي) ---
    y_5 = y_4 + 11
    # الرصيد السابق
    pdf.set_xy(105, y_5)
    pdf.cell(65, 8, f"{float(prev_balance):,.2f}" if prev_balance else "", border=1, align="C")
    pdf.cell(30, 8, ar("الرصيد السابق"), border=1, align="C")

    # الرصيد بعد التسديد
    pdf.set_xy(105, y_5 + 8)
    pdf.cell(65, 8, f"{float(new_balance):,.2f}" if new_balance else "", border=1, align="C")
    pdf.cell(30, 8, ar("الرصيد بعد التسديد"), border=1, align="C")

    # إخراج ملف الـ PDF
    pdf_out = pdf.output()
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin1')
    return bytes(pdf_out)


# --- الواجهة الخاصة بالنظام (الصفحة الرئيسية) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>إدارة معمل الرافدين - طباعة سند قبض</title>
    <style>
        body { font-family: Tahoma, Arial, sans-serif; background-color: #f4f6f9; padding: 20px; }
        .card { background: #fff; max-width: 600px; margin: 0 auto; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        .form-group { margin-bottom: 12px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px; }
        input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        .row { display: flex; gap: 10px; }
        .row .form-group { flex: 1; }
        .btn { display: block; width: 100%; background-color: #28a745; color: white; border: none; padding: 12px; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 15px; }
        .btn:hover { background-color: #218838; }
    </style>
</head>
<body>
    <div class="card">
        <h2>نظام طباعة سند القبض</h2>
        <form action="/generate-receipt" method="POST">
            <div class="row">
                <div class="form-group">
                    <label>رقم المستند:</label>
                    <input type="text" name="doc_no" value="3290" required>
                </div>
                <div class="form-group">
                    <label>العملة:</label>
                    <input type="text" name="currency_name" value="دولار" required>
                </div>
            </div>

            <div class="row">
                <div class="form-group">
                    <label>تاريخ المستند:</label>
                    <input type="text" name="doc_date" value="13-07-2026" required>
                </div>
                <div class="form-group">
                    <label>السيد / الجهة:</label>
                    <input type="text" name="agent_name" value="صدام الهواش ابو كوار /معمل الرافدين" required>
                </div>
            </div>

            <div class="row">
                <div class="form-group">
                    <label>المبلغ رقماً:</label>
                    <input type="number" step="0.01" name="amount_num" value="143.00" required>
                </div>
                <div class="form-group">
                    <label>المبلغ كتابةً:</label>
                    <input type="text" name="amount_text" value="مئة و ثلاثة و اربعون دولارا أمريكا" required>
                </div>
            </div>

            <div class="form-group">
                <label>الملاحظات:</label>
                <input type="text" name="notes" placeholder="أدخل الملاحظات إن وجدت...">
            </div>

            <div class="row">
                <div class="form-group">
                    <label>الرصيد السابق:</label>
                    <input type="number" step="0.01" name="prev_balance" value="143.00">
                </div>
                <div class="form-group">
                    <label>الرصيد بعد التسديد:</label>
                    <input type="number" step="0.01" name="new_balance" placeholder="اتركه فارغاً إذا لم يوجد">
                </div>
            </div>

            <button type="submit" class="btn">تحميل / طباعة السند PDF</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate-receipt', methods=['POST'])
def generate_receipt():
    doc_no = request.form.get('doc_no', '')
    doc_date = request.form.get('doc_date', '')
    currency_name = request.form.get('currency_name', '')
    agent_name = request.form.get('agent_name', '')
    amount_num = request.form.get('amount_num', 0)
    amount_text = request.form.get('amount_text', '')
    prev_balance = request.form.get('prev_balance', 0)
    new_balance = request.form.get('new_balance', '')
    notes = request.form.get('notes', '')

    pdf_bytes = generate_sanad_qabd_pdf(
        doc_no=doc_no,
        doc_date=doc_date,
        currency_name=currency_name,
        agent_name=agent_name,
        amount_num=amount_num,
        amount_text=amount_text,
        prev_balance=prev_balance,
        new_balance=new_balance,
        notes=notes
    )

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=Sanad_{doc_no}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
