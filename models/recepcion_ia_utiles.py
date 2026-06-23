from odoo import models, api
from odoo.exceptions import UserError


class RecepcionUtilesEscolarIA(models.Model):
    _inherit = "recepcion.utiles.escolar"

    def _ia_normalizar_texto(self, texto):
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

    def action_abrir_reconocimiento_ia(self):
        self.ensure_one()

        if not self.linea_ids:
            raise UserError("Primero debes cargar la lista de útiles del alumno.")

        return {
            "type": "ir.actions.client",
            "name": "Reconocimiento IA",
            "tag": "gestion_utiles_escolares.reconocimiento_ia_dashboard",
            "target": "current",
            "context": {
                "active_id": self.id,
                "active_model": self._name,
                "recepcion_id": self.id,
                "modo_recepcion": True,
            },
        }

    @api.model
    def aplicar_detecciones_ia_recepcion(self, recepcion_id, detections):
        recepcion = self.browse(int(recepcion_id)).exists()

        if not recepcion:
            raise UserError("No se encontró la recepción seleccionada.")

        if recepcion.estado == "validado":
            raise UserError("La recepción ya está validada. No se puede modificar con IA.")

        if not recepcion.linea_ids:
            raise UserError("Primero debes cargar la lista de útiles del alumno.")

        aplicadas = []
        no_encontradas = []
        ya_completas = []

        for detection in detections or []:
            label = detection.get("label") or ""
            confidence = float(detection.get("confidence") or 0)
            product_id = detection.get("product_id") or False

            if confidence < 40:
                no_encontradas.append({
                    "label": label,
                    "motivo": "Confianza baja",
                    "confidence": confidence,
                })
                continue

            lineas_match = self.env["recepcion.utiles.linea"]

            if product_id:
                lineas_match = recepcion.linea_ids.filtered(
                    lambda linea: linea.product_id.id == int(product_id)
                )

            if not lineas_match:
                label_normalizado = recepcion._ia_normalizar_texto(label)
                lineas_match = recepcion.linea_ids.filtered(
                    lambda linea: label_normalizado
                    and (
                        label_normalizado in recepcion._ia_normalizar_texto(linea.product_id.display_name)
                        or label_normalizado in recepcion._ia_normalizar_texto(linea.product_id.name)
                    )
                )

            if not lineas_match:
                no_encontradas.append({
                    "label": label,
                    "motivo": "No está en la lista del alumno",
                    "confidence": confidence,
                })
                continue

            linea = lineas_match.filtered(lambda l: l.cantidad_faltante > 0)[:1]

            if not linea:
                ya_completas.append({
                    "label": label,
                    "motivo": "El producto ya estaba completo",
                    "confidence": confidence,
                })
                continue

            cantidad_a_sumar = 1

            if linea.cantidad_faltante < cantidad_a_sumar:
                cantidad_a_sumar = linea.cantidad_faltante

            nueva_cantidad = linea.cantidad_entregada + cantidad_a_sumar

            observacion_ia = "Detectado con IA: %s (%.2f%%)" % (label, confidence)

            if linea.observacion:
                observacion_ia = linea.observacion + " | " + observacion_ia

            linea.write({
                "cantidad_entregada": nueva_cantidad,
                "observacion": observacion_ia,
            })

            aplicadas.append({
                "linea_id": linea.id,
                "producto": linea.product_id.display_name,
                "cantidad_entregada": linea.cantidad_entregada,
                "cantidad_esperada": linea.cantidad_esperada,
                "cantidad_faltante": linea.cantidad_faltante,
                "estado_linea": linea.estado_linea,
                "confidence": confidence,
            })

        recepcion.action_calcular_faltantes()

        return {
            "success": True,
            "message": "Detecciones aplicadas a la recepción.",
            "aplicadas": aplicadas,
            "no_encontradas": no_encontradas,
            "ya_completas": ya_completas,
            "resumen": {
                "total_productos": recepcion.total_productos,
                "total_completos": recepcion.total_completos,
                "total_faltantes": recepcion.total_faltantes,
                "estado_entrega": recepcion.estado_entrega,
            },
        }