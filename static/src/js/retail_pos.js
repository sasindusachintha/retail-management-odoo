/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class RetailPOS extends Component {

    static template = "shop_management.RetailPOS";

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            products: [],
            customers: [],
            cart: [],

            search: "",
            category: "all",

            customer_id: "",
            discount: 0,

            payment_method: "cash",
            amount_paid: 0,

            processing: false,
            completedOrder: null,
        });

        this.loadData();
    }

    async loadData() {

        this.state.products = await this.orm.searchRead(
            "shop.product",
            [["active", "=", true]],
            [
                "name",
                "price",
                "quantity",
                "category"
            ]
        );

        this.state.customers = await this.orm.searchRead(
            "shop.customer",
            [["active", "=", true]],
            [
                "name",
                "phone"
            ]
        );
    }

    get categories() {

        const categories = this.state.products
            .map(product => product.category)
            .filter(category => category);

        return [...new Set(categories)];
    }

    get filteredProducts() {

        const search = this.state.search
            .toLowerCase()
            .trim();

        return this.state.products.filter(product => {

            const matchesSearch =
                !search ||
                product.name.toLowerCase().includes(search);

            const matchesCategory =
                this.state.category === "all" ||
                product.category === this.state.category;

            return matchesSearch && matchesCategory;
        });
    }

    addProduct(product) {

        if (product.quantity <= 0) {
            alert(
                `${product.name} is out of stock.`
            );
            return;
        }

        const existing = this.state.cart.find(
            item => item.product_id === product.id
        );

        if (existing) {

            if (existing.quantity < product.quantity) {
                existing.quantity++;
            }

            return;
        }

        this.state.cart.push({
            product_id: product.id,
            name: product.name,
            price: product.price,
            available: product.quantity,
            quantity: 1,
        });
    }

    increase(item) {

        if (item.quantity < item.available) {
            item.quantity++;
        }
    }

    decrease(item) {

        if (item.quantity > 1) {
            item.quantity--;
        } else {
            this.removeItem(item);
        }
    }

    removeItem(item) {

        const index = this.state.cart.indexOf(item);

        if (index !== -1) {
            this.state.cart.splice(index, 1);
        }
    }

    clearCart() {

        this.state.cart.splice(0);

        this.state.discount = 0;
        this.state.amount_paid = 0;
    }

    get subtotal() {

        return this.state.cart.reduce(
            (total, item) =>
                total + item.price * item.quantity,
            0
        );
    }

    get discount() {

        const discount = Number(
            this.state.discount
        ) || 0;

        return Math.min(
            Math.max(discount, 0),
            this.subtotal
        );
    }

    get total() {

        return Math.max(
            this.subtotal - this.discount,
            0
        );
    }

    get change() {

        const paid =
            Number(this.state.amount_paid) || 0;

        return Math.max(
            paid - this.total,
            0
        );
    }

    get canCompleteSale() {

        const paid =
            Number(this.state.amount_paid) || 0;

        return (
            this.state.cart.length > 0 &&
            paid >= this.total &&
            !this.state.processing
        );
    }

    async completeSale() {

        if (!this.state.cart.length) {
            alert("Cart is empty.");
            return;
        }

        const paid =
            Number(this.state.amount_paid) || 0;

        if (paid < this.total) {
            alert(
                `Payment is insufficient.\n\n` +
                `Total: Rs. ${this.total.toFixed(2)}\n` +
                `Paid: Rs. ${paid.toFixed(2)}`
            );
            return;
        }

        this.state.processing = true;

        try {

            const orderIds = await this.orm.create(
                "shop.sale.order",
                [{
                    customer_id:
                        this.state.customer_id
                        ? Number(this.state.customer_id)
                        : false,

                    discount: this.discount,

                    payment_method:
                        this.state.payment_method,

                    amount_paid: paid,
                }]
            );

            const orderId =
                Array.isArray(orderIds)
                    ? orderIds[0]
                    : orderIds;

            for (const item of this.state.cart) {

                await this.orm.create(
                    "shop.sale.order.line",
                    [{
                        order_id: orderId,
                        product_id: item.product_id,
                        quantity: item.quantity,
                        unit_price: item.price,
                    }]
                );
            }

            await this.orm.call(
                "shop.sale.order",
                "action_confirm",
                [[orderId]]
            );

            const order = await this.orm.read(
                "shop.sale.order",
                [orderId],
                [
                    "name",
                    "order_date",
                    "subtotal",
                    "discount",
                    "amount_total",
                    "amount_paid",
                    "change_amount",
                    "payment_method",
                    "customer_id",
                ]
            );

            this.state.completedOrder = order[0];

            await this.loadData();

            this.state.cart.splice(0);
            this.state.discount = 0;
            this.state.amount_paid = 0;
            this.state.customer_id = "";

        } catch (error) {

            console.error(error);

            alert(
                error?.data?.message ||
                error?.message ||
                "Unable to complete sale."
            );

        } finally {

            this.state.processing = false;
        }
    }

    newSale() {

        this.state.completedOrder = null;
        this.state.cart.splice(0);

        this.state.discount = 0;
        this.state.amount_paid = 0;
        this.state.customer_id = "";
        this.state.payment_method = "cash";
    }

    printReceipt() {

        window.print();
    }
}

registry.category("actions").add(
    "shop_management.retail_pos",
    RetailPOS
);