from odoo import models, fields


class ShopProductSupplierComparison(models.TransientModel):
    _name = 'shop.product.supplier.comparison'
    _description = 'Product Supplier Comparison Line'
    _order = 'latest_cost asc, id'

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True,
        ondelete='cascade'
    )

    supplier_id = fields.Many2one(
        'shop.supplier',
        string='Supplier',
        required=True
    )

    latest_cost = fields.Float(
        string='Latest Cost'
    )

    previous_cost = fields.Float(
        string='Previous Cost'
    )

    total_quantity = fields.Float(
        string='Qty Purchased'
    )

    total_spent = fields.Float(
        string='Total Spent'
    )

    is_cheapest = fields.Boolean(
        string='Is Lowest Cost'
    )
