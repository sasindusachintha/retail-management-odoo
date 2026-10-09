# Retail Management System — Odoo 19

A complete retail shop management system built as a custom **Odoo 19** module for managing day-to-day retail operations including point of sale, products, customers, sales, payments, inventory, suppliers, purchases, and business reporting.

The system is designed around a practical retail workflow, from purchasing stock from suppliers to selling products to customers and analyzing business performance through reports.

---

## Features

### 📊 Dashboard

A centralized dashboard providing an overview of the shop's current activity.

* Today's sales.
* Today's orders.
* Product count.
* Customer count.
* Low-stock products.
* Recent sales.
* Quick access to major shop functions

---

### 🛒 Point of Sale

A custom retail POS interface designed for fast checkout.

* Product search
* Product selection
* Customer selection
* Cart management
* Quantity adjustment
* Discounts
* Multiple payment methods
* Sale confirmation
* Automatic stock deduction
* Automatic payment recording
* Sales history
* Receipt printing

---

### 📦 Product Management

Manage the products sold by the shop.

* Product name
* Category
* Selling price
* Stock quantity
* Product description
* Active/inactive products
* Product filtering
* Inventory tracking

---

### 👥 Customer Management

Manage retail customers and their sales activity.

* Customer records
* Customer contact information
* Customer selection during POS checkout
* Customer-linked sales
* Customer purchase history

---

### 💰 Sales Management

Complete sales order management.

* Sales order creation
* Sales order lines
* Product quantities
* Discounts
* Sales totals
* Sale confirmation
* Automatic stock deduction
* Automatic payment creation
* Sales history
* Receipt generation

---

### 💳 Payment Management

Track payments associated with sales.

* Payment recording
* Payment methods
* Payment amounts
* Sale-linked payments
* Payment history
* Sales by payment method reporting

---

### 📦 Inventory & Stock Management

Track and manage shop inventory.

* Current stock quantities
* Stock adjustments
* Stock movement history
* Automatic stock reduction after sales
* Automatic stock increase after purchases
* Low-stock identification
* Out-of-stock identification
* Stock valuation

---

### 🚚 Supplier Management

Manage suppliers and supplier information.

* Supplier records
* Supplier contact details
* Supplier-linked purchases
* Supplier purchase history

---

### 🧾 Purchase Management

Manage stock purchases from suppliers.

* Purchase orders
* Purchase order lines
* Supplier selection
* Product quantities
* Purchase costs
* Purchase totals
* Purchase receiving
* Automatic stock increase
* Purchase history

---

# 📈 Business Reports

The system includes a dedicated **Reports** section for analyzing business activity.

### Daily Sales

View sales activity for a selected day.

### Monthly Sales

Analyze sales across a selected month.

### Sales by Product

Analyze products sold during a selected date range.

Includes:

* Product
* Quantity sold
* Sales amount
* Total quantity
* Total sales

### Sales by Payment Method

Analyze sales grouped by payment method.

Includes:

* Payment method
* Number of transactions
* Sales amount
* Total transactions
* Total sales

### Purchase Report

Analyze purchases made during a selected period.

Includes supplier and purchase information with purchase totals.

### Profit Report

Analyze business profitability using actual sales and purchase-cost information.

Includes:

* Quantity sold
* Sales revenue
* Product cost
* Profit
* Profit margin
* Total sales
* Total cost
* Total profit
* Overall profit margin

### Stock Report

Analyze current inventory.

Includes:

* Product
* Category
* Current stock
* Unit cost
* Stock value
* Stock status
* Total products
* Total quantity
* Total stock value
* Low-stock products
* Out-of-stock products
* Products without purchase cost

**Stock costing:** Unit cost is calculated using the weighted-average cost of received purchases. Products without purchase history have a cost of `0`.

---

# 🔄 Core Business Workflow

The system follows a connected retail workflow:

```text
Supplier
   │
   ▼
Purchase
   │
   ▼
Receive Stock
   │
   ▼
Inventory
   │
   ▼
Point of Sale
   │
   ▼
Sale
   │
   ├──► Payment
   │
   ├──► Stock Reduction
   │
   └──► Receipt
          │
          ▼
       Reports
```

This allows sales, payments, purchases, inventory and reporting to work together using the same underlying business data.

---

# 🏗️ Technology Stack

| Technology | Purpose                     |
| ---------- | --------------------------- |
| Odoo 19    | ERP / Application Framework |
| Python     | Backend & Business Logic    |
| PostgreSQL | Database                    |
| XML        | Odoo Views & Configuration  |
| JavaScript | Custom POS & Dashboard UI   |
| CSS        | UI Styling                  |
| QWeb       | PDF Receipt Generation      |

---

# 📁 Module Structure

