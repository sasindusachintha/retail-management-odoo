from odoo import models, fields, api
from odoo.exceptions import ValidationError



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

    # -------------------------------------------------------
    # PHASE 2: Price / quantity constraints (Rule #13)
    # -------------------------------------------------------

    @api.constrains('price')
    def _check_price(self):
        for product in self:
            if product.price < 0:
                raise ValidationError(
                    f'Selling price for "{product.name}" cannot be negative.'
                )

    @api.constrains('min_stock')
    def _check_min_stock(self):
        for product in self:
            if product.min_stock < 0:
                raise ValidationError(
                    f'Minimum stock for "{product.name}" cannot be negative.'
                )

    @api.constrains('quantity')
    def _check_quantity_not_negative(self):
        """Last-resort guard: prevents any write that sets quantity < 0."""
        for product in self:
            if product.quantity < 0:
                raise ValidationError(
                    f'Stock quantity for "{product.name}" cannot be negative.'
                )