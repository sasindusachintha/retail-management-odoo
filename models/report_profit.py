from collections import defaultdict

from odoo import Command, api, fields, models


class ShopReportProfit(models.TransientModel):
    _name = 'shop.report.profit'
    _inherit = ['shop.report.mixin']
    _description = 'Profit Report'

    product_id = fields.Many2one('shop.product', string='Product')
    line_ids = fields.One2many(
        'shop.report.profit.line', 'report_id', string='Results',
    )
    total_sales = fields.Float(string='Total Sales', compute='_compute_totals')
    total_cost = fields.Float(string='Total Cost', compute='_compute_totals')
    total_profit = fields.Float(string='Total Profit', compute='_compute_totals')
    overall_margin = fields.Float(
        string='Overall Profit Margin %', compute='_compute_totals',
    )
    missing_cost_count = fields.Integer(
        string='Products Without Purchase Cost', compute='_compute_totals',
    )

    @api.depends('line_ids.revenue', 'line_ids.cost', 'line_ids.cost_missing')
    def _compute_totals(self):
        for report in self:
            sales = sum(report.line_ids.mapped('revenue'))
            cost = sum(report.line_ids.mapped('cost'))
            report.total_sales = sales
            report.total_cost = cost
            report.total_profit = sales - cost
            report.overall_margin = (
                (sales - cost) / sales * 100.0 if sales else 0.0
            )
            report.missing_cost_count = len(
                report.line_ids.filtered('cost_missing')
            )

    def action_generate(self):
        self.ensure_one()
        warning = self._invalid_range_notification()
        if warning:
            return warning

        start, end = self._get_utc_range()
        domain = [
            ('order_id.state', '=', 'confirmed'),
            ('order_id.order_date', '>=', start),
            ('order_id.order_date', '<', end),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        sale_lines = self.env['shop.sale.order.line'].search(domain)

        # Spread any order-level discount across the order's lines so revenue
        # matches what was actually charged (order.amount_total).
        totals = defaultdict(lambda: [0.0, 0.0])  # product_id -> [qty, revenue]
        for line in sale_lines:
            order = line.order_id
            factor = order.amount_total / order.subtotal if order.subtotal else 0.0
            totals[line.product_id.id][0] += line.quantity
            totals[line.product_id.id][1] += line.subtotal * factor

        costs = self._get_product_costs(list(totals), before=end)

        rows = []
        for product_id, (qty, revenue) in totals.items():
            unit_cost = costs.get(product_id, 0.0)
            cost = qty * unit_cost
            profit = revenue - cost
            rows.append({
                'product_id': product_id,
                'quantity': qty,
                'revenue': revenue,
                'unit_cost': unit_cost,
                'cost': cost,
                'profit': profit,
                'margin': profit / revenue * 100.0 if revenue else 0.0,
                'cost_missing': product_id not in costs,
            })
        rows.sort(key=lambda row: -row['profit'])

        self.line_ids = [Command.clear()] + [Command.create(r) for r in rows]
        return True


class ShopReportProfitLine(models.TransientModel):
    _name = 'shop.report.profit.line'
    _description = 'Profit Report Line'
    _order = 'profit desc, id'

    report_id = fields.Many2one(
        'shop.report.profit', required=True, ondelete='cascade',
    )
    product_id = fields.Many2one('shop.product', string='Product')
    quantity = fields.Float(string='Qty Sold')
    revenue = fields.Float(string='Sales')
    unit_cost = fields.Float(string='Unit Cost')
    cost = fields.Float(string='Cost')
    profit = fields.Float(string='Profit')
    margin = fields.Float(string='Margin %')
    cost_missing = fields.Boolean(string='No Purchase Cost')
