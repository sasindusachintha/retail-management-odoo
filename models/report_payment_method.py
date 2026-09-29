from odoo import Command, api, fields, models


class ShopReportPaymentMethod(models.TransientModel):
    _name = 'shop.report.payment.method'
    _inherit = ['shop.report.mixin']
    _description = 'Sales by Payment Method Report'

    payment_method = fields.Selection(
        selection='_selection_payment_method',
        string='Payment Method',
    )
    line_ids = fields.One2many(
        'shop.report.payment.method.line',
        'report_id',
        string='Results',
    )
    total_transactions = fields.Integer(
        string='Total Transactions',
        compute='_compute_totals',
    )
    total_sales = fields.Float(
        string='Total Sales',
        compute='_compute_totals',
    )

    @api.model
    def _selection_payment_method(self):
        return self.env['shop.sale.order']._fields['payment_method'].selection

    @api.depends('line_ids.transactions', 'line_ids.sales_amount')
    def _compute_totals(self):
        for report in self:
            report.total_transactions = sum(report.line_ids.mapped('transactions'))
            report.total_sales = sum(report.line_ids.mapped('sales_amount'))

    def action_generate(self):
        self.ensure_one()
        warning = self._invalid_range_notification()
        if warning:
            return warning

        start, end = self._get_utc_range()
        domain = [
            ('state', '=', 'confirmed'),
            ('order_date', '>=', start),
            ('order_date', '<', end),
        ]
        if self.payment_method:
            domain.append(('payment_method', '=', self.payment_method))

        labels = dict(self._selection_payment_method())
        groups = self.env['shop.sale.order']._read_group(
            domain, ['payment_method'], ['__count', 'amount_total:sum'],
        )
        grand_total = sum(amount for _m, _c, amount in groups)

        commands = [Command.clear()]
        for method, count, amount in groups:
            commands.append(Command.create({
                'method_name': labels.get(method, 'Other'),
                'transactions': count,
                'sales_amount': amount,
                'share': (amount / grand_total * 100.0) if grand_total else 0.0,
            }))
        self.line_ids = commands
        return True


class ShopReportPaymentMethodLine(models.TransientModel):
    _name = 'shop.report.payment.method.line'
    _description = 'Sales by Payment Method Report Line'
    _order = 'sales_amount desc, id'

    report_id = fields.Many2one(
        'shop.report.payment.method',
        required=True,
        ondelete='cascade',
    )
    method_name = fields.Char(string='Payment Method')
    transactions = fields.Integer(string='Transactions')
    sales_amount = fields.Float(string='Sales Amount')
    share = fields.Float(string='Share %')
