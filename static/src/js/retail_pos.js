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
            categories: [],
            customers: [],
            cart: [],

            search: "",
            category: "all",

            barcodeInput: "",
            barcodeError: "",

            customer_id: "",
            discount: 0,

            payment_method: "cash",
            amount_paid: 0,

            isMultiPayment: false,
            multiPayments: {
                cash: 0,
                card: 0,
                bank: 0,
            },

            showCustomerModal: false,
            newCustomerName: "",
            newCustomerPhone: "",

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
                "category_id",
                "barcode",
                "sku",
                "image",
            ]
        );

        const categoryRecords = await this.orm.searchRead(
            "shop.product.category",
            [["active", "=", true]],
            ["name"]
        );
        this.state.categories = categoryRecords.map(c => c.name);

        this.state.customers = await this.orm.searchRead(
            "shop.customer",
            [["active", "=", true]],
            [
                "name",
                "phone"
            ]
        );
    }

    get categoryList() {
        const prodCategories = this.state.products
            .map(product =>
                product.category_id
                    ? product.category_id[1]
                    : null
            )
            .filter(Boolean);

        const combined = [...this.state.categories, ...prodCategories];
        return [...new Set(combined)];
    }

    get filteredProducts() {
        const search = this.state.search.toLowerCase().trim();

        return this.state.products.filter(product => {
            const matchesSearch =
                !search ||
                product.name.toLowerCase().includes(search) ||
                (product.barcode && product.barcode.toLowerCase().includes(search)) ||
                (product.sku && product.sku.toLowerCase().includes(search));

            const categoryName = product.category_id
                ? product.category_id[1]
                : "";

            const matchesCategory =
                this.state.category === "all" ||
                categoryName === this.state.category;

            return matchesSearch && matchesCategory;
        });
    }

    // ------------------------------------------------------------------
    // Barcode scanning / entry
    // ------------------------------------------------------------------

    onBarcodeKeydown(event) {
        if (event.key === "Enter") {
            this.searchByBarcode();
        }
    }

    searchByBarcode() {
        const barcode = this.state.barcodeInput.trim();
        this.state.barcodeError = "";

        if (!barcode) {
            return;
        }

        const product = this.state.products.find(
            p => p.barcode && p.barcode.trim().toLowerCase() === barcode.toLowerCase()
        );

        if (!product) {
            this.state.barcodeError = `Product not found for barcode: ${barcode}`;
            setTimeout(() => {
                this.state.barcodeError = "";
            }, 4000);
            return;
        }

        this.addProduct(product);
        this.state.barcodeInput = "";
    }

    // ------------------------------------------------------------------
    // Cart management
    // ------------------------------------------------------------------

    addProduct(product) {
        if (product.quantity <= 0) {
            alert(`${product.name} is out of stock.`);
            return;
        }

        const existing = this.state.cart.find(
            item => item.product_id === product.id
        );

        if (existing) {
            if (existing.quantity < product.quantity) {
                existing.quantity++;
            } else {
                alert(`Cannot add more. Available stock for "${product.name}": ${product.quantity}`);
            }
            return;
        }

        this.state.cart.push({
            product_id: product.id,
            name: product.name,
            price: product.price,
            available: product.quantity,
            quantity: 1,
            discount: 0,
        });
    }

    increase(item) {
        if (item.quantity < item.available) {
            item.quantity++;
        } else {
            alert(`Cannot exceed available stock (${item.available}) for "${item.name}".`);
        }
    }

    decrease(item) {
        if (item.quantity > 1) {
            item.quantity--;
        } else {
            this.removeItem(item);
        }
    }

    updateLineDiscount(item, val) {
        let disc = Number(val) || 0;
        if (disc < 0) disc = 0;
        const maxDisc = item.quantity * item.price;
        if (disc > maxDisc) disc = maxDisc;
        item.discount = disc;
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
        this.state.multiPayments = { cash: 0, card: 0, bank: 0 };
    }

    lineSubtotal(item) {
        const gross = item.price * item.quantity;
        const disc = Number(item.discount) || 0;
        return Math.max(gross - disc, 0);
    }

    get subtotal() {
        return this.state.cart.reduce(
            (total, item) => total + this.lineSubtotal(item),
            0
        );
    }

    get discount() {
        const discount = Number(this.state.discount) || 0;
        return Math.min(Math.max(discount, 0), this.subtotal);
    }

    get total() {
        return Math.max(this.subtotal - this.discount, 0);
    }

    get totalPaid() {
        if (this.state.isMultiPayment) {
            const c = Number(this.state.multiPayments.cash) || 0;
            const cd = Number(this.state.multiPayments.card) || 0;
            const b = Number(this.state.multiPayments.bank) || 0;
            return Math.max(0, c + cd + b);
        } else {
            return Math.max(0, Number(this.state.amount_paid) || 0);
        }
    }

    get change() {
        return Math.max(this.totalPaid - this.total, 0);
    }

    get canCompleteSale() {
        return (
            this.state.cart.length > 0 &&
            this.totalPaid >= this.total &&
            !this.state.processing
        );
    }

    toggleMultiPayment() {
        this.state.isMultiPayment = !this.state.isMultiPayment;
        if (this.state.isMultiPayment) {
            this.state.multiPayments = { cash: this.total, card: 0, bank: 0 };
        } else {
            this.state.amount_paid = this.total;
        }
    }

    // ------------------------------------------------------------------
    // Quick Customer Creation
    // ------------------------------------------------------------------

    openCustomerModal() {
        this.state.newCustomerName = "";
        this.state.newCustomerPhone = "";
        this.state.showCustomerModal = true;
    }

    closeCustomerModal() {
        this.state.showCustomerModal = false;
    }

    async createCustomer() {
        const name = this.state.newCustomerName.trim();
        if (!name) {
            alert("Customer name is required.");
            return;
        }

        try {
            const customerId = await this.orm.create("shop.customer", [{
                name: name,
                phone: this.state.newCustomerPhone.trim(),
            }]);

            const id = Array.isArray(customerId) ? customerId[0] : customerId;
            await this.loadData();
            this.state.customer_id = id;
            this.closeCustomerModal();
        } catch (error) {
            console.error(error);
            alert(error?.data?.message || error?.message || "Failed to create customer.");
        }
    }

    // ------------------------------------------------------------------
    // Sale Confirmation (Atomic)
    // ------------------------------------------------------------------

    async completeSale() {
        if (!this.state.cart.length) {
            alert("Cart is empty.");
            return;
        }

        if (this.totalPaid < this.total) {
            alert(
                `Payment is insufficient.\n\n` +
                `Total Required: Rs. ${this.total.toFixed(2)}\n` +
                `Amount Received: Rs. ${this.totalPaid.toFixed(2)}`
            );
            return;
        }

        this.state.processing = true;

        try {
            const paymentBreakdown = [];
            if (this.state.isMultiPayment) {
                if (Number(this.state.multiPayments.cash) > 0) {
                    paymentBreakdown.push({ method: "cash", amount: Number(this.state.multiPayments.cash) });
                }
                if (Number(this.state.multiPayments.card) > 0) {
                    paymentBreakdown.push({ method: "card", amount: Number(this.state.multiPayments.card) });
                }
                if (Number(this.state.multiPayments.bank) > 0) {
                    paymentBreakdown.push({ method: "bank", amount: Number(this.state.multiPayments.bank) });
                }
            } else {
                paymentBreakdown.push({ method: this.state.payment_method, amount: this.totalPaid });
            }

            const posData = {
                customer_id: this.state.customer_id ? Number(this.state.customer_id) : false,
                discount: this.discount,
                payment_method: this.state.payment_method,
                amount_paid: this.totalPaid,
                payments: paymentBreakdown,
                lines: this.state.cart.map(item => ({
                    product_id: item.product_id,
                    quantity: item.quantity,
                    unit_price: item.price,
                    discount: item.discount || 0,
                })),
            };

            const order = await this.orm.call(
                "shop.sale.order",
                "create_pos_sale",
                [posData]
            );

            this.state.completedOrder = order;

            await this.loadData();

            this.state.cart.splice(0);
            this.state.discount = 0;
            this.state.amount_paid = 0;
            this.state.multiPayments = { cash: 0, card: 0, bank: 0 };
            this.state.isMultiPayment = false;
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
        this.state.multiPayments = { cash: 0, card: 0, bank: 0 };
        this.state.isMultiPayment = false;
        this.state.customer_id = "";
        this.state.payment_method = "cash";
        this.state.barcodeInput = "";
        this.state.barcodeError = "";
    }

    printReceipt() {
        window.print();
    }
}

registry.category("actions").add(
    "shop_management.retail_pos",
    RetailPOS
);