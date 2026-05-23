/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const EXCLUDED_CATEGORIES = [
    "cuadernos",
    "material personal",
];

function normalizeText(value) {
    return String(value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
}

class DashboardUtilesEscolares extends Component {
    static template = "gestion_utiles_escolares.DashboardUtilesEscolares";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            search: "",
            selectedCategory: "Todos",
            updatedAt: "",
            products: [],
            categories: ["Todos"],
            totalItems: 0,
            totalProducts: 0,
            lowStock: 0,
            noStock: 0,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const products = await this.orm.searchRead(
            "product.product",
            [],
            ["display_name", "default_code", "categ_id"],
            { limit: 2000, order: "id asc" }
        );

        const movimientos = await this.orm.searchRead(
            "almacen.utiles.movimiento",
            [],
            ["product_id", "cantidad", "tipo_movimiento", "categoria_id"],
            { limit: 10000, order: "id asc" }
        );

        const stockByProduct = {};

        for (const mov of movimientos) {
            if (!mov.product_id || !mov.product_id[0]) {
               continue;
            }

            const productId = mov.product_id[0];
            const cantidad = Number(mov.cantidad || 0);

            if (!stockByProduct[productId]) {
                 stockByProduct[productId] = 0;
           }

           if (mov.tipo_movimiento === "entrada") {
               stockByProduct[productId] += cantidad;
           } else if (mov.tipo_movimiento === "salida") {
               stockByProduct[productId] -= cantidad;
           } else if (mov.tipo_movimiento === "ajuste") {
               stockByProduct[productId] += cantidad;
           }
       }

        const normalized = products
            .map((product) => {
               const qty = Number(stockByProduct[product.id] || 0);
               const reserved = 0;
               const available = Math.max(qty - reserved, 0);

               const category = product.categ_id
                   ? product.categ_id[1].split("/").pop().trim()
                   : "Varios";

               return {
                   id: product.id,
                   name: product.display_name || "Sin nombre",
                   code: product.default_code || "",
                   category: category || "Varios",
                   qty,
                   reserved,
                   available,
                   status: available <= 0 ? "Sin stock" : available <= 5 ? "Stock bajo" : "Normal",
             };
            })
           .filter((product) => {
              const categoryNormalized = normalizeText(product.category);

              return !EXCLUDED_CATEGORIES.some((excluded) =>
                  categoryNormalized.includes(excluded)
              );
           });
 
        const categories = Array.from(new Set(normalized.map((p) => p.category))).sort();
        const now = new Date();

        this.state.products = normalized;
        this.state.categories = ["Todos", ...categories];
        this.state.totalItems = normalized.reduce((sum, item) => sum + item.qty, 0);
        this.state.totalProducts = normalized.length;
        this.state.lowStock = normalized.filter((item) => item.available > 0 && item.available <= 5).length;
        this.state.noStock = normalized.filter((item) => item.available <= 0).length;
        this.state.updatedAt =
            now.toLocaleDateString("es-PE") +
            " " +
            now.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
    }

    get filteredProducts() {
        const text = normalizeText(this.state.search);

        return this.state.products.filter((product) => {
            const matchesCategory =
                this.state.selectedCategory === "Todos" ||
                product.category === this.state.selectedCategory;

            const matchesText =
                !text ||
                normalizeText(product.name).includes(text) ||
                normalizeText(product.category).includes(text) ||
                normalizeText(product.code).includes(text);

            return matchesCategory && matchesText;
        });
    }

    selectCategory(category) {
        this.state.selectedCategory = category;
    }

    progressWidth(product) {
        const base = Math.max(product.qty, product.reserved, product.available, 1);
        const percent = Math.min(Math.round((product.available / base) * 100), 100);
        return `width: ${percent}%;`;
    }

    statusClass(status) {
        if (status === "Sin stock") {
            return "o_utiles_status_no_stock";
        }

        if (status === "Stock bajo") {
            return "o_utiles_status_low";
        }

        return "o_utiles_status_ok";
    }

    async openProducts() {
        await this.action.doAction("gestion_utiles_escolares.action_productos_utiles_escolares");
    }

    exportCsv() {
        const rows = [
            ["Producto", "Categoría", "En almacén", "Reservado", "Disponible", "Estado"],
        ];

        for (const product of this.filteredProducts) {
            rows.push([
                product.name,
                product.category,
                product.qty,
                product.reserved,
                product.available,
                product.status,
            ]);
        }

        const csv = rows
            .map((row) =>
                row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",")
            )
            .join("\n");

        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "stock_utiles_escolares.csv";
        link.click();

        URL.revokeObjectURL(url);
    }
}

registry.category("actions").add("gestion_utiles_escolares.dashboard", DashboardUtilesEscolares);