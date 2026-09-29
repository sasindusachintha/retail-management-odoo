from odoo import models, fields, api
from odoo.exceptions import UserError


class ShopSaleOrder(models.Model):
    _name = 'shop.sale.order'
    _description = 'Shop Sale Order'
    _order = 'order_date desc'

    name = fields.Char(
        string='Order Number',
        required=True,
        readonly=True,
        default='New'
    )

    customer_id = fields.Many2one(
        'shop.customer',
        string='Customer'
    )

    order_date = fields.Datetime(
        string='Order Date',
        default=fields.Datetime.now,
        required=True
    )

    line_ids = fields.One2many(
        'shop.sale.order.line',
        'order_id',
        string='Order Lines'
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals',
        store=True
    )

    discount = fields.Float(
        string='Discount',
        default=0
    )

    amount_total = fields.Float(
        string='Total',
        compute='_compute_totals',
        store=True
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('bank', 'Bank Transfer'),
        ],
        string='Payment Method',
        default='cash'
    )

    amount_paid = fields.Float(
        string='Amount Paid',
        default=0
    )

    change_amount = fields.Float(
        string='Change',
        compute='_compute_change',
        store=True
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled')
        ],
        string='Status',
        default='draft'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'shop.sale.order'
                    ) or 'SO/NEW'
                )

        return super().create(vals_list)

    @api.depends('line_ids.subtotal', 'discount')
    def _compute_totals(self):
        for order in self:
            order.subtotal = sum(
                line.subtotal
                for line in order.line_ids
            )

            discount = max(order.discount, 0)

            order.amount_total = max(
                order.subtotal - discount,
                0
            )

    @api.depends('amount_paid', 'amount_total')
    def _compute_change(self):
        for order in self:
            order.change_amount = max(
                order.amount_paid - order.amount_total,
                0
            )

    def action_confirm(self):
        for order in self:

            # ---------------------------------
            # BASIC VALIDATION
            # ---------------------------------

            if order.state != 'draft':
                raise UserError(
                    'Only draft orders can be completed.'
                )

            if not order.line_ids:
                raise UserError(
                    'You cannot complete an order without products.'
                )

            if order.amount_paid < order.amount_total:
                raise UserError(
                    f'Insufficient payment. '
                    f'Total: {order.amount_total:.2f}, '
                    f'Paid: {order.amount_paid:.2f}'
                )

            # ---------------------------------
            # VALIDATE PRODUCTS AND STOCK
            # ---------------------------------

            for line in order.line_ids:

                if not line.product_id:
                    raise UserError(
                        'Every order line must have a product.'
                    )

                if line.quantity <= 0:
                    raise UserError(
                        f'Quantity for {line.product_id.name} '
                        f'must be greater than 0.'
                    )

                if line.quantity > line.product_id.quantity:
                    raise UserError(
                        f'Not enough stock for '
                        f'{line.product_id.name}. '
                        f'Available: {line.product_id.quantity}'
                    )

            # ---------------------------------
            # DEDUCT STOCK + CREATE MOVEMENT
            # ---------------------------------

            for line in order.line_ids:

                product = line.product_id

                previous_quantity = product.quantity

                new_quantity = (
                    previous_quantity - line.quantity
                )

                # Reduce product stock
                product.quantity = new_quantity

                # Create stock movement
                self.env['shop.stock.movement'].create({
                    'product_id': product.id,
                    'movement_type': 'out',
                    'quantity': line.quantity,
                    'previous_quantity': previous_quantity,
                    'new_quantity': new_quantity,
                    'reason': 'POS Sale',
                    'reference': order.name,
                })

            # ---------------------------------
            # CONFIRM SALE
            # ---------------------------------

            order.state = 'confirmed'

            # ---------------------------------
            # CREATE PAYMENT
            # ---------------------------------

            self.env['shop.payment'].create({
                'name': f'PAY-{order.name}',
                'order_id': order.id,
                'amount': order.amount_total,
                'payment_method': order.payment_method,
                'state': 'paid',
            })

        return True

    def action_cancel(self):
        for order in self:

            if order.state == 'confirmed':
                raise UserError(
                    'A completed sale cannot be cancelled here.'
                )

            order.state = 'cancelled'

    def action_reset_draft(self):
        for order in self:
            order.state = 'draft'


class ShopSaleOrderLine(models.Model):
    _name = 'shop.sale.order.line'
    _description = 'Shop Sale Order Line'

    order_id = fields.Many2one(
        'shop.sale.order',
        string='Order',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True
    )

    quantity = fields.Float(
        string='Quantity',
        default=1,
        required=True
    )

    unit_price = fields.Float(
        string='Unit Price',
        required=True
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.price

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (
                line.quantity * line.unit_price
            )