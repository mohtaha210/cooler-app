from flask import Flask, jsonify, request, render_template_string
import sqlite3

app = Flask(__name__)

# إعداد قاعدة البيانات في الذاكرة
def init_db():
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المواد الخام
    cursor.execute('''CREATE TABLE materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity REAL,
        unit TEXT
    )''')
    
    # جدول المنتجات التامة (البرادات)
    cursor.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity INTEGER
    )''')
    
    # جدول الوكلاء والديون
    cursor.execute('''CREATE TABLE agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        debt REAL DEFAULT 0
    )''')
    
    # جدول الحركات المالية
    cursor.execute('''CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        type TEXT,
        amount REAL,
        details TEXT,
        date TEXT
    )''')
    
    # إدخال بيانات تجريبية أولية
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('صفيحة معدنية', 100, 'قطعة')")
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('ضاغط تبريد (كمبريسور)', 50, 'قطعة')")
    cursor.execute("INSERT INTO materials (name, quantity, unit) VALUES ('خزان مياه داخلي', 60, 'قطعة')")
    cursor.execute("INSERT INTO products (name, quantity) VALUES ('براد ماء ستانلس 2 بزبور', 5)")
    cursor.execute("INSERT INTO agents (name, phone, debt) VALUES ('وكيل بغداد', '07700000000', 250000)")
    
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# الصفحة الرئيسية (واجهة المستخدم المدمجة)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>إدارة معمل برادات الماء</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; }
        .card { background: #fff; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #007bff; color: white; }
        button { background: #28a745; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; }
        .btn-prod { background: #ffc107; color: black; font-weight: bold; font-size: 16px; }
    </style>
</head>
<body>
    <h1>مصنع برادات الماء - لوحة التحكم (Python/Flask)</h1>
    <div class="card">
        <h2>إدارة الإنتاج والمخزون</h2>
        <button class="btn-prod" onclick="produceCooler()">⚙️ إنتاج براد ماء جديد</button>
        <h3>المواد الخام:</h3>
        <table id="materialsTable"></table>
        <h3>البرادات الجاهزة:</h3>
        <table id="productsTable"></table>
    </div>
    <div class="card">
        <h2>حسابات الوكلاء والديون</h2>
        <table>
            <thead><tr><th>اسم الوكيل</th><th>الهاتف</th><th>الديون المستحقة</th><th>إجراء</th></tr></thead>
            <tbody id="agentsTable"></tbody>
        </table>
    </div>
    <script>
        async function loadData() {
            const res = await fetch('/api/data');
            const data = await res.json();
            
            let matHtml = `<tr><th>المادة</th><th>الكمية</th><th>الوحدة</th></tr>`;
            data.materials.forEach(m => matHtml += `<tr><td>${m[1]}</td><td>${m[2]}</td><td>${m[3]}</td></tr>`);
            document.getElementById('materialsTable').innerHTML = matHtml;

            let prodHtml = `<tr><th>نوع البراد</th><th>الكمية</th></tr>`;
            data.products.forEach(p => prodHtml += `<tr><td>${p[1]}</td><td>${p[2]}</td></tr>`);
            document.getElementById('productsTable').innerHTML = prodHtml;

            let agtHtml = '';
            data.agents.forEach(a => {
                agtHtml += `<tr><td>${a[1]}</td><td>${a[2]}</td><td style="color:red;font-weight:bold;">${a[3]} د.ع</td><td><button onclick="addTransaction(${a[0]})">حركة مالية</button></td></tr>`;
            });
            document.getElementById('agentsTable').innerHTML = agtHtml;
        }

        async function produceCooler() {
            const res = await fetch('/api/produce', { method: 'POST' });
            const result = await res.json();
            alert(result.message);
            loadData();
        }

        async function addTransaction(agentId) {
            const type = prompt("اختر نوع الحركة: sale (بيع بالدين) أو payment (تسديد)");
            if (type !== 'sale' && type !== 'payment') return;
            const amount = parseFloat(prompt("أدخل المبلغ (د.ع):"));
            if (isNaN(amount)) return;
            const details = prompt("تفاصيل الحركة:");

            const res = await fetch('/api/agent-transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId, type, amount, details })
            });
            const result = await res.json();
            alert(result.message);
            loadData();
        }
        loadData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/api/data')
def get_data():
    cursor.execute("SELECT * FROM materials")
    materials = cursor.fetchall()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.execute("SELECT * FROM agents")
    agents = cursor.fetchall()
    return jsonify(materials=materials, products=products, agents=agents)

@app.route('/api/produce', methods=['POST'])
def produce():
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'صفيحة معدنية'")
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'ضاغط تبريد (كمبريسور)'")
    cursor.execute("UPDATE materials SET quantity = quantity - 1 WHERE name = 'خزان مياه داخلي'")
    cursor.execute("UPDATE products SET quantity = quantity + 1 WHERE name = 'براد ماء ستانلس 2 بزبور'")
    conn.commit()
    return jsonify(success=True, message='تم إنتاج البراد وخصم المواد الخام بنجاح!')

@app.route('/api/agent-transaction', methods=['POST'])
def agent_transaction():
    data = request.json
    agent_id = data.get('agent_id')
    t_type = data.get('type')
    amount = data.get('amount')
    details = data.get('details')
    
    debt_change = amount if t_type == 'sale' else -amount
    cursor.execute("UPDATE agents SET debt = debt + ? WHERE id = ?", (debt_change, agent_id))
    cursor.execute("INSERT INTO transactions (agent_id, type, amount, details) VALUES (?, ?, ?, ?)",
                   (agent_id, t_type, amount, details))
    conn.commit()
    return jsonify(success=True, message='تم تسجيل الحركة المالية بنجاح')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
