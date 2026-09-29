{
    'name': 'Shop Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Complete retail shop management system',
    'description': """
        Retail management system with POS,
        products, customers, sales and payments.
    """,
    'author': 'Sasindu',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'web',
    ],

    'assets': {
        'web.assets_web': [
        'shop_management/static/src/js/retail_pos.js',
        'shop_management/static/src/js/dashboard.js',

        'shop_management/static/src/xml/retail_pos.xml',
        'shop_management/static/src/xml/dashboard.xml',

        'shop_management/static/src/css/retail_pos.css',
        'shop_management/static/src/css/dashboard.css',
        ],
    },

    'data': [
    'security/security.xml',
    'security/ir.model.access.csv',

    'data/sequence.xml',

    'views/menu_root.xml',
    'views/product_views.xml',
    'views/customer_views.xml',
    'views/sale_receipt.xml',
    'views/sale_order_views.xml',
    'views/payment_views.xml',
    'views/retail_pos_views.xml',
    'views/stock_views.xml',
    'views/supplier_views.xml',
    'views/purchase_views.xml',
    'views/menu.xml',
    'views/report_extra_views.xml',
    ],

    'installable': True,
    'application': True,
}

