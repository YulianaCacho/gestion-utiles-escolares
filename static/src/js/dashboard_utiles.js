/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const EXCLUDED_CATEGORIES = [
    "cuadernos",
    "material personal",
];

const GRADOS_INICIAL = [
    { value: "inicial_3", label: "Inicial 3 años" },
    { value: "inicial_4", label: "Inicial 4 años" },
    { value: "inicial_5", label: "Inicial 5 años" },
];

const GRADOS_PRIMARIA = [
    { value: "1er_grado", label: "1er grado" },
    { value: "2do_grado", label: "2do grado" },
    { value: "3er_grado", label: "3er grado" },
    { value: "4to_grado", label: "4to grado" },
    { value: "5to_grado", label: "5to grado" },
    { value: "6to_grado", label: "6to grado" },
];

const GRADOS_ESCOLARES = [
    { value: "Todos", label: "Todos los grados" },
    ...GRADOS_INICIAL,
    ...GRADOS_PRIMARIA,
];

const GRADOS_BY_NIVEL = {
    Inicial: GRADOS_INICIAL.map((item) => item.value),
    Primaria: GRADOS_PRIMARIA.map((item) => item.value),
};

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
            selectedGrade: "Todos",
            selectedNivel: "",
            showGradeGroup: "",

            updatedAt: "",
            products: [],
            categories: ["Todos"],
            grades: GRADOS_ESCOLARES,

            currentYearId: false,
            currentYearLabel: "Año actual",
            previousYearLabel: "Sobrante anterior",

            totalItems: 0,
            totalProducts: 0,
            lowStock: 0,
            noStock: 0,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadCurrentYear() {
        const anioData = await this.orm.call("anio.escolar", "get_selector_data", []);
        const currentId = anioData.current_id || false;

        this.state.currentYearId = currentId;

        if (!currentId) {
            this.state.currentYearLabel = "Año actual";
            this.state.previousYearLabel = "Sobrante anterior";
            return;
        }

        const anios = await this.orm.searchRead(
            "anio.escolar",
            [["id", "=", currentId]],
            ["anio", "name", "anio_anterior_id"],
            { limit: 1 }
        );

        if (!anios.length) {
            this.state.currentYearLabel = "Año actual";
            this.state.previousYearLabel = "Sobrante anterior";
            return;
        }

        const anio = anios[0];

        this.state.currentYearLabel = String(anio.anio || anio.name || "Año actual");

        if (anio.anio_anterior_id && anio.anio_anterior_id[1]) {
            this.state.previousYearLabel = String(anio.anio_anterior_id[1]).replace("Año escolar ", "");
        } else {
            this.state.previousYearLabel = "Anterior";
        }
    }

    _matchesSelectedScope(gradoEscolar, tipoMovimiento, cantidad) {
        const selectedGrade = this.state.selectedGrade || "Todos";
        const selectedNivel = this.state.selectedNivel || "";
        const viendoTodos = selectedGrade === "Todos" && !selectedNivel;

        if (!gradoEscolar) {
            // Un movimiento sin grado puede sumar o restar stock. Solo
            // cuenta siempre (en cualquier grado) si efectivamente RESTA
            // del almacén compartido: una salida, o un ajuste negativo
            // (ej. mermas del cierre de año). Si en cambio SUMA stock
            // (una entrada, o un ajuste positivo como una compra directa
            // registrada como corrección de inventario), no pertenece a
            // ningún grado en particular y solo debe contarse en "Todos".
            const esReductor =
                tipoMovimiento === "salida" ||
                (tipoMovimiento === "ajuste" && Number(cantidad) < 0);

            if (esReductor) {
                return true;
            }

            return viendoTodos;
        }

        if (selectedGrade !== "Todos") {
            return gradoEscolar === selectedGrade;
        }

        if (selectedNivel) {
            const gradosNivel = GRADOS_BY_NIVEL[selectedNivel] || [];
            return gradosNivel.includes(gradoEscolar);
        }

        return true;
    }

    async loadDashboardData() {
        await this.loadCurrentYear();

        const products = await this.orm.searchRead(
            "product.product",
            [],
            ["display_name", "default_code", "categ_id"],
            { limit: 2000, order: "id asc" }
        );

        const movimientosDomain = this.state.currentYearId
            ? [["anio_escolar_id", "=", this.state.currentYearId]]
            : [["id", "=", 0]];

        const movimientos = await this.orm.searchRead(
            "almacen.utiles.movimiento",
            movimientosDomain,
            ["product_id", "cantidad", "tipo_movimiento", "categoria_id", "grado_escolar"],
            { limit: 10000, order: "id asc" }
        );

        const sobranteFieldsInfo = await this.orm.call(
            "sobrante.utiles.anio",
            "fields_get",
            [],
            { attributes: ["string", "type"] }
        );

        const possibleSobranteFields = [
            "product_id",
            "cantidad_inicial",
            "cantidad_usada",
            "cantidad_disponible",
            "anio_origen_id",
            "anio_destino_id",
            "grado_escolar",
            "estado",
        ];

        const sobranteFields = possibleSobranteFields.filter((field) => sobranteFieldsInfo[field]);
        const sobranteHasGrade = sobranteFields.includes("grado_escolar");

        const sobrantesDomain = this.state.currentYearId
            ? [["anio_destino_id", "=", this.state.currentYearId]]
            : [["id", "=", 0]];

        const sobrantes = await this.orm.searchRead(
            "sobrante.utiles.anio",
            sobrantesDomain,
            sobranteFields,
            { limit: 10000, order: "id asc" }
        );

        const stockActualByProduct = {};
        const retiradoByProduct = {};
        const sobranteByProduct = {};

        for (const mov of movimientos) {
            if (!this._matchesSelectedScope(mov.grado_escolar, mov.tipo_movimiento, mov.cantidad)) {
                continue;
            }

            if (!mov.product_id || !mov.product_id[0]) {
                continue;
            }

            const productId = mov.product_id[0];
            const cantidad = Number(mov.cantidad || 0);

            if (!stockActualByProduct[productId]) {
                stockActualByProduct[productId] = 0;
            }

            if (!retiradoByProduct[productId]) {
                retiradoByProduct[productId] = 0;
            }

            if (mov.tipo_movimiento === "entrada") {
                stockActualByProduct[productId] += cantidad;
            } else if (mov.tipo_movimiento === "salida") {
                stockActualByProduct[productId] -= cantidad;
                retiradoByProduct[productId] += cantidad;
            } else if (mov.tipo_movimiento === "ajuste") {
                stockActualByProduct[productId] += cantidad;
            }
        }

        for (const sobrante of sobrantes) {
            if (sobranteHasGrade && !this._matchesSelectedScope(sobrante.grado_escolar)) {
                continue;
            }

            if (!sobrante.product_id || !sobrante.product_id[0]) {
                continue;
            }

            const productId = sobrante.product_id[0];

            let disponible = 0;

            if ("cantidad_disponible" in sobrante) {
                disponible = Number(sobrante.cantidad_disponible || 0);
            } else {
                const inicial = Number(sobrante.cantidad_inicial || 0);
                const usada = Number(sobrante.cantidad_usada || 0);
                disponible = inicial - usada;
            }

            if (!sobranteByProduct[productId]) {
                sobranteByProduct[productId] = 0;
            }

            sobranteByProduct[productId] += disponible;
        }

        const normalized = products
            .map((product) => {
                const stockActual = Number(stockActualByProduct[product.id] || 0);
                const retirado = Number(retiradoByProduct[product.id] || 0);
                const sobranteAnterior = Number(sobranteByProduct[product.id] || 0);

                const actualDisponible = Math.max(stockActual, 0);
                const totalDisponible = actualDisponible;

                const category = product.categ_id
                    ? product.categ_id[1].split("/").pop().trim()
                    : "Varios";

                return {
                    id: product.id,
                    name: product.display_name || "Sin nombre",
                    code: product.default_code || "",
                    category: category || "Varios",

                    currentQty: actualDisponible,
                    previousQty: 0,
                    totalQty: totalDisponible,
                    reserved: retirado,

                    available: totalDisponible,
                    status: totalDisponible <= 0
                        ? "Sin stock"
                        : totalDisponible <= 5
                            ? "Stock bajo"
                            : "Normal",
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

        this.state.totalItems = normalized.reduce((sum, item) => sum + item.totalQty, 0);
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

    get selectedGradeLabel() {
        if (this.state.selectedGrade !== "Todos") {
            const grado = this.state.grades.find(
                (item) => item.value === this.state.selectedGrade
            );
            return grado ? grado.label : "Todos los grados";
        }

        if (this.state.selectedNivel) {
            return this.state.selectedNivel;
        }

        return "Todos los grados";
    }

    get inicialGrades() {
        return GRADOS_INICIAL;
    }

    get primariaGrades() {
        return GRADOS_PRIMARIA;
    }

    selectCategory(category) {
        this.state.selectedCategory = category;
    }

    async selectGrade(grade) {
        this.state.selectedGrade = grade;

        if (grade === "Todos") {
            this.state.selectedNivel = "";
            this.state.showGradeGroup = "";
        }

        await this.loadDashboardData();
    }

    async toggleGradeGroup(nivel) {
        this.state.showGradeGroup = this.state.showGradeGroup === nivel ? "" : nivel;
        this.state.selectedNivel = nivel;
        this.state.selectedGrade = "Todos";

        await this.loadDashboardData();
    }

    async setGradeFilter(grade) {
        this.state.selectedGrade = grade;
        await this.loadDashboardData();
    }

    progressWidth(product) {
        const base = Math.max(product.totalQty, product.reserved, 1);
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
            [
                "Producto",
                "Categoría",
                `Año actual ${this.state.currentYearLabel}`,
                `Sobrante ${this.state.previousYearLabel}`,
                "Total disponible",
                "Retirado",
                "Estado",
            ],
        ];

        for (const product of this.filteredProducts) {
            rows.push([
                product.name,
                product.category,
                product.currentQty,
                product.previousQty,
                product.totalQty,
                product.reserved,
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