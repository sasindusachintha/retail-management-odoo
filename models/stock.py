from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ShopStockMovement(models.Model):
    _name = 'shop.stock.movement'
    _description = 'Stock Movement'
    _order = 'movement_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New'
    )

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True,
        ondelete='cascade'
    )

    movement_type = fields.Selection(
        [
            ('in', 'Purchase'),
            ('out', 'Sale'),
            ('adjustment', 'Adjustment'),
            ('sale_reversal', 'Sale Reversal'),
            ('purchase_reversal', 'Purchase Reversal'),
        ],
        string='Movement Type',
        required=True
    )

    quantity = fields.Float(
        string='Quantity',
        required=True
    )

    previous_quantity = fields.Float(
        string='Previous Stock',
        readonly=True
    )

    new_quantity = fields.Float(
        string='New Stock',
        readonly=True
    )

    reason = fields.Char(
        string='Reason'
    )

    movement_date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True
    )

    reference = fields.Char(
        string='Reference Document'
    )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'shop.stock.movement'
                    ) or 'STOCK/NEW'
                )

        return super().create(vals_list)


class ShopStockAdjustment(models.TransientModel):
    _name = 'shop.stock.adjustment'
    _description = 'Stock Adjustment'

    product_id = fields.Many2one(
        'shop.product',
        string='Product',
        required=True
    )

    adjustment_type = fields.Selection(
        [
            ('add', 'Add Stock'),
            ('remove', 'Remove Stock'),
            ('set', 'Set to Exact Quantity'),
        ],
        string='Adjustment Type',
        required=True,
        default='add'
    )

    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1
    )

    reason = fields.Char(
        string='Reason',
        required=True
    )

    current_quantity = fields.Float(
        string='Current Stock',
        related='product_id.quantity',
        readonly=True
    )

    new_quantity_preview = fields.Float(
        string='New Stock (Preview)',
        compute='_compute_new_quantity_preview',
        readonly=True
    )

    @api.depends('product_id', 'adjustment_type', 'quantity')
    def _compute_new_quantity_preview(self):
        for record in self:
            if not record.product_id:
                record.new_quantity_preview = 0
                continue
            current = record.product_id.quantity
            if record.adjustment_type == 'add':
                record.new_quantity_preview = current + record.quantity
            elif record.adjustment_type == 'remove':
                record.new_quantity_preview = current - record.quantity
            elif record.adjustment_type == 'set':
                record.new_quantity_preview = record.quantity
            else:
                record.new_quantity_preview = current

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(
                    'Adjustment quantity must be greater than zero.'
                )

    def action_apply(self):
        self.ensure_one()

        if not self.product_id:
            raise UserError('Please select a product.')

        if not self.reason or not self.reason.strip():
            raise UserError('A reason is required for stock adjustments.')

        if self.quantity <= 0:
            raise UserError(
                'Adjustment quantity must be greater than zero.'
            )

        product = self.product_id
        previous_quantity = product.quantity

        if self.adjustment_type == 'add':
            new_quantity = previous_quantity + self.quantity
            movement_qty = self.quantity

        elif self.adjustment_type == 'remove':
            new_quantity = previous_quantity - self.quantity
            movement_qty = self.quantity

            if new_quantity < 0:
                raise UserError(
                    f'Cannot remove {self.quantity} units. '
                    f'Only {previous_quantity} units are available.'
                )

        else:  # set
            new_quantity = self.quantity
            movement_qty = abs(new_quantity - previous_quantity)

            if new_quantity < 0:
                raise UserError(
                    'New stock quantity cannot be negative.'
                )

        product.sudo().write({
            'quantity': new_quantity
        })

        diff = new_quantity - previous_quantity

        self.env['shop.stock.movement'].sudo().create({
            'product_id': product.id,
            'movement_type': 'adjustment',
            'quantity': movement_qty if diff >= 0 else -movement_qty,
            'previous_quantity': previous_quantity,
            'new_quantity': new_quantity,
            'reason': self.reason,
            'reference': f'ADJ/{product.name}',
            'user_id': self.env.user.id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }