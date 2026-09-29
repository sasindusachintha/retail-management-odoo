from odoo import models, fields


class ShopCustomer(models.Model):
    _name = 'shop.customer'
    _description = 'Shop Customer'
    _order = 'name'

    name = fields.Char(
        string='Customer Name',
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

    active = fields.Boolean(
        string='Active',
        default=True
    )

    notes = fields.Text(
        string='Notes'
    )