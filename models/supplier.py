from odoo import models, fields


class ShopSupplier(models.Model):
    _name = 'shop.supplier'
    _description = 'Shop Supplier'
    _order = 'name'

    name = fields.Char(
        string='Supplier Name',
        required=True
    )

    phone = fields.Char(
        string='Phone'
    )

    email = fields.Char(
        string='Email'
    )

    address = fields.Text(
        string='Address'
    )

    notes = fields.Text(
        string='Notes'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    product_ids = fields.One2many(
        'shop.product',
        'supplier_id',
        string='Products'
    )

    total_purchase_value = fields.Float(
        string='Total Purchase Value',
        compute='_compute_supplier_stats'
    )

    purchase_order_count = fields.Integer(
        string='Purchase Orders',
        compute='_compute_supplier_stats'
    )

    received_purchase_count = fields.Integer(
        string='Received Purchases',
        compute='_compute_supplier_stats'
    )

    last_purchase_date = fields.Datetime(
        string='Last Purchase Date',
        compute='_compute_supplier_stats'
    )

    products_supplied_count = fields.Integer(
        string='Products Supplied',
        compute='_compute_supplier_stats'
    )

    avg_purchase_value = fields.Float(
        string='Average Purchase Value',
        compute='_compute_supplier_stats'
    )

    supplier_product_line_ids = fields.One2many(
        'shop.supplier.product.line',
        'supplier_id',
        string='Supplier Product History',
        compute='_compute_supplier_product_lines'
    )

    def _compute_supplier_stats(self):
        for supplier in self:
            po_records = self.env['shop.purchase.order'].search([
                ('supplier_id', '=', supplier.id)
            ])
            received_pos = po_records.filtered(lambda r: r.state == 'received')

            supplier.purchase_order_count = len(po_records)
            supplier.received_purchase_count = len(received_pos)
            supplier.total_purchase_value = sum(received_pos.mapped('total'))

            if received_pos:
                supplier.last_purchase_date = max(received_pos.mapped('purchase_date'))
                supplier.avg_purchase_value = (
                    supplier.total_purchase_value / len(received_pos)
                )
            else:
                supplier.last_purchase_date = False
                supplier.avg_purchase_value = 0.0

            received_lines = self.env['shop.purchase.order.line'].search([
                ('purchase_id.supplier_id', '=', supplier.id),
                ('purchase_id.state', '=', 'received')
            ])
            purchased_product_ids = set(received_lines.mapped('product_id.id'))
            assigned_product_ids = set(supplier.product_ids.ids)
            supplier.products_supplied_count = len(
                purchased_product_ids | assigned_product_ids
            )

    def _compute_supplier_product_lines(self):
        for supplier in self:
            existing_lines = self.env['shop.supplier.product.line'].search([
                ('supplier_id', '=', supplier.id)
            ])
            existing_lines.unlink()

            lines_to_create = []

            purchase_lines = self.env['shop.purchase.order.line'].search([
                ('purchase_id.supplier_id', '=', supplier.id),
                ('purchase_id.state', '=', 'received')
            ]).sorted(key=lambda l: (l.purchase_id.purchase_date or fields.Datetime.now(), l.id), reverse=True)

            product_map = {}
            for line in purchase_lines:
                pid = line.product_id.id
                if pid not in product_map:
                    product_map[pid] = []
                product_map[pid].append(line)

            for prod in supplier.product_ids:
                if prod.id not in product_map:
                    product_map[prod.id] = []

            for pid, lines in product_map.items():
                if lines:
                    last_line = lines[0]
                    prev_cost = lines[1].cost_price if len(lines) > 1 else 0.0
                    last_date = last_line.purchase_date
                    last_cost = last_line.cost_price
                    total_qty = sum(l.quantity for l in lines)
                    total_amt = sum(l.subtotal for l in lines)
                else:
                    product_obj = self.env['shop.product'].browse(pid)
                    last_date = False
                    last_cost = product_obj.cost_price
                    prev_cost = 0.0
                    total_qty = 0.0
                    total_amt = 0.0

                lines_to_create.append({
                    'supplier_id': supplier.id,
                    'product_id': pid,
                    'last_purchase_date': last_date,
                    'last_purchase_cost': last_cost,
                    'previous_purchase_cost': prev_cost,
                    'total_quantity': total_qty,
                    'total_amount': total_amt,
                })

            if lines_to_create:
                created = self.env['shop.supplier.product.line'].create(
                    lines_to_create
                )
                supplier.supplier_product_line_ids = created
            else:
                supplier.supplier_product_line_ids = False
