from odoo import models, fields


class ShopProduct(models.Model):
    _name = 'shop.product'
    _description = 'Shop Product'
    _order = 'name'

    name = fields.Char(
        string='Product Name',
        required=True
    )

    price = fields.Float(
        string='Selling Price',
        required=True
    )

    quantity = fields.Float(
        string='Stock Quantity',
        default=0
    )

    min_stock = fields.Float(
        string='Minimum Stock',
        default=5
    )

    category = fields.Char(
        string='Category'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description'
    )

    stock_status = fields.Selection(
        [
            ('out', 'Out of Stock'),
            ('low', 'Low Stock'),
            ('ok', 'In Stock'),
        ],
        string='Stock Status',
        compute='_compute_stock_status',
        store=True
    )

    def _compute_stock_status(self):
        for product in self:
            if product.quantity <= 0:
                product.stock_status = 'out'
            elif product.quantity <= product.min_stock:
                product.stock_status = 'low'
            else:
                product.stock_status = 'ok'