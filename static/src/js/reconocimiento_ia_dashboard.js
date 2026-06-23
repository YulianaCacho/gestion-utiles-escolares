/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReconocimientoIADashboard extends Component {
    static template = "gestion_utiles_escolares.ReconocimientoIADashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const actionContext = this.props.action?.context || {};
        const recepcionId =
            actionContext.recepcion_id ||
            actionContext.active_id ||
            actionContext.default_recepcion_id ||
            false;

        this.state = useState({
            loading: false,
            checkingModel: true,

            filename: "",
            preview: "",
            imageBase64: "",

            recepcionId: recepcionId,
            candidateLoading: false,
            candidatePanel: null,
            selectedLineId: false,
            quantityToMark: 1,
            applyLoading: false,
            applyResult: null,

            modelStatus: {
                exists: false,
                dependency_ok: false,
                dependency_message: "",
                model_path: "",
                size_mb: 0,
            },

            result: null,
            detections: [],
            error: "",
        });

        onWillStart(async () => {
            await this.loadModelStatus();
        });
    }

    async loadModelStatus() {
        this.state.checkingModel = true;

        try {
            const status = await this.orm.call(
                "reconocimiento.ia.utiles",
                "get_estado_modelo",
                []
            );

            this.state.modelStatus = status;
        } catch (error) {
            this.state.error = this.getErrorMessage(error);
        } finally {
            this.state.checkingModel = false;
        }
    }

    getErrorMessage(error) {
        return (
            error?.data?.message ||
            error?.message ||
            "Ocurrió un error inesperado."
        );
    }

    onFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];

        if (!file) {
            return;
        }

        if (!file.type.startsWith("image/")) {
            this.notification.add("Selecciona una imagen válida.", {
                type: "warning",
            });
            return;
        }

        const reader = new FileReader();

        reader.onload = () => {
            const value = String(reader.result || "");
            this.state.filename = file.name;
            this.state.preview = value;
            this.state.imageBase64 = value.includes(",")
                ? value.split(",")[1]
                : value;

            this.state.result = null;
            this.state.detections = [];
            this.state.candidatePanel = null;
            this.state.selectedLineId = false;
            this.state.quantityToMark = 1;
            this.state.applyResult = null;
            this.state.error = "";
        };

        reader.readAsDataURL(file);
    }

    async analyzeImage() {
        if (!this.state.imageBase64) {
            this.notification.add("Primero selecciona una imagen.", {
                type: "warning",
            });
            return;
        }

        this.state.loading = true;
        this.state.error = "";
        this.state.result = null;
        this.state.detections = [];
        this.state.candidatePanel = null;
        this.state.selectedLineId = false;
        this.state.quantityToMark = 1;
        this.state.applyResult = null;

        try {
            const result = await this.orm.call(
                "reconocimiento.ia.utiles",
                "analizar_imagen_base64",
                [this.state.imageBase64, this.state.filename]
            );

            this.state.result = result;
            this.state.detections = result.detections || [];

            if (this.state.detections.length) {
                this.notification.add("Imagen analizada correctamente.", {
                    type: "success",
                });

                if (this.state.recepcionId) {
                    await this.loadCandidatesForReception(this.state.detections[0]);
                }
            } else {
                this.notification.add("No se detectaron útiles en la imagen.", {
                    type: "info",
                });
            }
        } catch (error) {
            this.state.error = this.getErrorMessage(error);
            this.notification.add(this.state.error, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async loadCandidatesForReception(detection) {
        this.state.candidateLoading = true;
        this.state.candidatePanel = null;
        this.state.selectedLineId = false;
        this.state.quantityToMark = 1;

        try {
            const result = await this.orm.call(
                "recepcion.utiles.escolar",
                "obtener_candidatos_ia_recepcion",
                [this.state.recepcionId, detection]
            );

            this.state.candidatePanel = result;
            this.state.selectedLineId = result.selected_line_id || false;
            this.state.quantityToMark = result.cantidad_sugerida || 1;

            if (!result.candidatos || !result.candidatos.length) {
                this.notification.add(
                    "No se encontraron productos candidatos en la lista del alumno.",
                    { type: "warning" }
                );
            }
        } catch (error) {
            this.state.error = this.getErrorMessage(error);
            this.notification.add(this.state.error, {
                type: "danger",
            });
        } finally {
            this.state.candidateLoading = false;
        }
    }

    onCandidateChange(ev) {
        this.state.selectedLineId = parseInt(ev.target.value || "0", 10) || false;

        const selected = this.candidates.find(
            (item) => item.linea_id === this.state.selectedLineId
        );

        if (selected && selected.cantidad_faltante > 0) {
            this.state.quantityToMark = Math.min(1, selected.cantidad_faltante);
        }
    }

    onQuantityChange(ev) {
        const value = parseFloat(ev.target.value || "0");
        this.state.quantityToMark = value > 0 ? value : 1;
    }

    async applySelectedToReception() {
        if (!this.state.recepcionId) {
            this.notification.add(
                "Abre este panel desde una recepción para marcar la lista del alumno.",
                { type: "warning" }
            );
            return;
        }

        if (!this.state.selectedLineId) {
            this.notification.add("Selecciona el producto correcto.", {
                type: "warning",
            });
            return;
        }

        if (!this.state.quantityToMark || this.state.quantityToMark <= 0) {
            this.notification.add("Ingresa una cantidad válida.", {
                type: "warning",
            });
            return;
        }

        this.state.applyLoading = true;
        this.state.applyResult = null;

        try {
            const result = await this.orm.call(
                "recepcion.utiles.escolar",
                "aplicar_verificacion_ia_recepcion",
                [
                    this.state.recepcionId,
                    this.state.selectedLineId,
                    this.state.quantityToMark,
                    this.topDetection || {},
                ]
            );

            this.state.applyResult = result;

            this.notification.add("Producto marcado como verificado.", {
                type: "success",
            });

            if (this.topDetection) {
                await this.loadCandidatesForReception(this.topDetection);
            }
        } catch (error) {
            this.state.error = this.getErrorMessage(error);
            this.notification.add(this.state.error, {
                type: "danger",
            });
        } finally {
            this.state.applyLoading = false;
        }
    }

    clearImage() {
        this.state.filename = "";
        this.state.preview = "";
        this.state.imageBase64 = "";
        this.state.result = null;
        this.state.detections = [];
        this.state.candidatePanel = null;
        this.state.selectedLineId = false;
        this.state.quantityToMark = 1;
        this.state.applyResult = null;
        this.state.error = "";
    }

    get topDetection() {
        if (!this.state.detections.length) {
            return null;
        }

        return this.state.detections[0];
    }

    get confidenceText() {
        if (!this.topDetection) {
            return "0%";
        }

        return `${this.topDetection.confidence}%`;
    }

    get modelReady() {
        return (
            this.state.modelStatus.exists &&
            this.state.modelStatus.dependency_ok
        );
    }

    get candidates() {
        return this.state.candidatePanel?.candidatos || [];
    }

    get hasCandidates() {
        return this.candidates.length > 0;
    }
}

registry
    .category("actions")
    .add(
        "gestion_utiles_escolares.reconocimiento_ia_dashboard",
        ReconocimientoIADashboard
    );