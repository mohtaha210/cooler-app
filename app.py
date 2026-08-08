from flask import Flask, render_template_string, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'cooler_factory_secret_key'

# --- إعداد قاعدة البيانات SQLite ---
def init_db():
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    
    # 1. جدول المواد الخام (28 مادة)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity REAL DEFAULT 0,
            unit_cost REAL DEFAULT 0
        )
    ''')
    
    # 2. جدول مخزن البرادات الجاهزة (المنتج التام)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finished_coolers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            cost_price REAL DEFAULT 0,
            selling_price REAL DEFAULT 0
        )
    ''')
    
    # 3. جدول الوكلاء والزبائن والديون
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            balance REAL DEFAULT 0 -- موجب: عليه دين / سالب: له رصيد
        )
    ''')
    
    # 4. جدول المعاملات والوصولات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            type TEXT, -- 'INVOICE' (فاتورة بيع) أو 'PAYMENT' (سند قبض)
            amount REAL,
            details TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- القوالب الواجهات (HTML Direct Strings) ---
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام إدارة معمل البرادات</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar { background-color: #0d6efd; }
        .card { border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        @media print {
            .no-print { display: none !important; }
            .print-only { display: block !important; }
            body { background-color: #fff; }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4 no-print">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#">🧊 معمل برادات الماء</a>
            <div class="navbar-nav">
                <a class="nav-link text-white" href="{{ url_for('index') }}">الرئيسية</a>
                <a class="nav-link text-white" href="{{ url_for('clients') }}">الوكلاء والديون</a>
                <a class="nav-link text-white" href="{{ url_for('materials') }}">المواد الخام (28 مادة)</a>
                <a class="nav-link text-white" href="{{ url_for('inventory') }}">مخزن البرادات</a>
            </div>
        </div>
    </nav>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# --- المسارات (Routes) ---

@app.route('/')
def index():
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM raw_materials")
    mat_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(stock) FROM finished_coolers")
    coolers_count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(balance) FROM clients WHERE balance > 0")
    total_debts = cursor.fetchone()[0] or 0
    conn.close()
    
    html = BASE_TEMPLATE + '''
    {% extends "base" %}
    {% block content %}
    <h3 class="mb-4 text-center">لوحة تحكم معمل برادات الماء</h3>
    <div class="row text-center g-3">
        <div class="col-md-4">
            <div class="card bg-primary text-white p-3">
                <h5>إجمالي البرادات بالإنتاج/المخزن</h5>
                <h2>{{ coolers_count }} براد</h2>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-warning text-dark p-3">
                <h5>إجمالي ديون الوكلاء (لصالحنا)</h5>
                <h2>{{ total_debts }} د.ع</h2>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-success text-white p-3">
                <h5>المواد الخام المسجلة</h5>
                <h2>{{ mat_count }} مادة</h2>
            </div>
        </div>
    </div>
    {% endblock %}
    '''
    return render_template_string(html, mat_count=mat_count, coolers_count=coolers_count, total_debts=total_debts)

# 1. صفحة الوكلاء والديون
@app.route('/clients', methods=['GET', 'POST'])
def clients():
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        balance = request.form.get('balance', 0)
        cursor.execute("INSERT INTO clients (name, phone, balance) VALUES (?, ?, ?)", (name, phone, balance))
        conn.commit()
        return redirect(url_for('clients'))
        
    cursor.execute("SELECT * FROM clients")
    clients_list = cursor.fetchall()
    conn.close()
    
    html = BASE_TEMPLATE + '''
    <h3>إدارة حسابات الوكلاء والديون</h3>
    <div class="card p-3 mb-4 no-print">
        <h5>إضافة وكيل جديد / دين سابق</h5>
        <form method="POST" class="row g-2">
            <div class="col-md-4"><input type="text" name="name" class="form-control" placeholder="اسم الوكيل/الزبون" required></div>
            <div class="col-md-4"><input type="text" name="phone" class="form-control" placeholder="رقم الهاتف"></div>
            <div class="col-md-2"><input type="number" step="0.01" name="balance" class="form-control" placeholder="الدين السابـق"></div>
            <div class="col-md-2"><button type="submit" class="btn btn-primary w-100">إضافة</button></div>
        </form>
    </div>
    
    <table class="table table-bordered bg-white text-center">
        <thead class="table-dark">
            <tr>
                <th>#</th><th>اسم الوكيل</th><th>الهاتف</th><th>الرصيد/الدين الحتلي</th><th>إجراءات / طباعة</th>
            </tr>
        </thead>
        <tbody>
            {% for c in clients_list %}
            <tr>
                <td>{{ c[0] }}</td>
                <td>{{ c[1] }}</td>
                <td>{{ c[2] }}</td>
                <td class="fw-bold {% if c[3] > 0 %}text-danger{% else %}text-success{% endif %}">{{ c[3] }}</td>
                <td>
                    <a href="/client/{{ c[0] }}" class="btn btn-sm btn-info">عرض الحساب / سند قبض / وصل</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    '''
    return render_template_string(html, clients_list=clients_list)

# 2. كشف حساب الوكيل وطباعة الوصولات
@app.route('/client/<int:client_id>', methods=['GET', 'POST'])
def client_detail(client_id):
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        trans_type = request.form['type'] # 'PAYMENT' أو 'INVOICE'
        amount = float(request.form['amount'])
        details = request.form['details']
        
        # تحديث رصيد الوكيل
        if trans_type == 'PAYMENT':
            cursor.execute("UPDATE clients SET balance = balance - ? WHERE id = ?", (amount, client_id))
        else:
            cursor.execute("UPDATE clients SET balance = balance + ? WHERE id = ?", (amount, client_id))
            
        cursor.execute("INSERT INTO transactions (client_id, type, amount, details) VALUES (?, ?, ?, ?)",
                       (client_id, trans_type, amount, details))
        conn.commit()
        return redirect(url_for('client_detail', client_id=client_id))
        
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    
    cursor.execute("SELECT * FROM transactions WHERE client_id = ? ORDER BY date DESC", (client_id,))
    transactions = cursor.fetchall()
    conn.close()
    
    html = BASE_TEMPLATE + '''
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h2>كشف حساب: {{ client[1] }}</h2>
        <button onclick="window.print()" class="btn btn-secondary no-print">🖨️ طباعة كشف الحساب / الوصل</button>
    </div>
    <p><strong>رقم الهاتف:</strong> {{ client[2] }} | <strong>الرصيد / الدين الحالي:</strong> <span class="badge bg-danger fs-6">{{ client[3] }}</span></p>
    
    <div class="card p-3 mb-4 no-print">
        <h5>إضافة عملية جديدة (فاتورة بيع / سند قبض استلام مبلغ)</h5>
        <form method="POST" class="row g-2">
            <div class="col-md-3">
                <select name="type" class="form-select">
                    <option value="PAYMENT">سند قبض (استلام مبلغ من الوكيل)</option>
                    <option value="INVOICE">فاتورة بيع (إضافة دين برادات)</option>
                </select>
            </div>
            <div class="col-md-3"><input type="number" step="0.01" name="amount" class="form-control" placeholder="المبلغ" required></div>
            <div class="col-md-4"><input type="text" name="details" class="form-control" placeholder="تفاصيل (مثلاً: تسليم 5 برادات / دفعة نقداً)"></div>
            <div class="col-md-2"><button type="submit" class="btn btn-success w-100">حفظ وحساب</button></div>
        </form>
    </div>

    <h4>سجل المعاملات والوصولات:</h4>
    <table class="table table-striped bg-white">
        <thead>
            <tr><th>التاريخ</th><th>نوع المعاملة</th><th>المبلغ</th><th>التفاصيل</th></tr>
        </thead>
        <tbody>
            {% for t in transactions %}
            <tr>
                <td>{{ t[4] }}</td>
                <td>{% if t[2] == 'PAYMENT' %}<span class="badge bg-success">سند قبض (-)</span>{% else %}<span class="badge bg-danger">فاتورة (+)</span{% endif %}</td>
                <td>{{ t[3] }}</td>
                <td>{{ t[3] }} - {{ t[3] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    '''
    return render_template_string(html, client=client, transactions=transactions)

# 3. إدارة المواد الخام (28 مادة)
@app.route('/materials', methods=['GET', 'POST'])
def materials():
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        qty = request.form['quantity']
        cost = request.form['unit_cost']
        cursor.execute("INSERT INTO raw_materials (name, quantity, unit_cost) VALUES (?, ?, ?)", (name, qty, cost))
        conn.commit()
        return redirect(url_for('materials'))
        
    cursor.execute("SELECT * FROM raw_materials")
    items = cursor.fetchall()
    conn.close()
    
    html = BASE_TEMPLATE + '''
    <h3>إدارة مخزن المواد الخام (الـ 28 مادة)</h3>
    <div class="card p-3 mb-4 no-print">
        <h5>إضافة مادة خام جديدة (موتور، صاج، نحاس، عازل...)</h5>
        <form method="POST" class="row g-2">
            <div class="col-md-5"><input type="text" name="name" class="form-control" placeholder="اسم المادة الخام" required></div>
            <div class="col-md-3"><input type="number" step="0.1" name="quantity" class="form-control" placeholder="الكمية" required></div>
            <div class="col-md-2"><input type="number" step="0.01" name="unit_cost" class="form-control" placeholder="تكلفة الوحدة" required></div>
            <div class="col-md-2"><button type="submit" class="btn btn-primary w-100">إضافة للمخزن</button></div>
        </form>
    </div>
    
    <table class="table table-bordered bg-white text-center">
        <thead class="table-dark">
            <tr><th>#</th><th>المادة</th><th>الكمية المتوفرة</th><th>تكلفة الوحدة</th></tr>
        </thead>
        <tbody>
            {% for i in items %}
            <tr><td>{{ i[0] }}</td><td>{{ i[1] }}</td><td>{{ i[2] }}</td><td>{{ i[3] }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    '''
    return render_template_string(html, items=items)

# 4. مخزن البرادات التامة
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect('factory.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        model_name = request.form['model_name']
        stock = request.form['stock']
        cost_price = request.form['cost_price']
        selling_price = request.form['selling_price']
        cursor.execute("INSERT INTO finished_coolers (model_name, stock, cost_price, selling_price) VALUES (?, ?, ?, ?)",
                       (model_name, stock, cost_price, selling_price))
        conn.commit()
        return redirect(url_for('inventory'))
        
    cursor.execute("SELECT * FROM finished_coolers")
    coolers = cursor.fetchall()
    conn.close()
    
    html = BASE_TEMPLATE + '''
    <h3>مخزن المنتج التام (برادات الماء الجاهزة)</h3>
    <div class="card p-3 mb-4 no-print">
        <h5>إدخال وجبة برادات مصنعة جاهزة للبيع</h5>
        <form method="POST" class="row g-2">
            <div class="col-md-3"><input type="text" name="model_name" class="form-control" placeholder="موديل البراد (مثلاً: براد 3 عيون)" required></div>
            <div class="col-md-3"><input type="number" name="stock" class="form-control" placeholder="العدد المصنع" required></div>
            <div class="col-md-3"><input type="number" step="0.01" name="cost_price" class="form-control" placeholder="تكلفة الإنتاج للواحد" required></div>
            <div class="col-md-3"><input type="number" step="0.01" name="selling_price" class="form-control" placeholder="سعر البيع للوكيل" required></div>
            <div class="col-md-12 text-end mt-2"><button type="submit" class="btn btn-success">تسجيل بالمخزن</button></div>
        </form>
    </div>
    
    <table class="table table-bordered bg-white text-center">
        <thead class="table-dark">
            <tr><th>#</th><th>الموديل</th><th>المخزون المتوفر</th><th>التكلفة</th><th>سعر البيع</th></tr>
        </thead>
        <tbody>
            {% for c in coolers %}
            <tr><td>{{ c[0] }}</td><td>{{ c[1] }}</td><td>{{ c[2] }} براد</td><td>{{ c[3] }}</td><td>{{ c[4] }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    '''
    return render_template_string(html, coolers=coolers)

if __name__ == '__main__':
    # تشغيل التطبيق في وضع التطوير
    app.run(debug=True, host='0.0.0.0', port=5000)
