/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReconocimientoIADashboard extends Component {
    static template = "gestion_utiles_escolares.ReconocimientoIADashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: false,
            checkingModel: true,

            filename: "",
            preview: "",
            imageBase64: "",

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

    clearImage() {
        this.state.filename = "";
        this.state.preview = "";
        this.state.imageBase64 = "";
        this.state.result = null;
        this.state.detections = [];
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

        return `${Number(this.topDetection.confidence || 0).toFixed(1)}%`;
    }

    get modelReady() {
        return (
            this.state.modelStatus.exists &&
            this.state.modelStatus.dependency_ok
        );
    }
}

registry
    .category("actions")
    .add(
        "gestion_utiles_escolares.reconocimiento_ia_dashboard",
        ReconocimientoIADashboard
    );