from odoo import api, models
from odoo.exceptions import UserError


class RecepcionUtilesEscolarIA(models.Model):
    _inherit = "recepcion.utiles.escolar"

    IA_KEYWORDS = {
        "alcohol_gel": ["alcohol gel", "alcohol en gel", "gel"],
        "alcohol_liquido": ["alcohol liquido", "alcohol líquido"],
        "papel_toalla": ["papel toalla"],
        "panos_humedos": ["pano humedo", "panos humedos", "paño humedo", "paños humedos", "paños húmedos"],
        "goma": ["goma"],
        "silicona": ["silicona liquida", "silicona líquida", "silicona x 250", "silicona x250"],
        "barra_de_silicona": ["barra silicona", "barra de silicona", "barras silicona", "barras de silicona"],
        "lapiceros": ["lapicero", "lapiceros", "boligrafo", "bolígrafo", "boligrafos", "bolígrafos"],
        "lapiz": ["lapiz", "lápiz"],
        "lapiz_rojo": ["lapiz rojo", "lápiz rojo", "chequeo rojo"],
        "corrector": ["corrector"],
        "resaltador": ["resaltador"],
        "borrador": ["borrador"],
        "tajador": ["tajador"],
        "tijera": ["tijera", "tijeras"],
        "plumones": ["plumones", "plumon", "plumón"],
        "plumon_de_pizarra": ["plumon de pizarra", "plumón de pizarra", "pizarra", "pilot"],
        "plumon_indeleble": ["plumon indeleble", "plumón indeleble", "indeleble"],
        "colores_crayones": ["colores", "caja de colores", "crayones", "crayon"],
        "plastilina": ["plastilina"],
        "pintura_acrilica": ["pintura acrilica", "pintura acrílica", "acrilica", "acrílica"],
        "tempera": ["tempera", "témpera"],
        "pincel_lengua": ["pincel", "lengua de gato"],
        "tizas_pastel": ["tizas pastel", "tiza pastel"],
        "cuaderno": ["cuaderno"],
        "archivador": ["archivador"],
        "cartuchera": ["cartuchera"],
        "regla": ["regla"],
        "transportador": ["transportador"],
        "cinta_masking": ["cinta masking", "masking tape", "masking"],
    }

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

    def _ia_normalizar_clase(self, texto):
        texto = self._ia_normalizar_texto(texto)
        texto = texto.replace(" ", "_")

        alias = {
            "paños_humedos": "panos_humedos",
            "panos_humedos": "panos_humedos",
            "cinta_masking": "cinta_masking",
            "cinta_masking_tape": "cinta_masking",
            "barra_silicona": "barra_de_silicona",
            "barra_de_silicona": "barra_de_silicona",
            "colores": "colores_crayones",
            "crayones": "colores_crayones",
        }

        return alias.get(texto, texto)

    def _ia_producto_coincide_con_clase(self, producto, ia_class):
        if not producto or not ia_class:
            return False

        clase_producto = producto.product_tmpl_id.ia_clase_util

        if clase_producto:
            return clase_producto == ia_class

        nombre_producto = self._ia_normalizar_texto(producto.display_name)
        keywords = self.IA_KEYWORDS.get(ia_class, [])

        for keyword in keywords:
            keyword_norm = self._ia_normalizar_texto(keyword)
            if keyword_norm and keyword_norm in nombre_producto:
                return True

        return False

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
    def obtener_candidatos_ia_recepcion(self, recepcion_id, detection):
        recepcion = self.browse(int(recepcion_id)).exists()

        if not recepcion:
            raise UserError("No se encontró la recepción seleccionada.")

        if not recepcion.linea_ids:
            raise UserError("Primero debes cargar la lista de útiles del alumno.")

        detection = detection or {}
        ia_class = self._ia_normalizar_clase(
            detection.get("ia_class") or detection.get("label") or ""
        )

        confidence = float(detection.get("confidence") or 0)
        label = detection.get("label") or ia_class.replace("_", " ").title()

        lineas_con_clase_configurada = recepcion.linea_ids.filtered(
            lambda linea: linea.product_id.product_tmpl_id.ia_clase_util == ia_class
        )

        if lineas_con_clase_configurada:
            lineas_candidatas = lineas_con_clase_configurada
        else:
            lineas_candidatas = recepcion.linea_ids.filtered(
                lambda linea: self._ia_producto_coincide_con_clase(linea.product_id, ia_class)
            )

        candidatos = []

        for linea in lineas_candidatas:
            faltante = float(linea.cantidad_faltante or 0)
            esperado = float(linea.cantidad_esperada or 0)
            entregado = float(linea.cantidad_entregada or 0)

            candidatos.append({
                "linea_id": linea.id,
                "product_id": linea.product_id.id,
                "producto": linea.product_id.display_name,
                "cantidad_esperada": esperado,
                "cantidad_entregada": entregado,
                "cantidad_faltante": faltante,
                "estado_linea": linea.estado_linea,
                "is_complete": faltante <= 0,
            })

        candidato_disponible = next(
            (item for item in candidatos if not item["is_complete"]),
            False,
        )

        cantidad_sugerida = 1
        max_quantity = 1

        if candidato_disponible:
            max_quantity = max(candidato_disponible["cantidad_faltante"], 1)
            cantidad_sugerida = min(1, max_quantity)

        return {
            "success": True,
            "label": label,
            "ia_class": ia_class,
            "confidence": confidence,
            "candidatos": candidatos,
            "selected_line_id": candidato_disponible["linea_id"] if candidato_disponible else False,
            "cantidad_sugerida": cantidad_sugerida,
            "max_quantity": max_quantity,
            "message": "Candidatos encontrados." if candidatos else "No se encontraron productos candidatos en la lista del alumno.",
        }

    @api.model
    def aplicar_verificacion_ia_recepcion(self, recepcion_id, linea_id, cantidad, detection):
        recepcion = self.browse(int(recepcion_id)).exists()

        if not recepcion:
            raise UserError("No se encontró la recepción seleccionada.")

        if "estado" in recepcion._fields and recepcion.estado == "validado":
            raise UserError("La recepción ya está validada. No se puede modificar con IA.")

        linea = recepcion.linea_ids.filtered(lambda item: item.id == int(linea_id))[:1]

        if not linea:
            raise UserError("El producto seleccionado no pertenece a esta recepción.")

        try:
            cantidad = float(cantidad or 0)
        except Exception:
            cantidad = 0

        if cantidad <= 0:
            raise UserError("La cantidad debe ser mayor a cero.")

        faltante = float(linea.cantidad_faltante or 0)

        if faltante <= 0:
            raise UserError("Este producto ya se encuentra completo en la recepción.")

        if cantidad > faltante:
            raise UserError(
                "La cantidad ingresada supera la cantidad faltante. "
                "Faltante actual: %.2f" % faltante
            )

        detection = detection or {}
        label = detection.get("label") or ""
        ia_class = detection.get("ia_class") or ""
        confidence = float(detection.get("confidence") or 0)

        nueva_cantidad = float(linea.cantidad_entregada or 0) + cantidad

        observacion_ia = "Verificado con IA: %s [%s] (%.2f%%) - Cantidad: %.2f" % (
            label,
            ia_class,
            confidence,
            cantidad,
        )

        if linea.observacion:
            observacion_ia = linea.observacion + " | " + observacion_ia

        linea.write({
            "cantidad_entregada": nueva_cantidad,
            "observacion": observacion_ia,
        })

        recepcion.action_calcular_faltantes()

        return {
            "success": True,
            "message": "Producto marcado como verificado.",
            "producto": linea.product_id.display_name,
            "cantidad_marcada": cantidad,
            "cantidad_entregada": linea.cantidad_entregada,
            "cantidad_esperada": linea.cantidad_esperada,
            "cantidad_faltante": linea.cantidad_faltante,
            "estado_linea": linea.estado_linea,
        }