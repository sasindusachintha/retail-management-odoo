from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


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
            # GUARD: Idempotency / duplicate click protection (Rule #16)
            # ---------------------------------

            if order.state != 'draft':
                raise UserError(
                    'Only draft orders can be completed. '
                    f'This order is already "{order.state}".'
                )

            if not order.line_ids:
                raise UserError(
                    'You cannot complete an order without products.'
                )

            # ---------------------------------
            # VALIDATE PAYMENT (Rule #7 / #9)
            # ---------------------------------

            if order.amount_paid < order.amount_total:
                raise UserError(
                    f'Insufficient payment. '
                    f'Total: {order.amount_total:.2f}, '
                    f'Paid: {order.amount_paid:.2f}'
                )

            # ---------------------------------
            # VALIDATE SALE LINES (Rule #14)
            # ---------------------------------

            for line in order.line_ids:

                if not line.product_id:
                    raise UserError(
                        'Every order line must have a product.'
                    )

                if not line.product_id.active:
                    raise UserError(
                        f'Product "{line.product_id.name}" is inactive '
                        f'and cannot be sold.'
                    )

                if line.quantity <= 0:
                    raise UserError(
                        f'Quantity for "{line.product_id.name}" '
                        f'must be greater than 0.'
                    )

                if line.unit_price < 0:
                    raise UserError(
                        f'Unit price for "{line.product_id.name}" '
                        f'cannot be negative.'
                    )

                if line.discount < 0:
                    raise UserError(
                        f'Discount for "{line.product_id.name}" '
                        f'cannot be negative.'
                    )

                if line.discount > (line.quantity * line.unit_price):
                    raise UserError(
                        f'Discount for "{line.product_id.name}" '
                        f'cannot exceed total line price.'
                    )

            # ---------------------------------
            # CONCURRENCY: Lock product rows before reading stock (Rule #20)
            # SELECT ... FOR UPDATE prevents two cashiers from overselling.
            # ---------------------------------

            product_ids = order.line_ids.mapped('product_id').ids
            self.env.cr.execute(
                'SELECT id FROM shop_product WHERE id = ANY(%s) FOR UPDATE NOWAIT',
                (product_ids,)
            )

            # ---------------------------------
            # VALIDATE STOCK (Rule #1 / #14)
            # ---------------------------------

            for line in order.line_ids:

                # Re-read from DB after lock to get current committed value
                available = line.product_id.quantity

                if line.quantity > available:
                    raise UserError(
                        f'Insufficient stock for "{line.product_id.name}". '
                        f'Available: {available:.0f}, '
                        f'Requested: {line.quantity:.0f}.'
                    )

            # ---------------------------------
            # ATOMIC: DEDUCT STOCK + CREATE MOVEMENTS (Rules #2 / #4 / #12)
            # All operations within this method share the same DB transaction.
            # Any exception triggers a full rollback.
            # ---------------------------------

            for line in order.line_ids:

                product = line.product_id

                previous_quantity = product.quantity
                new_quantity = previous_quantity - line.quantity

                # sudo() allows Cashier role to write product stock
                product.sudo().write({'quantity': new_quantity})

                self.env['shop.stock.movement'].sudo().create({
                    'product_id': product.id,
                    'movement_type': 'out',
                    'quantity': line.quantity,
                    'previous_quantity': previous_quantity,
                    'new_quantity': new_quantity,
                    'reason': 'POS Sale',
                    'reference': order.name,
                    'user_id': self.env.user.id,
                })

            # ---------------------------------
            # CONFIRM SALE STATE (Rule #2)
            # ---------------------------------

            order.write({'state': 'confirmed'})

            # ---------------------------------
            # CREATE PAYMENT RECORD (Rules #2 / #8 / #18)
            # Guard against duplicate payments if payment records exist already.
            # ---------------------------------

            existing_payment = self.env['shop.payment'].sudo().search([
                ('order_id', '=', order.id),
                ('state', '=', 'paid'),
            ], limit=1)

            if not existing_payment:
                self.env['shop.payment'].sudo().create({
                    'name': f'PAY-{order.name}',
                    'order_id': order.id,
                    'amount': order.amount_total,
                    'payment_method': order.payment_method,
                    'state': 'paid',
                })

        return True

    @api.model
    def create_pos_sale(self, pos_data):
        """Create and confirm a POS sale atomically in a single RPC transaction."""
        if not pos_data or not pos_data.get('lines'):
            raise UserError('You cannot complete an order without products.')

        customer_id = pos_data.get('customer_id') or False
        order_discount = float(pos_data.get('discount') or 0.0)
        payment_method = pos_data.get('payment_method') or 'cash'
        amount_paid = float(pos_data.get('amount_paid') or 0.0)

        line_vals_list = []
        for line in pos_data.get('lines', []):
            product_id = line.get('product_id')
            qty = float(line.get('quantity') or 0)
            unit_price = float(line.get('unit_price') or 0)
            line_disc = float(line.get('discount') or 0)

            if not product_id:
                raise UserError('Every order line must specify a product.')
            if qty <= 0:
                raise UserError('Product quantity must be greater than 0.')

            line_vals_list.append((0, 0, {
                'product_id': product_id,
                'quantity': qty,
                'unit_price': unit_price,
                'discount': line_disc,
            }))

        order = self.create({
            'customer_id': customer_id,
            'discount': order_discount,
            'payment_method': payment_method,
            'amount_paid': amount_paid,
            'line_ids': line_vals_list,
        })

        # Process multi-payment breakdown if provided
        payments_list = pos_data.get('payments')
        if payments_list and isinstance(payments_list, list):
            for p_info in payments_list:
                p_amount = float(p_info.get('amount') or 0)
                p_method = p_info.get('method') or payment_method
                if p_amount > 0:
                    self.env['shop.payment'].sudo().create({
                        'name': f'PAY-{order.name}-{p_method.upper()}',
                        'order_id': order.id,
                        'amount': p_amount,
                        'payment_method': p_method,
                        'state': 'paid',
                    })

        # Confirm sale (deducts stock, logs movement, completes payment)
        order.action_confirm()

        return {
            'id': order.id,
            'name': order.name,
            'order_date': fields.Datetime.to_string(order.order_date),
            'customer_name': order.customer_id.name if order.customer_id else 'Walk-in Customer',
            'cashier_name': self.env.user.name,
            'subtotal': order.subtotal,
            'discount': order.discount,
            'amount_total': order.amount_total,
            'amount_paid': order.amount_paid,
            'change_amount': order.change_amount,
            'payment_method': order.payment_method,
            'lines': [
                {
                    'product_id': l.product_id.id,
                    'product_name': l.product_id.name,
                    'quantity': l.quantity,
                    'unit_price': l.unit_price,
                    'discount': l.discount,
                    'subtotal': l.subtotal,
                }
                for l in order.line_ids
            ]
        }

    def action_cancel(self):
        """Cancel a sale. For confirmed sales, reverse stock and payment."""
        for order in self:

            if order.state == 'cancelled':
                raise UserError(
                    f'Order {order.name} is already cancelled.'
                )

            if order.state == 'confirmed':
                # Only Managers can cancel a confirmed sale (Rule #5)
                if not self.env.user.has_group(
                    'shop_management.group_shop_manager'
                ):
                    raise UserError(
                        'Only a Shop Manager can cancel a completed sale.'
                    )

                # -- Return stock for each sold line (Rule #5 / #12) --
                for line in order.line_ids:
                    product = line.product_id
                    previous_quantity = product.quantity
                    new_quantity = previous_quantity + line.quantity

                    product.sudo().write({'quantity': new_quantity})

                    self.env['shop.stock.movement'].sudo().create({
                        'product_id': product.id,
                        'movement_type': 'sale_reversal',
                        'quantity': line.quantity,
                        'previous_quantity': previous_quantity,
                        'new_quantity': new_quantity,
                        'reason': 'Sale Reversed',
                        'reference': order.name,
                        'user_id': self.env.user.id,
                    })

                # -- Reverse payment record (Rule #5) --
                payments = self.env['shop.payment'].sudo().search([
                    ('order_id', '=', order.id),
                    ('state', '=', 'paid'),
                ])
                payments.write({'state': 'cancelled'})

            order.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Reset to draft — only allowed from cancelled state, never from confirmed."""
        for order in self:
            if order.state == 'confirmed':
                raise UserError(
                    'A completed sale cannot be reset to draft. '
                    'Use Cancel instead.'
                )
            order.write({'state': 'draft'})


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

    discount = fields.Float(
        string='Discount',
        default=0
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

    @api.depends('quantity', 'unit_price', 'discount')
    def _compute_subtotal(self):
        for line in self:
            discount = max(line.discount, 0)
            gross = line.quantity * line.unit_price
            line.subtotal = max(gross - discount, 0)

    # -------------------------------------------------------
    # PHASE 2: Sale line validation constraints (Rule #14)
    # -------------------------------------------------------

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    f'Quantity for "{line.product_id.name}" '
                    f'must be greater than 0.'
                )

    @api.constrains('unit_price')
    def _check_unit_price(self):
        for line in self:
            if line.unit_price < 0:
                raise ValidationError(
                    f'Unit price for "{line.product_id.name}" '
                    f'cannot be negative.'
                )

    @api.constrains('discount')
    def _check_discount(self):
        for line in self:
            if line.discount < 0:
                raise ValidationError(
                    f'Discount for "{line.product_id.name}" '
                    f'cannot be negative.'
                )
            if line.discount > (line.quantity * line.unit_price):
                raise ValidationError(
                    f'Discount for "{line.product_id.name}" '
                    f'cannot exceed the line gross total.'
                )