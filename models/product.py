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