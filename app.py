-- 1. جدول المواد الخام
CREATE TABLE raw_materials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    unit VARCHAR(20) NOT NULL, -- (قطعة، متر، كجم، إلخ)
    stock_quantity DECIMAL(10,2) DEFAULT 0.00,
    min_safety_limit DECIMAL(10,2) DEFAULT 0.00
);

-- 2. جدول أصناف برادات المياه
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    model_code VARCHAR(50) UNIQUE NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0
);

-- 3. جدول قائمة المكونات (BOM - Bill of Materials)
-- يربط كل براد بالمواد الخام التي يستهلكها
CREATE TABLE product_bom (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    raw_material_id INT NOT NULL,
    required_quantity DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (raw_material_id) REFERENCES raw_materials(id)
);

-- 4. جدول الوكلاء
CREATE TABLE agents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    phone VARCHAR(30),
    company_name VARCHAR(150),
    credit_limit DECIMAL(12,2) DEFAULT 0.00,
    balance DECIMAL(12,2) DEFAULT 0.00 -- المديونية الحالية
);

-- 5. جدول الفواتير / السندات (الحسابات)
CREATE TABLE transactions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    agent_id INT NOT NULL,
    type ENUM('INVOICE', 'PAYMENT_RECEIPT') NOT NULL, -- فاتورة بيع أو وصل قبض
    amount DECIMAL(12,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
