from odoo import models, fields


class ShopSupplierProductLine(models.TransientModel):
    _name = 'shop.supplier.product.line'
    _description = 'Supplier Product History Line'
    _order = 'last_purchase_date desc, id'

    supplier_id = fields.Many2one(
        'shop.supplier',
        string='Supplier',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True
    )

    last_purchase_date = fields.Datetime(
        string='Last Purchase Date'
    )

    last_purchase_cost = fields.Float(
        string='Last Purchase Cost'
    )

    previous_purchase_cost = fields.Float(
        string='Previous Purchase Cost'
    )

    total_quantity = fields.Float(
        string='Total Qty Purchased'
    )

    total_amount = fields.Float(
        string='Total Amount Spent'
    )
