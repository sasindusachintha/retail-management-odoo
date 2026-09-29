/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ShopDashboard extends Component {
    static template = "shop_management.ShopDashboard";

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loading: true,
            data: {
                today_sales: 0,
                today_orders: 0,
                total_products: 0,
                total_customers: 0,
                low_stock_count: 0,
                low_stock_products: [],
                recent_sales: [],
            },
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;

        try {
            this.state.data = await this.orm.call(
                "shop.dashboard",
                "get_dashboard_data",
                []
            );
        } catch (error) {
            console.error("Dashboard loading error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("en-LK", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value || 0);
    }

    formatDate(date) {
        if (!date) {
            return "";
        }

        const parsed = new Date(date.replace(" ", "T") + "Z");

        return parsed.toLocaleString("en-LK", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    getStockClass(quantity) {
        if (quantity <= 0) {
            return "stock-danger";
        }

        if (quantity <= 5) {
            return "stock-warning";
        }

        return "stock-good";
    }
}

registry.category("actions").add(
    "shop_management.dashboard",
    ShopDashboard
);