from collections import defaultdict

from odoo import Command, api, fields, models


class ShopReportPurchase(models.TransientModel):
    _name = 'shop.report.purchase'
    _inherit = ['shop.report.mixin']
    _description = 'Purchase Report'

    supplier_id = fields.Many2one('shop.supplier', string='Supplier')
    line_ids = fields.One2many(
        'shop.report.purchase.line', 'report_id', string='Purchases',
    )
    product_line_ids = fields.One2many(
        'shop.report.purchase.product', 'report_id', string='Items Purchased',
    )
    purchase_count = fields.Integer(
        string='Number of Purchases', compute='_compute_totals',
    )
    total_amount = fields.Float(
        string='Total Purchase Amount', compute='_compute_totals',
    )

    @api.depends('line_ids.total')
    def _compute_totals(self):
        for report in self:
            report.purchase_count = len(report.line_ids)
            report.total_amount = sum(report.line_ids.mapped('total'))

    def action_generate(self):
        self.ensure_one()
        warning = self._invalid_range_notification()
        if warning:
            return warning

        start, end = self._get_utc_range()
        domain = [
            ('state', '=', 'received'),
            ('purchase_date', '>=', start),
            ('purchase_date', '<', end),
        ]
        if self.supplier_id:
            domain.append(('supplier_id', '=', self.supplier_id.id))
        purchases = self.env['shop.purchase.order'].search(
            domain, order='purchase_date, id',
        )

        line_cmds = [Command.clear()]
        per_product = defaultdict(lambda: [0.0, 0.0])
        for purchase in purchases:
            line_cmds.append(Command.create({
                'purchase_id': purchase.id,
                'supplier_id': purchase.supplier_id.id,
                'purchase_date': purchase.purchase_date,
                'items': sum(purchase.line_ids.mapped('quantity')),
                'total': purchase.total,
            }))
            for line in purchase.line_ids:
                per_product[line.product_id.id][0] += line.quantity
                per_product[line.product_id.id][1] += line.subtotal

        product_cmds = [Command.clear()]
        for product_id, (qty, cost) in sorted(
            per_product.items(), key=lambda item: -item[1][1],
        ):
            product_cmds.append(Command.create({
                'product_id': product_id,
                'quantity': qty,
                'avg_cost': cost / qty if qty else 0.0,
                'total_cost': cost,
            }))

        self.write({'line_ids': line_cmds, 'product_line_ids': product_cmds})
        return True


class ShopReportPurchaseLine(models.TransientModel):
    _name = 'shop.report.purchase.line'
    _description = 'Purchase Report Line'
    _order = 'purchase_date, id'

    report_id = fields.Many2one(
        'shop.report.purchase', required=True, ondelete='cascade',
    )
    purchase_id = fields.Many2one('shop.purchase.order', string='Purchase')
    supplier_id = fields.Many2one('shop.supplier', string='Supplier')
    purchase_date = fields.Datetime(string='Date')
    items = fields.Float(string='Items (Qty)')
    total = fields.Float(string='Total')


class ShopReportPurchaseProduct(models.TransientModel):
    _name = 'shop.report.purchase.product'
    _description = 'Purchase Report Item Line'
    _order = 'total_cost desc, id'

    report_id = fields.Many2one(
        'shop.report.purchase', required=True, ondelete='cascade',
    )
    product_id = fields.Many2one('shop.product', string='Product')
    quantity = fields.Float(string='Quantity Purchased')
    avg_cost = fields.Float(string='Average Cost')
    total_cost = fields.Float(string='Total Cost')
