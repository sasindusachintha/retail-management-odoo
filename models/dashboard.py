from odoo import models, api


class ShopDashboard(models.AbstractModel):
    _name = 'shop.dashboard'
    _description = 'Shop Management Dashboard'

    @api.model
    def get_dashboard_data(self):
        Product = self.env['shop.product']
        Customer = self.env['shop.customer']
        SaleOrder = self.env['shop.sale.order']

        self.env.cr.execute("SELECT date_trunc('day', NOW() AT TIME ZONE 'UTC')")
        today_start = self.env.cr.fetchone()[0].replace(tzinfo=None)

        today_sales = sum(
            SaleOrder.search([
                ('state', '=', 'confirmed'),
                ('order_date', '>=', today_start),
            ]).mapped('amount_total')
        )

        today_orders = SaleOrder.search_count([
            ('state', '=', 'confirmed'),
            ('order_date', '>=', today_start),
        ])

        total_products = Product.search_count([
            ('active', '=', True),
        ])

        total_customers = Customer.search_count([
            ('active', '=', True),
        ])

        low_stock_products = Product.search([
            ('active', '=', True),
            ('quantity', '<=', 5),
        ], order='quantity asc', limit=10)

        recent_sales = SaleOrder.search([
            ('state', '=', 'confirmed'),
        ], order='order_date desc', limit=10)

        return {
            'today_sales': today_sales,
            'today_orders': today_orders,
            'total_products': total_products,
            'total_customers': total_customers,

            'low_stock_count': len(low_stock_products),

            'low_stock_products': [
                {
                    'id': product.id,
                    'name': product.name,
                    'quantity': product.quantity,
                }
                for product in low_stock_products
            ],

            'recent_sales': [
                {
                    'id': order.id,
                    'name': order.name,
                    'customer': order.customer_id.name
                    if order.customer_id else 'Walk-in Customer',
                    'amount': order.amount_total,
                    'date': order.order_date,
                }
                for order in recent_sales
            ],
        }