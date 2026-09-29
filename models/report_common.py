from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models


class ShopReportMixin(models.AbstractModel):
    """Shared date handling and cost lookup for the Shop Management reports."""
    _name = 'shop.report.mixin'
    _description = 'Shop Report Mixin'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    def _invalid_range_notification(self):
        """Return a warning notification action if the date range is invalid."""
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid date range'),
                    'message': _('Date From must be on or before Date To.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return False

    def _get_utc_range(self):
        """Return (start, end) as naive UTC datetimes.

        start is the first instant of Date From and end is the first instant
        of the day AFTER Date To (both in the user's timezone), so a domain of
        ``>= start`` and ``< end`` covers the whole Date To day.
        """
        self.ensure_one()
        tz = pytz.timezone(
            self.env.context.get('tz') or self.env.user.tz or 'UTC'
        )
        start_local = tz.localize(datetime.combine(self.date_from, time.min))
        end_local = tz.localize(
            datetime.combine(self.date_to + timedelta(days=1), time.min)
        )
        return (
            start_local.astimezone(pytz.utc).replace(tzinfo=None),
            end_local.astimezone(pytz.utc).replace(tzinfo=None),
        )

    @api.model
    def _get_product_costs(self, product_ids, before=None):
        """Weighted-average unit cost per product from RECEIVED purchases.

        shop.product has no cost field, so the real cost source is the
        cost_price on received purchase lines. If ``before`` (naive UTC
        datetime) is given, purchases received up to that moment are
        preferred; products with no earlier purchase fall back to the
        all-time average. Products never purchased are absent from the result.
        """
        if not product_ids:
            return {}
        Line = self.env['shop.purchase.order.line']
        base = [
            ('purchase_id.state', '=', 'received'),
            ('product_id', 'in', list(product_ids)),
        ]

        def averages(extra):
            groups = Line._read_group(
                base + extra, ['product_id'],
                ['quantity:sum', 'subtotal:sum'],
            )
            return {
                product.id: subtotal / qty
                for product, qty, subtotal in groups if qty
            }

        costs = averages([])
        if before:
            costs.update(averages([('purchase_id.purchase_date', '<', before)]))
        return costs
