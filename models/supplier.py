from odoo import models, fields


class ShopSupplier(models.Model):
    _name = 'shop.supplier'
    _description = 'Shop Supplier'
    _order = 'name'

    name = fields.Char(
        string='Supplier Name',
        required=True
    )

    phone = fields.Char(
        string='Phone'
    )

    email = fields.Char(
        string='Email'
    )

    address = fields.Text(
        string='Address'
    )

    notes = fields.Text(
        string='Notes'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    product_ids = fields.One2many(
        'shop.product',
        'supplier_id',
        string='Products'
    )