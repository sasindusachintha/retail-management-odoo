from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ShopProductCategory(models.Model):
    _name = 'shop.product.category'
    _description = 'Shop Product Category'
    _order = 'name'

    name = fields.Char(
        string='Category Name',
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description'
    )

    product_count = fields.Integer(
        string='Products',
        compute='_compute_product_count'
    )

    def _compute_product_count(self):
        for category in self:
            category.product_count = self.env['shop.product'].search_count([
                ('category_id', '=', category.id),
            ])


class ShopProduct(models.Model):
    _name = 'shop.product'
    _description = 'Shop Product'
    _order = 'name'

    name = fields.Char(
        string='Product Name',
        required=True
    )

    sku = fields.Char(
        string='SKU / Product Code'
    )

    barcode = fields.Char(
        string='Barcode'
    )

    image = fields.Binary(
        string='Product Image',
        attachment=True
    )

    price = fields.Float(
        string='Selling Price',
        required=True
    )

    cost_price = fields.Float(
        string='Purchase Cost',
        default=0
    )

    quantity = fields.Float(
        string='Stock Quantity',
        default=0
    )

    min_stock = fields.Float(
        string='Minimum Stock',
        default=5
    )

    # ------------------------------------------------------------------
    # Category: Many2one to configurable shop.product.category
    # category (Char) kept as legacy fallback — mapped to category_id on
    # first save via _onchange / compute; old records keep working.
    # ------------------------------------------------------------------

    category_id = fields.Many2one(
        'shop.product.category',
        string='Category',
        ondelete='set null'
    )

    # Keep the old char field for backward compat but make it computed
    # so existing views that reference it still work.
    category = fields.Char(
        string='Category (Legacy)',
        compute='_compute_category_char',
        store=True
    )

    @api.depends('category_id')
    def _compute_category_char(self):
        for product in self:
            product.category = (
                product.category_id.name
                if product.category_id
                else ''
            )

    # ------------------------------------------------------------------
    # Supplier link
    # ------------------------------------------------------------------

    supplier_id = fields.Many2one(
        'shop.supplier',
        string='Primary Supplier',
        ondelete='set null'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description'
    )

    stock_status = fields.Selection(
        [
            ('out', 'Out of Stock'),
            ('low', 'Low Stock'),
            ('ok', 'In Stock'),
        ],
        string='Stock Status',
        compute='_compute_stock_status',
        store=True
    )

    def _compute_stock_status(self):
        for product in self:
            if product.quantity <= 0:
                product.stock_status = 'out'
            elif product.quantity <= product.min_stock:
                product.stock_status = 'low'
            else:
                product.stock_status = 'ok'

    # -------------------------------------------------------
    # Constraints
    # -------------------------------------------------------

    @api.constrains('price')
    def _check_price(self):
        for product in self:
            if product.price < 0:
                raise ValidationError(
                    f'Selling price for "{product.name}" cannot be negative.'
                )

    @api.constrains('cost_price')
    def _check_cost_price(self):
        for product in self:
            if product.cost_price < 0:
                raise ValidationError(
                    f'Purchase cost for "{product.name}" cannot be negative.'
                )

    @api.constrains('min_stock')
    def _check_min_stock(self):
        for product in self:
            if product.min_stock < 0:
                raise ValidationError(
                    f'Minimum stock for "{product.name}" cannot be negative.'
                )

    @api.constrains('quantity')
    def _check_quantity_not_negative(self):
        """Last-resort guard: prevents any write that sets quantity < 0."""
        for product in self:
            if product.quantity < 0:
                raise ValidationError(
                    f'Stock quantity for "{product.name}" cannot be negative.'
                )

    @api.constrains('barcode')
    def _check_barcode_unique(self):
        for product in self:
            if not product.barcode:
                continue
            duplicate = self.search([
                ('barcode', '=', product.barcode),
                ('id', '!=', product.id),
                ('active', 'in', [True, False]),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f'Barcode "{product.barcode}" is already used by '
                    f'product "{duplicate.name}". '
                    f'Barcodes must be unique across all products.'
                )

    @api.constrains('sku')
    def _check_sku_unique(self):
        for product in self:
            if not product.sku:
                continue
            duplicate = self.search([
                ('sku', '=', product.sku),
                ('id', '!=', product.id),
                ('active', 'in', [True, False]),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f'SKU "{product.sku}" is already used by '
                    f'product "{duplicate.name}". '
                    f'SKUs must be unique across all products.'
                )

    # ------------------------------------------------------------------
    # PHASE 5: Advanced Purchasing & Supplier Intelligence
    # ------------------------------------------------------------------

    purchase_line_ids = fields.One2many(
        'shop.purchase.order.line',
        'product_id',
        string='Purchase History'
    )

    latest_purchase_cost = fields.Float(
        string='Latest Purchase Cost',
        compute='_compute_purchase_cost_history'
    )

    previous_purchase_cost = fields.Float(
        string='Previous Purchase Cost',
        compute='_compute_purchase_cost_history'
    )

    price_change_amount = fields.Float(
        string='Cost Increase Amount',
        compute='_compute_purchase_cost_history'
    )

    price_change_percent = fields.Float(
        string='Cost Increase %',
        compute='_compute_purchase_cost_history'
    )

    cost_increase_threshold = fields.Float(
        string='Alert Threshold (%)',
        default=5.0
    )

    has_cost_increase = fields.Boolean(
        string='Has Cost Increase Alert',
        compute='_compute_purchase_cost_history',
        search='_search_has_cost_increase'
    )

    cost_increase_alert = fields.Char(
        string='Cost Increase Warning',
        compute='_compute_purchase_cost_history'
    )

    cheapest_supplier_id = fields.Many2one(
        'shop.supplier',
        string='Recommended / Cheapest Supplier',
        compute='_compute_supplier_comparison'
    )

    best_purchase_cost = fields.Float(
        string='Lowest Known Recent Cost',
        compute='_compute_supplier_comparison'
    )

    most_expensive_supplier_id = fields.Many2one(
        'shop.supplier',
        string='Most Expensive Supplier',
        compute='_compute_supplier_comparison'
    )

    potential_savings = fields.Float(
        string='Potential Savings per Unit',
        compute='_compute_supplier_comparison'
    )

    supplier_recommendation_text = fields.Text(
        string='Supplier Recommendation',
        compute='_compute_supplier_comparison'
    )

    supplier_comparison_ids = fields.One2many(
        'shop.product.supplier.comparison',
        'product_id',
        string='Supplier Cost Comparison',
        compute='_compute_supplier_comparison_lines'
    )

    @api.depends('cost_price', 'cost_increase_threshold', 'purchase_line_ids.cost_price', 'purchase_line_ids.purchase_id.state')
    def _compute_purchase_cost_history(self):
        for product in self:
            rec_lines = self.env['shop.purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('purchase_id.state', '=', 'received')
            ]).sorted(key=lambda l: (l.purchase_id.purchase_date or fields.Datetime.now(), l.id), reverse=True)

            if rec_lines:
                latest_cost = rec_lines[0].cost_price
                prev_line = False
                for line in rec_lines[1:]:
                    if line.purchase_id != rec_lines[0].purchase_id:
                        prev_line = line
                        break
                if not prev_line and len(rec_lines) > 1:
                    prev_line = rec_lines[1]

                prev_cost = prev_line.cost_price if prev_line else 0.0
            else:
                latest_cost = product.cost_price
                prev_cost = 0.0

            product.latest_purchase_cost = latest_cost
            product.previous_purchase_cost = prev_cost

            if prev_cost > 0:
                diff = latest_cost - prev_cost
                pct = (diff / prev_cost) * 100.0
            else:
                diff = 0.0
                pct = 0.0

            product.price_change_amount = diff
            product.price_change_percent = pct

            threshold = product.cost_increase_threshold or 5.0
            is_increase = (pct >= threshold) and (prev_cost > 0)
            product.has_cost_increase = is_increase

            if is_increase:
                product.cost_increase_alert = (
                    f"⚠ Purchase cost increased by {pct:.2f}% "
                    f"(Rs. {prev_cost:,.2f} → Rs. {latest_cost:,.2f})"
                )
            else:
                product.cost_increase_alert = ""

    def _search_has_cost_increase(self, operator, value):
        products = self.search([])
        matching_ids = []
        for p in products:
            if (p.has_cost_increase and value) or (
                not p.has_cost_increase and not value
            ):
                matching_ids.append(p.id)
        return [('id', 'in', matching_ids)]

    @api.depends('supplier_id', 'cost_price', 'purchase_line_ids.cost_price', 'purchase_line_ids.purchase_id.state')
    def _compute_supplier_comparison(self):
        for product in self:
            rec_lines = self.env['shop.purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('purchase_id.state', '=', 'received')
            ]).sorted(key=lambda l: (l.purchase_id.purchase_date or fields.Datetime.now(), l.id), reverse=True)

            supplier_map = {}
            for line in rec_lines:
                sid = line.supplier_id.id
                if not sid:
                    continue
                if sid not in supplier_map:
                    supplier_map[sid] = []
                supplier_map[sid].append(line)

            if (
                product.supplier_id
                and product.supplier_id.id not in supplier_map
            ):
                supplier_map[product.supplier_id.id] = []

            min_cost = None
            max_cost = None
            cheapest_supp = False
            expensive_supp = False

            for sid, lines in supplier_map.items():
                supp_obj = self.env['shop.supplier'].browse(sid)
                if lines:
                    last_cost = lines[0].cost_price
                else:
                    last_cost = product.cost_price

                if min_cost is None or (
                    last_cost > 0 and last_cost < min_cost
                ):
                    min_cost = last_cost
                    cheapest_supp = supp_obj
                if max_cost is None or last_cost > max_cost:
                    max_cost = last_cost
                    expensive_supp = supp_obj

            supp_rec = cheapest_supp or product.supplier_id or False
            exp_rec = expensive_supp or product.supplier_id or False

            product.cheapest_supplier_id = supp_rec
            product.most_expensive_supplier_id = exp_rec
            product.best_purchase_cost = (
                min_cost if min_cost is not None else product.cost_price
            )

            curr_cost = product.latest_purchase_cost or product.cost_price
            if (
                product.best_purchase_cost
                and curr_cost > product.best_purchase_cost
            ):
                product.potential_savings = (
                    curr_cost - product.best_purchase_cost
                )
            else:
                product.potential_savings = 0.0

            if product.cheapest_supplier_id:
                rec_name = product.cheapest_supplier_id.name
                rec_cost = product.best_purchase_cost
                prev_cost_val = product.previous_purchase_cost
                latest_cost_val = product.latest_purchase_cost
                product.supplier_recommendation_text = (
                    f"Recommended Supplier: {rec_name}\n"
                    f"Lowest Known Recent Cost: Rs. {rec_cost:,.2f}\n"
                    f"Latest Purchase Cost: Rs. {latest_cost_val:,.2f}\n"
                    f"Previous Purchase Cost: Rs. {prev_cost_val:,.2f}\n"
                    f"Potential Saving: Rs. {product.potential_savings:,.2f}/unit"
                )
            else:
                product.supplier_recommendation_text = (
                    "No supplier history available."
                )

    def _compute_supplier_comparison_lines(self):
        for product in self:
            existing = self.env['shop.product.supplier.comparison'].search([
                ('product_id', '=', product.id)
            ])
            existing.unlink()

            rec_lines = self.env['shop.purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('purchase_id.state', '=', 'received')
            ]).sorted(key=lambda l: (l.purchase_id.purchase_date or fields.Datetime.now(), l.id), reverse=True)

            supplier_map = {}
            for line in rec_lines:
                sid = line.supplier_id.id
                if not sid:
                    continue
                if sid not in supplier_map:
                    supplier_map[sid] = []
                supplier_map[sid].append(line)

            if (
                product.supplier_id
                and product.supplier_id.id not in supplier_map
            ):
                supplier_map[product.supplier_id.id] = []

            comp_lines = []
            min_cost = product.best_purchase_cost

            for sid, lines in supplier_map.items():
                if lines:
                    last_cost = lines[0].cost_price
                    prev_cost = lines[1].cost_price if len(lines) > 1 else 0.0
                    tot_qty = sum(l.quantity for l in lines)
                    tot_spent = sum(l.subtotal for l in lines)
                else:
                    last_cost = product.cost_price
                    prev_cost = 0.0
                    tot_qty = 0.0
                    tot_spent = 0.0

                comp_lines.append({
                    'product_id': product.id,
                    'supplier_id': sid,
                    'latest_cost': last_cost,
                    'previous_cost': prev_cost,
                    'total_quantity': tot_qty,
                    'total_spent': tot_spent,
                    'is_cheapest': (min_cost and last_cost == min_cost),
                })

            if comp_lines:
                created = self.env['shop.product.supplier.comparison'].create(comp_lines)
                product.supplier_comparison_ids = created
            else:
                product.supplier_comparison_ids = False