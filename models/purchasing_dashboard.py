from odoo import models, fields, api


class ShopPurchasingDashboard(models.TransientModel):
    _name = 'shop.purchasing.dashboard'
    _description = 'Purchasing Intelligence Dashboard'

    total_month_purchase = fields.Float(
        string='Total Purchases This Month',
        readonly=True
    )

    active_suppliers_count = fields.Integer(
        string='Active Suppliers',
        readonly=True
    )

    products_purchased_count = fields.Integer(
        string='Products Purchased',
        readonly=True
    )

    reorder_suggestions_count = fields.Integer(
        string='Reorder Suggestions',
        readonly=True
    )

    cost_increase_alerts_count = fields.Integer(
        string='Cost Increase Alerts',
        readonly=True
    )

    top_supplier_id = fields.Many2one(
        'shop.supplier',
        string='Top Supplier',
        readonly=True
    )

    top_supplier_amount = fields.Float(
        string='Top Supplier Spending',
        readonly=True
    )

    highest_cost_increase_product_id = fields.Many2one(
        'shop.product',
        string='Highest Cost Increase Product',
        readonly=True
    )

    highest_cost_increase_percent = fields.Float(
        string='Highest Increase %',
        readonly=True
    )

    top_supplier_line_ids = fields.One2many(
        'shop.purchasing.dashboard.supplier',
        'dashboard_id',
        string='Top Suppliers by Spending'
    )

    top_product_line_ids = fields.One2many(
        'shop.purchasing.dashboard.product',
        'dashboard_id',
        string='Top Purchased Products'
    )

    cost_alert_line_ids = fields.One2many(
        'shop.purchasing.dashboard.alert',
        'dashboard_id',
        string='Cost Alert Details'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        received_pos_this_month = self.env['shop.purchase.order'].search([
            ('state', '=', 'received'),
            ('purchase_date', '>=', month_start)
        ])
        total_month = sum(received_pos_this_month.mapped('total'))

        suppliers = self.env['shop.supplier'].search([('active', '=', True)])
        active_supp_count = len(suppliers)

        rec_lines = self.env['shop.purchase.order.line'].search([
            ('purchase_id.state', '=', 'received')
        ])
        products_purchased = len(set(rec_lines.mapped('product_id.id')))

        low_products = self.env['shop.product'].search([
            ('active', '=', True),
            ('stock_status', 'in', ['low', 'out'])
        ])
        reorder_count = len(low_products)

        supp_spending = {}
        supp_orders = {}
        all_rec_pos = self.env['shop.purchase.order'].search([('state', '=', 'received')])
        for po in all_rec_pos:
            sid = po.supplier_id.id
            if sid:
                supp_spending[sid] = supp_spending.get(sid, 0.0) + po.total
                supp_orders[sid] = supp_orders.get(sid, 0) + 1

        top_supp_id = False
        top_supp_amt = 0.0
        sorted_supps = sorted(supp_spending.items(), key=lambda x: x[1], reverse=True)
        if sorted_supps:
            top_supp_id = sorted_supps[0][0]
            top_supp_amt = sorted_supps[0][1]

        supp_lines_cmds = []
        for sid, amt in sorted_supps[:10]:
            supp_lines_cmds.append((0, 0, {
                'supplier_id': sid,
                'total_spending': amt,
                'order_count': supp_orders.get(sid, 0),
            }))

        prod_qty = {}
        prod_cost = {}
        for line in rec_lines:
            pid = line.product_id.id
            prod_qty[pid] = prod_qty.get(pid, 0.0) + line.quantity
            prod_cost[pid] = prod_cost.get(pid, 0.0) + line.subtotal

        sorted_prods = sorted(prod_qty.items(), key=lambda x: x[1], reverse=True)
        prod_lines_cmds = []
        for pid, qty in sorted_prods[:10]:
            prod_lines_cmds.append((0, 0, {
                'product_id': pid,
                'total_quantity': qty,
                'total_spending': prod_cost.get(pid, 0.0),
            }))

        all_products = self.env['shop.product'].search([('active', '=', True)])
        alert_lines_cmds = []
        highest_prod_id = False
        highest_pct = 0.0

        for prod in all_products:
            if prod.has_cost_increase:
                pct = prod.price_change_percent
                if pct > highest_pct:
                    highest_pct = pct
                    highest_prod_id = prod.id
                alert_lines_cmds.append((0, 0, {
                    'product_id': prod.id,
                    'supplier_id': prod.supplier_id.id if prod.supplier_id else False,
                    'previous_cost': prod.previous_purchase_cost,
                    'current_cost': prod.latest_purchase_cost,
                    'increase_amount': prod.price_change_amount,
                    'increase_percent': pct,
                }))

        res.update({
            'total_month_purchase': total_month,
            'active_suppliers_count': active_supp_count,
            'products_purchased_count': products_purchased,
            'reorder_suggestions_count': reorder_count,
            'cost_increase_alerts_count': len(alert_lines_cmds),
            'top_supplier_id': top_supp_id,
            'top_supplier_amount': top_supp_amt,
            'highest_cost_increase_product_id': highest_prod_id,
            'highest_cost_increase_percent': highest_pct,
            'top_supplier_line_ids': supp_lines_cmds,
            'top_product_line_ids': prod_lines_cmds,
            'cost_alert_line_ids': alert_lines_cmds,
        })
        return res

    def action_generate(self):
        self.ensure_one()
        self.top_supplier_line_ids.unlink()
        self.top_product_line_ids.unlink()
        self.cost_alert_line_ids.unlink()

        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        received_pos_this_month = self.env['shop.purchase.order'].search([
            ('state', '=', 'received'),
            ('purchase_date', '>=', month_start)
        ])
        total_month = sum(received_pos_this_month.mapped('total'))

        suppliers = self.env['shop.supplier'].search([('active', '=', True)])
        active_supp_count = len(suppliers)

        rec_lines = self.env['shop.purchase.order.line'].search([
            ('purchase_id.state', '=', 'received')
        ])
        products_purchased = len(set(rec_lines.mapped('product_id.id')))

        low_products = self.env['shop.product'].search([
            ('active', '=', True),
            ('stock_status', 'in', ['low', 'out'])
        ])
        reorder_count = len(low_products)

        supp_spending = {}
        supp_orders = {}
        all_rec_pos = self.env['shop.purchase.order'].search([('state', '=', 'received')])
        for po in all_rec_pos:
            sid = po.supplier_id.id
            if sid:
                supp_spending[sid] = supp_spending.get(sid, 0.0) + po.total
                supp_orders[sid] = supp_orders.get(sid, 0) + 1

        top_supp_id = False
        top_supp_amt = 0.0
        sorted_supps = sorted(supp_spending.items(), key=lambda x: x[1], reverse=True)
        if sorted_supps:
            top_supp_id = sorted_supps[0][0]
            top_supp_amt = sorted_supps[0][1]

        supp_lines_to_create = []
        for sid, amt in sorted_supps[:10]:
            supp_lines_to_create.append({
                'dashboard_id': self.id,
                'supplier_id': sid,
                'total_spending': amt,
                'order_count': supp_orders.get(sid, 0),
            })
        if supp_lines_to_create:
            self.env['shop.purchasing.dashboard.supplier'].create(supp_lines_to_create)

        prod_qty = {}
        prod_cost = {}
        for line in rec_lines:
            pid = line.product_id.id
            prod_qty[pid] = prod_qty.get(pid, 0.0) + line.quantity
            prod_cost[pid] = prod_cost.get(pid, 0.0) + line.subtotal

        sorted_prods = sorted(prod_qty.items(), key=lambda x: x[1], reverse=True)
        prod_lines_to_create = []
        for pid, qty in sorted_prods[:10]:
            prod_lines_to_create.append({
                'dashboard_id': self.id,
                'product_id': pid,
                'total_quantity': qty,
                'total_spending': prod_cost.get(pid, 0.0),
            })
        if prod_lines_to_create:
            self.env['shop.purchasing.dashboard.product'].create(prod_lines_to_create)

        all_products = self.env['shop.product'].search([('active', '=', True)])
        alerts = []
        highest_prod_id = False
        highest_pct = 0.0

        for prod in all_products:
            if prod.has_cost_increase:
                pct = prod.price_change_percent
                if pct > highest_pct:
                    highest_pct = pct
                    highest_prod_id = prod.id
                alerts.append({
                    'dashboard_id': self.id,
                    'product_id': prod.id,
                    'supplier_id': prod.supplier_id.id if prod.supplier_id else False,
                    'previous_cost': prod.previous_purchase_cost,
                    'current_cost': prod.latest_purchase_cost,
                    'increase_amount': prod.price_change_amount,
                    'increase_percent': pct,
                })

        if alerts:
            self.env['shop.purchasing.dashboard.alert'].create(alerts)

        self.write({
            'total_month_purchase': total_month,
            'active_suppliers_count': active_supp_count,
            'products_purchased_count': products_purchased,
            'reorder_suggestions_count': reorder_count,
            'cost_increase_alerts_count': len(alerts),
            'top_supplier_id': top_supp_id,
            'top_supplier_amount': top_supp_amt,
            'highest_cost_increase_product_id': highest_prod_id,
            'highest_cost_increase_percent': highest_pct,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shop.purchasing.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ShopPurchasingDashboardSupplier(models.TransientModel):
    _name = 'shop.purchasing.dashboard.supplier'
    _description = 'Top Supplier Line'
    _order = 'total_spending desc, id'

    dashboard_id = fields.Many2one('shop.purchasing.dashboard', required=True, ondelete='cascade')
    supplier_id = fields.Many2one('shop.supplier', string='Supplier', required=True)
    total_spending = fields.Float(string='Total Spend')
    order_count = fields.Integer(string='Received POs')


class ShopPurchasingDashboardProduct(models.TransientModel):
    _name = 'shop.purchasing.dashboard.product'
    _description = 'Top Product Line'
    _order = 'total_quantity desc, id'

    dashboard_id = fields.Many2one('shop.purchasing.dashboard', required=True, ondelete='cascade')
    product_id = fields.Many2one('shop.product', string='Product', required=True)
    total_quantity = fields.Float(string='Units Purchased')
    total_spending = fields.Float(string='Total Spend')


class ShopPurchasingDashboardAlert(models.TransientModel):
    _name = 'shop.purchasing.dashboard.alert'
    _description = 'Dashboard Cost Alert Line'
    _order = 'increase_percent desc, id'

    dashboard_id = fields.Many2one('shop.purchasing.dashboard', required=True, ondelete='cascade')
    product_id = fields.Many2one('shop.product', string='Product', required=True)
    supplier_id = fields.Many2one('shop.supplier', string='Supplier')
    previous_cost = fields.Float(string='Previous Cost')
    current_cost = fields.Float(string='Current Cost')
    increase_amount = fields.Float(string='Increase Amount')
    increase_percent = fields.Float(string='Increase %')
