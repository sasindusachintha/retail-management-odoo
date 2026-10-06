from odoo import models, fields, api
from odoo.exceptions import UserError


class ShopReorderAssistant(models.TransientModel):
    _name = 'shop.reorder.assistant'
    _description = 'Reorder Assistant'

    filter_type = fields.Selection(
        [
            ('low_stock', 'Low Stock Products (Stock <= Min Stock)'),
            ('all', 'All Active Products'),
        ],
        string='Filter Products',
        default='low_stock',
        required=True
    )

    line_ids = fields.One2many(
        'shop.reorder.assistant.line',
        'assistant_id',
        string='Reorder Suggestions'
    )

    total_suggested_count = fields.Integer(
        string='Suggested Products',
        compute='_compute_counts'
    )

    selected_count = fields.Integer(
        string='Selected Products',
        compute='_compute_counts'
    )

    total_estimated_cost = fields.Float(
        string='Total Estimated Cost',
        compute='_compute_counts'
    )

    @api.depends('line_ids', 'line_ids.selected', 'line_ids.estimated_subtotal')
    def _compute_counts(self):
        for record in self:
            record.total_suggested_count = len(record.line_ids)
            selected_lines = record.line_ids.filtered(lambda l: l.selected)
            record.selected_count = len(selected_lines)
            record.total_estimated_cost = sum(selected_lines.mapped('estimated_subtotal'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        domain = [('active', '=', True), ('stock_status', 'in', ['low', 'out'])]
        products = self.env['shop.product'].search(domain, order='quantity asc, name asc')
        lines_cmds = []

        for prod in products:
            rec_lines = self.env['shop.purchase.order.line'].search([
                ('product_id', '=', prod.id),
                ('purchase_id.state', '=', 'received')
            ])

            if rec_lines:
                avg_qty = sum(l.quantity for l in rec_lines) / len(rec_lines)
            else:
                avg_qty = 0.0

            curr = prod.quantity
            min_stk = prod.min_stock or 5.0
            target_stk = min_stk * 2.0
            defic = target_stk - curr

            if avg_qty > 0:
                sug_qty = max(defic, avg_qty)
                note = f"Target Stock ({target_stk:.0f}) - Current ({curr:.0f}) | Avg Purchase Qty ({avg_qty:.0f})"
            else:
                sug_qty = max(defic, min_stk * 2.0 if min_stk > 0 else 10.0)
                note = f"Target Stock ({target_stk:.0f}) - Current Stock ({curr:.0f})"

            if sug_qty <= 0:
                sug_qty = 10.0

            unit_cost = prod.latest_purchase_cost or prod.cost_price
            supp = prod.cheapest_supplier_id or prod.supplier_id

            lines_cmds.append((0, 0, {
                'selected': True,
                'product_id': prod.id,
                'supplier_id': supp.id if supp else False,
                'current_stock': curr,
                'min_stock': min_stk,
                'avg_purchase_qty': avg_qty,
                'suggested_qty': sug_qty,
                'unit_cost': unit_cost,
                'calculation_note': note,
            }))

        res['line_ids'] = lines_cmds
        return res

    def action_generate_suggestions(self):
        self.ensure_one()
        self.line_ids.unlink()

        domain = [('active', '=', True)]
        if self.filter_type == 'low_stock':
            domain.append(('stock_status', 'in', ['low', 'out']))

        products = self.env['shop.product'].search(domain, order='quantity asc, name asc')
        lines_to_create = []

        for prod in products:
            rec_lines = self.env['shop.purchase.order.line'].search([
                ('product_id', '=', prod.id),
                ('purchase_id.state', '=', 'received')
            ])

            if rec_lines:
                avg_qty = sum(l.quantity for l in rec_lines) / len(rec_lines)
            else:
                avg_qty = 0.0

            curr = prod.quantity
            min_stk = prod.min_stock or 5.0
            target_stk = min_stk * 2.0
            defic = target_stk - curr

            if avg_qty > 0:
                sug_qty = max(defic, avg_qty)
                note = f"Target Stock ({target_stk:.0f}) - Current ({curr:.0f}) | Avg Purchase Qty ({avg_qty:.0f})"
            else:
                sug_qty = max(defic, min_stk * 2.0 if min_stk > 0 else 10.0)
                note = f"Target Stock ({target_stk:.0f}) - Current Stock ({curr:.0f})"

            if sug_qty <= 0:
                sug_qty = 10.0

            unit_cost = prod.latest_purchase_cost or prod.cost_price
            supp = prod.cheapest_supplier_id or prod.supplier_id

            lines_to_create.append({
                'assistant_id': self.id,
                'selected': True,
                'product_id': prod.id,
                'supplier_id': supp.id if supp else False,
                'current_stock': curr,
                'min_stock': min_stk,
                'avg_purchase_qty': avg_qty,
                'suggested_qty': sug_qty,
                'unit_cost': unit_cost,
                'calculation_note': note,
            })

        if lines_to_create:
            self.env['shop.reorder.assistant.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shop.reorder.assistant',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_purchase_orders(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError('Please select at least one product to reorder.')

        for line in selected_lines:
            if line.suggested_qty <= 0:
                raise UserError(f'Suggested quantity for "{line.product_id.name}" must be greater than zero.')
            if not line.supplier_id:
                raise UserError(f'Please select a supplier for "{line.product_id.name}".')

        supplier_map = {}
        for line in selected_lines:
            sid = line.supplier_id.id
            if sid not in supplier_map:
                supplier_map[sid] = []
            supplier_map[sid].append(line)

        created_po_ids = []
        for sid, lines in supplier_map.items():
            po_vals = {
                'supplier_id': sid,
                'purchase_date': fields.Datetime.now(),
                'state': 'draft',
                'notes': 'Generated via Reorder Assistant',
                'line_ids': [
                    (0, 0, {
                        'product_id': l.product_id.id,
                        'quantity': l.suggested_qty,
                        'cost_price': l.unit_cost,
                    })
                    for l in lines
                ]
            }
            po = self.env['shop.purchase.order'].create(po_vals)
            created_po_ids.append(po.id)

        if len(created_po_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generated Purchase Order',
                'res_model': 'shop.purchase.order',
                'res_id': created_po_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generated Purchase Orders',
                'res_model': 'shop.purchase.order',
                'domain': [('id', 'in', created_po_ids)],
                'view_mode': 'list,form',
                'target': 'current',
            }


class ShopReorderAssistantLine(models.TransientModel):
    _name = 'shop.reorder.assistant.line'
    _description = 'Reorder Assistant Line'

    assistant_id = fields.Many2one(
        'shop.reorder.assistant',
        string='Assistant',
        required=True,
        ondelete='cascade'
    )

    selected = fields.Boolean(
        string='Select',
        default=True
    )

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True,
        ondelete='cascade'
    )

    supplier_id = fields.Many2one(
        'shop.supplier',
        string='Supplier',
        required=True,
        ondelete='cascade'
    )

    current_stock = fields.Float(
        string='Current Stock',
        readonly=True
    )

    min_stock = fields.Float(
        string='Min Stock',
        readonly=True
    )

    avg_purchase_qty = fields.Float(
        string='Avg Purchase Qty',
        readonly=True
    )

    suggested_qty = fields.Float(
        string='Suggested Qty',
        required=True,
        default=1.0
    )

    unit_cost = fields.Float(
        string='Unit Cost',
        required=True,
        default=0.0
    )

    estimated_subtotal = fields.Float(
        string='Estimated Subtotal',
        compute='_compute_subtotal'
    )

    calculation_note = fields.Char(
        string='Calculation Note',
        readonly=True
    )

    @api.depends('suggested_qty', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.suggested_qty * line.unit_cost
