import base64
import os
import tempfile

from odoo import api, models, _
from odoo.exceptions import UserError


class ReconocimientoIAUtiles(models.Model):
    _name = "reconocimiento.ia.utiles"
    _description = "Reconocimiento IA de útiles escolares"

    _MODEL_CACHE = None
    _MODEL_CACHE_PATH = None

    IA_CLASS_ALIASES = {
        "alcohol gel": "alcohol_gel",
        "alcohol_gel": "alcohol_gel",
        "alcohol en gel": "alcohol_gel",

        "alcohol liquido": "alcohol_liquido",
        "alcohol_liquido": "alcohol_liquido",
        "alcohol líquido": "alcohol_liquido",

        "papel toalla": "papel_toalla",
        "papel_toalla": "papel_toalla",

        "panos humedos": "panos_humedos",
        "paños humedos": "panos_humedos",
        "paños húmedos": "panos_humedos",
        "panos_humedos": "panos_humedos",

        "goma": "goma",
        "silicona": "silicona",

        "barra de silicona": "barra_de_silicona",
        "barra_de_silicona": "barra_de_silicona",
        "barras de silicona": "barra_de_silicona",

        "lapiceros": "lapiceros",
        "lapicero": "lapiceros",
        "boligrafos": "lapiceros",
        "bolígrafos": "lapiceros",

        "lapiz": "lapiz",
        "lápiz": "lapiz",

        "lapiz rojo": "lapiz_rojo",
        "lápiz rojo": "lapiz_rojo",
        "lapiz_rojo": "lapiz_rojo",

        "corrector": "corrector",
        "resaltador": "resaltador",
        "borrador": "borrador",
        "tajador": "tajador",
        "tijera": "tijera",
        "tijeras": "tijera",

        "plumones": "plumones",
        "plumon de pizarra": "plumon_de_pizarra",
        "plumón de pizarra": "plumon_de_pizarra",
        "plumon_de_pizarra": "plumon_de_pizarra",

        "plumon indeleble": "plumon_indeleble",
        "plumón indeleble": "plumon_indeleble",
        "plumon_indeleble": "plumon_indeleble",

        "colores crayones": "colores_crayones",
        "colores_crayones": "colores_crayones",
        "colores": "colores_crayones",
        "crayones": "colores_crayones",

        "plastilina": "plastilina",
        "pintura acrilica": "pintura_acrilica",
        "pintura_acrilica": "pintura_acrilica",
        "pintura acrílica": "pintura_acrilica",

        "tempera": "tempera",
        "témpera": "tempera",

        "pincel lengua": "pincel_lengua",
        "pincel_lengua": "pincel_lengua",

        "tizas pastel": "tizas_pastel",
        "tizas_pastel": "tizas_pastel",

        "cuaderno": "cuaderno",
        "archivador": "archivador",
        "cartuchera": "cartuchera",
        "regla": "regla",
        "transportador": "transportador",

        "cinta masking": "cinta_masking",
        "cinta_masking": "cinta_masking",
        "masking": "cinta_masking",
    }

    @api.model
    def _normalizar_texto(self, texto):
        texto = (texto or "").lower().replace("_", " ").strip()
        reemplazos = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
        for origen, destino in reemplazos.items():
            texto = texto.replace(origen, destino)
        return " ".join(texto.split())

    @api.model
    def _normalizar_clase_ia(self, texto):
        texto_normalizado = self._normalizar_texto(texto)
        return self.IA_CLASS_ALIASES.get(
            texto_normalizado,
            texto_normalizado.replace(" ", "_"),
        )

    @api.model
    def _get_local_model_path(self):
        module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(module_path, "ai_models", "utiles_escolares_best.pt")

    @api.model
    def _get_model_path(self):
        configured_path = self.env["ir.config_parameter"].sudo().get_param(
            "gestion_utiles_escolares.ia_model_path"
        )

        possible_paths = [
            configured_path,
            os.getenv("ODOO_IA_MODEL_PATH"),
            "/opt/odoo-genios/ia_models/utiles_escolares_best.pt",
            self._get_local_model_path(),
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return path

        return configured_path or self._get_local_model_path()

    @api.model
    def get_estado_modelo(self):
        model_path = self._get_model_path()
        exists = bool(model_path and os.path.exists(model_path))

        size_mb = 0
        if exists:
            size_mb = round(os.path.getsize(model_path) / (1024 * 1024), 2)

        dependency_ok = True
        dependency_message = "Ultralytics disponible"

        try:
            import ultralytics  # noqa: F401
        except Exception:
            dependency_ok = False
            dependency_message = "Falta instalar ultralytics en el servidor"

        return {
            "model_path": model_path,
            "exists": exists,
            "size_mb": size_mb,
            "dependency_ok": dependency_ok,
            "dependency_message": dependency_message,
        }

    @api.model
    def _load_yolo_model(self, model_path):
        if not model_path or not os.path.exists(model_path):
            raise UserError(
                _(
                    "No se encontró el modelo IA.\n\n"
                    "Ruta esperada:\n%s\n\n"
                    "Primero debes subir utiles_escolares_best.pt al servidor."
                )
                % model_path
            )

        try:
            from ultralytics import YOLO
        except Exception as error:
            raise UserError(
                _(
                    "Falta instalar la librería ultralytics en el servidor de Odoo.\n\n"
                    "Error técnico:\n%s"
                )
                % str(error)
            )

        if (
            self.__class__._MODEL_CACHE is None
            or self.__class__._MODEL_CACHE_PATH != model_path
        ):
            self.__class__._MODEL_CACHE = YOLO(model_path)
            self.__class__._MODEL_CACHE_PATH = model_path

        return self.__class__._MODEL_CACHE

    @api.model
    def _buscar_producto_por_clase_ia(self, ia_class):
        if not ia_class:
            return False

        producto = self.env["product.product"].search(
            [("product_tmpl_id.ia_clase_util", "=", ia_class)],
            limit=1,
        )

        return producto

    @api.model
    def analizar_imagen_base64(self, image_base64, filename=False):
        if not image_base64:
            raise UserError(_("Primero debes seleccionar una imagen."))

        model_path = self._get_model_path()
        model = self._load_yolo_model(model_path)

        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        try:
            image_content = base64.b64decode(image_base64)
        except Exception:
            raise UserError(_("La imagen no tiene un formato válido."))

        suffix = ".jpg"
        if filename and "." in filename:
            suffix = "." + filename.split(".")[-1].lower()

        temp_path = False

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(image_content)
                temp_path = temp_file.name

            results = model(temp_path, verbose=False)
            result = results[0] if results else False

            detections = []

            if not result or result.boxes is None:
                return {
                    "success": True,
                    "message": "No se detectaron útiles escolares en la imagen.",
                    "total": 0,
                    "detections": [],
                }

            names = getattr(model, "names", {}) or getattr(result, "names", {})

            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item()) * 100

                label_original = names.get(class_id, str(class_id))
                label_clean = str(label_original).replace("_", " ").strip()
                ia_class = self._normalizar_clase_ia(label_original)

                producto = self._buscar_producto_por_clase_ia(ia_class)

                detections.append(
                    {
                        "class_id": class_id,
                        "label": label_clean.title(),
                        "ia_class": ia_class,
                        "confidence": round(confidence, 2),
                        "product_id": producto.id if producto else False,
                        "product_name": producto.display_name if producto else "",
                    }
                )

            detections = sorted(
                detections,
                key=lambda item: item.get("confidence", 0),
                reverse=True,
            )

            top_detection = detections[0] if detections else False

            return {
                "success": True,
                "message": "Análisis completado correctamente.",
                "total": len(detections),
                "top_detection": top_detection,
                "detections": detections,
            }

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)