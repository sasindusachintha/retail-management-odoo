from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ShopPurchaseOrder(models.Model):
    _name = 'shop.purchase.order'
    _description = 'Purchase Order'
    _order = 'purchase_date desc'

    name = fields.Char(
        string='Purchase Number',
        required=True,
        readonly=True,
        default='New'
    )

    supplier_id = fields.Many2one(
        'shop.supplier',
        string='Supplier',
        required=True
    )

    purchase_date = fields.Datetime(
        string='Purchase Date',
        default=fields.Datetime.now,
        required=True
    )

    line_ids = fields.One2many(
        'shop.purchase.order.line',
        'purchase_id',
        string='Purchase Lines'
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_total',
        store=True
    )

    total = fields.Float(
        string='Total',
        compute='_compute_total',
        store=True
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('received', 'Received'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'shop.purchase.order'
                    ) or 'PO/NEW'
                )

        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for purchase in self:
            purchase.subtotal = sum(
                line.subtotal
                for line in purchase.line_ids
            )

            purchase.total = purchase.subtotal

    def action_receive(self):
        for purchase in self:

            if purchase.state != 'draft':
                raise UserError(
                    'Only draft purchases can be received.'
                )

            if not purchase.line_ids:
                raise UserError(
                    'You cannot receive a purchase without products.'
                )

            for line in purchase.line_ids:

                if not line.product_id:
                    raise UserError(
                        'Every purchase line must have a product.'
                    )

                if line.quantity <= 0:
                    raise UserError(
                        f'Quantity for {line.product_id.name} '
                        f'must be greater than 0.'
                    )

                if line.cost_price < 0:
                    raise UserError(
                        f'Cost price for {line.product_id.name} '
                        f'cannot be negative.'
                    )

            for line in purchase.line_ids:

                product = line.product_id

                previous_quantity = product.quantity

                new_quantity = (
                    previous_quantity + line.quantity
                )

                product.write({
                    'quantity': new_quantity
                })

                self.env['shop.stock.movement'].create({
                    'product_id': product.id,
                    'movement_type': 'in',
                    'quantity': line.quantity,
                    'previous_quantity': previous_quantity,
                    'new_quantity': new_quantity,
                    'reason': 'Purchase Received',
                    'reference': purchase.name,
                    'user_id': self.env.user.id,
                })

            purchase.state = 'received'

        return True

    def action_cancel(self):
        for purchase in self:

            if purchase.state == 'cancelled':
                raise UserError(
                    f'Purchase {purchase.name} is already cancelled.'
                )

            if purchase.state == 'received':
                # Only Managers can reverse a received purchase (Rule #6)
                if not self.env.user.has_group(
                    'shop_management.group_shop_manager'
                ):
                    raise UserError(
                        'A received purchase cannot be cancelled. '
                        'Contact a Shop Manager to reverse it.'
                    )

                # Reverse stock for each line (Rule #6 / #12)
                for line in purchase.line_ids:
                    product = line.product_id
                    previous_quantity = product.quantity
                    new_quantity = previous_quantity - line.quantity

                    if new_quantity < 0:
                        raise UserError(
                            f'Cannot reverse purchase: reversing "{product.name}" '
                            f'would result in negative stock '
                            f'(available: {previous_quantity:.0f}, '
                            f'to remove: {line.quantity:.0f}).'
                        )

                    product.write({'quantity': new_quantity})

                    self.env['shop.stock.movement'].create({
                        'product_id': product.id,
                        'movement_type': 'purchase_reversal',
                        'quantity': line.quantity,
                        'previous_quantity': previous_quantity,
                        'new_quantity': new_quantity,
                        'reason': 'Purchase Reversed',
                        'reference': purchase.name,
                        'user_id': self.env.user.id,
                    })

            purchase.write({'state': 'cancelled'})

    def action_reset_draft(self):
        for purchase in self:

            if purchase.state == 'received':
                raise UserError(
                    'A received purchase cannot be reset to draft. '
                    'Use Cancel instead.'
                )

            purchase.write({'state': 'draft'})


class ShopPurchaseOrderLine(models.Model):
    _name = 'shop.purchase.order.line'
    _description = 'Purchase Order Line'

    purchase_id = fields.Many2one(
        'shop.purchase.order',
        string='Purchase',
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
        required=True,
        default=1
    )

    cost_price = fields.Float(
        string='Cost Price',
        required=True,
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
            self.cost_price = self.product_id.price

    @api.depends('quantity', 'cost_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (
                line.quantity * line.cost_price
            )

    # -------------------------------------------------------
    # PHASE 2: Purchase line validation constraints (Rule #15)
    # -------------------------------------------------------

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    f'Quantity for "{line.product_id.name}" '
                    f'must be greater than 0.'
                )

    @api.constrains('cost_price')
    def _check_cost_price(self):
        for line in self:
            if line.cost_price < 0:
                raise ValidationError(
                    f'Cost price for "{line.product_id.name}" '
                    f'cannot be negative.'
                )