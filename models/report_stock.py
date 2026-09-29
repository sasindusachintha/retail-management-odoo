from odoo import Command, api, fields, models


class ShopReportStock(models.TransientModel):
    _name = 'shop.report.stock'
    _description = 'Stock Report'

    product_id = fields.Many2one('shop.product', string='Product')
    category = fields.Char(string='Category')
    stock_status = fields.Selection(
        selection='_selection_stock_status', string='Stock Status',
    )
    line_ids = fields.One2many(
        'shop.report.stock.line', 'report_id', string='Results',
    )
    total_products = fields.Integer(
        string='Total Products', compute='_compute_totals',
    )
    total_quantity = fields.Float(
        string='Total Quantity', compute='_compute_totals',
    )
    total_value = fields.Float(
        string='Total Stock Value', compute='_compute_totals',
    )
    low_count = fields.Integer(
        string='Low Stock Products', compute='_compute_totals',
    )
    out_count = fields.Integer(
        string='Out of Stock Products', compute='_compute_totals',
    )
    missing_cost_count = fields.Integer(
        string='Products Without Purchase Cost', compute='_compute_totals',
    )

    @api.model
    def _selection_stock_status(self):
        return self.env['shop.product']._fields['stock_status'].selection

    @api.depends('line_ids.quantity', 'line_ids.stock_value',
                 'line_ids.status', 'line_ids.cost_missing')
    def _compute_totals(self):
        for report in self:
            lines = report.line_ids
            report.total_products = len(lines)
            report.total_quantity = sum(lines.mapped('quantity'))
            report.total_value = sum(lines.mapped('stock_value'))
            report.low_count = len(lines.filtered(lambda l: l.status == 'low'))
            report.out_count = len(lines.filtered(lambda l: l.status == 'out'))
            report.missing_cost_count = len(lines.filtered('cost_missing'))

    def action_generate(self):
        self.ensure_one()
        domain = [('active', '=', True)]
        if self.product_id:
            domain.append(('id', '=', self.product_id.id))
        if self.category:
            domain.append(('category', 'ilike', self.category))
        products = self.env['shop.product'].search(domain, order='name')

        costs = self._get_current_costs(products.ids)

        commands = [Command.clear()]
        for product in products:
            # The stored stock_status on shop.product is not recomputed when
            # quantity changes, so derive the status from live quantity and
            # min_stock instead.
            if product.quantity <= 0:
                status = 'out'
            elif product.quantity <= product.min_stock:
                status = 'low'
            else:
                status = 'ok'
            if self.stock_status and status != self.stock_status:
                continue
            unit_cost = costs.get(product.id, 0.0)
            commands.append(Command.create({
                'product_id': product.id,
                'category': product.category,
                'quantity': product.quantity,
                'min_stock': product.min_stock,
                'unit_cost': unit_cost,
                'stock_value': product.quantity * unit_cost,
                'status': status,
                'cost_missing': product.id not in costs,
            }))
        self.line_ids = commands
        return True

    @api.model
    def _get_current_costs(self, product_ids):
        return self.env['shop.report.mixin']._get_product_costs(product_ids)


class ShopReportStockLine(models.TransientModel):
    _name = 'shop.report.stock.line'
    _description = 'Stock Report Line'
    _order = 'id'

    report_id = fields.Many2one(
        'shop.report.stock', required=True, ondelete='cascade',
    )
    product_id = fields.Many2one('shop.product', string='Product')
    category = fields.Char(string='Category')
    quantity = fields.Float(string='Current Stock')
    min_stock = fields.Float(string='Minimum Stock')
    unit_cost = fields.Float(string='Unit Cost')
    stock_value = fields.Float(string='Stock Value')
    status = fields.Selection(
        selection=lambda self: self.env['shop.product']._fields['stock_status'].selection,
        string='Status',
    )
    cost_missing = fields.Boolean(string='No Purchase Cost')
