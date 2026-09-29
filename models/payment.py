from odoo import models, fields


class ShopPayment(models.Model):
    _name = 'shop.payment'
    _description = 'Shop Payment'
    _order = 'payment_date desc'

    name = fields.Char(
        string='Payment Reference',
        required=True,
        readonly=True,
        default='New'
    )

    order_id = fields.Many2one(
        'shop.sale.order',
        string='Sales Order',
        required=True
    )

    customer_id = fields.Many2one(
        'shop.customer',
        string='Customer',
        related='order_id.customer_id',
        store=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    payment_date = fields.Datetime(
        string='Payment Date',
        default=fields.Datetime.now,
        required=True
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('bank', 'Bank Transfer')
        ],
        string='Payment Method',
        required=True,
        default='cash'
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled')
        ],
        string='Status',
        default='draft'
    )

    notes = fields.Text(string='Notes')

    def action_confirm_payment(self):
        self.write({'state': 'paid'})

    def action_cancel_payment(self):
        self.write({'state': 'cancelled'})

    def action_reset_payment(self):
        self.write({'state': 'draft'})