```text
shop_management/
│
├── models/
│   ├── product.py
│   ├── customer.py
│   ├── sale_order.py
│   ├── payment.py
│   ├── dashboard.py
│   ├── stock.py
│   ├── supplier.py
│   ├── purchase.py
│   ├── report_common.py
│   ├── report_payment_method.py
│   ├── report_purchase.py
│   ├── report_profit.py
│   └── report_stock.py
│
├── views/
│   ├── product_views.xml
│   ├── customer_views.xml
│   ├── sale_order_views.xml
│   ├── payment_views.xml
│   ├── retail_pos_views.xml
│   ├── sale_receipt.xml
│   ├── stock_views.xml
│   ├── supplier_views.xml
│   ├── purchase_views.xml
│   ├── report_extra_views.xml
│   ├── menu_root.xml
│   └── menu.xml
│
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
│
├── data/
│   └── sequence.xml
│
├── static/
│   ├── description/
│   │   └── icon.png
│   │
│   └── src/
│       ├── css/
│       ├── js/
│       └── xml/
│
├── __init__.py
├── __manifest__.py
└── .gitignore
```

---

# 🗃️ Main Business Models

The module uses dedicated models for the main retail operations:

```text
shop.product
shop.customer
shop.sale.order
shop.sale.order.line
shop.payment
shop.stock.movement
shop.stock.adjustment
shop.supplier
shop.purchase.order
shop.purchase.order.line
```

Reporting functionality is implemented through dedicated transient report models.

---

# 🔐 Security & Access

The module includes role-based security groups for different shop responsibilities.

Current groups include:

* **Shop Manager**
* **Shop Cashier**
* **Shop Inventory**

The permission structure can be configured according to the responsibilities of each user.

---

# ⚙️ Installation

## Requirements

* Odoo 19
* Python 3.12+
* PostgreSQL
* Git

---

## Clone the Repository

```bash
git clone https://github.com/sasindusachintha/retail-management-odoo.git
```

Copy the `shop_management` module into your Odoo custom addons directory.

Example:

```text
E:\Odoo19\custom-addons\shop_management
```

---

## Configure Odoo

Add the custom addons directory to your Odoo configuration:

```ini
addons_path = E:\Odoo19\odoo-19.0\addons,E:\Odoo19\custom-addons
```

Restart Odoo and update the Apps list.

Then install:

**Shop Management**

---

# 🧪 Development Environment

Example development setup:

```text
Odoo:
19.0

Python:
3.12

PostgreSQL:
18

Database:
shop_dev
```

---

# 🚀 Development Commands

Start Odoo:

```powershell
cd E:\Odoo19\odoo-19.0
E:\Odoo19\venv\Scripts\Activate.ps1
python odoo-bin -c E:\Odoo19\odoo.conf --data-dir="E:\Odoo19\odoo-data"
```

Update the module:

```powershell
cd E:\Odoo19\odoo-19.0
E:\Odoo19\venv\Scripts\Activate.ps1
python odoo-bin -c E:\Odoo19\odoo.conf -d shop_dev -u shop_management --stop-after-init --data-dir="E:\Odoo19\odoo-data"
```

---

# 📋 Current System Status

| Feature                 | Status |
| ----------------------- | ------ |
| Dashboard               | ✅      |
| Point of Sale           | ✅      |
| Products                | ✅      |
| Customers               | ✅      |
| Sales                   | ✅      |
| Payments                | ✅      |
| Stock Management        | ✅      |
| Suppliers               | ✅      |
| Purchases               | ✅      |
| Daily Sales Report      | ✅      |
| Monthly Sales Report    | ✅      |
| Sales by Product        | ✅      |
| Sales by Payment Method | ✅      |
| Purchase Report         | ✅      |
| Profit Report           | ✅      |
| Stock Report            | ✅      |
| PDF Sales Receipt       | ✅      |

---

# 🛣️ Roadmap

Planned improvements include:

* [ ] Role-based access refinement
* [ ] Product barcode support
* [ ] Product images
* [ ] SKU / barcode management
* [ ] Advanced product categories
* [ ] Customer purchase history improvements
* [ ] Supplier balance tracking
* [ ] Sales returns and refunds
* [ ] POS hold/resume orders
* [ ] Advanced discounts
* [ ] Shop configuration
* [ ] Receipt customization
* [ ] Backup and restore improvements
* [ ] UI/UX improvements
* [ ] Deployment documentation

---

# 🎯 Project Goals

The main goal of this project is to provide a practical retail management solution that connects:

**Sales + POS + Payments + Inventory + Purchases + Suppliers + Customers + Reports**

within a single Odoo-based system.

The project is designed with real retail workflows in mind rather than isolated demonstration features.

---

# 👨‍💻 Author

**Sasindu Sachintha Bandara**

Software Engineering Undergraduate
Sri Lanka

GitHub:
https://github.com/sasindusachintha

---

# 📄 License

This project is licensed under the **LGPL-3.0** license.
