from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestRecepcionUtiles(TransactionCase):
    """Pruebas unitarias del detalle de recepción de útiles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.producto = cls.env["product.product"].create({
            "name": "Cuaderno para prueba de recepción",
        })

        cls.recepcion = cls.env[
            "recepcion.utiles.escolar"
        ].create({
            "tipo_entrada": "recepcion_utiles",
            "observacion": "Recepción creada para pruebas unitarias",
        })

    def _crear_linea(
        self,
        esperada=10,
        entregada=0,
        destino="almacen",
        enviada=0,
    ):
        """Crea una línea de recepción con datos personalizables."""

        return self.env["recepcion.utiles.linea"].create({
            "recepcion_id": self.recepcion.id,
            "product_id": self.producto.id,
            "cantidad_esperada": esperada,
            "cantidad_entregada": entregada,
            "destino_recepcion": destino,
            "cantidad_enviada_almacen": enviada,
        })

    def test_01_calcular_cantidad_faltante(self):
        """Debe calcular esperado menos entregado."""

        linea = self._crear_linea(
            esperada=10,
            entregada=7,
        )

        self.assertEqual(
            linea.cantidad_faltante,
            3,
            "La cantidad faltante debería ser 3.",
        )

    def test_02_estado_pendiente_sin_entrega(self):
        """Sin productos entregados, el estado debe ser pendiente."""

        linea = self._crear_linea(
            esperada=10,
            entregada=0,
        )

        self.assertEqual(
            linea.estado_linea,
            "pendiente",
        )

    def test_03_estado_faltante_entrega_parcial(self):
        """Una entrega parcial debe quedar como faltante."""

        linea = self._crear_linea(
            esperada=10,
            entregada=6,
        )

        self.assertEqual(
            linea.cantidad_faltante,
            4,
        )

        self.assertEqual(
            linea.estado_linea,
            "faltante",
        )

    def test_04_estado_completo_entrega_total(self):
        """La entrega total debe quedar completa y sin faltantes."""

        linea = self._crear_linea(
            esperada=10,
            entregada=10,
        )

        self.assertEqual(
            linea.cantidad_faltante,
            0,
        )

        self.assertEqual(
            linea.estado_linea,
            "completo",
        )

    def test_05_rechazar_cantidad_negativa(self):
        """No debe permitir cantidades entregadas negativas."""

        with self.assertRaises(ValidationError):
            self._crear_linea(
                esperada=10,
                entregada=-1,
            )

    def test_06_rechazar_cantidad_decimal(self):
        """No debe permitir cantidades entregadas decimales."""

        with self.assertRaises(ValidationError):
            self._crear_linea(
                esperada=10,
                entregada=2.5,
            )

    def test_07_rechazar_entrega_superior(self):
        """No debe recibir más productos de los esperados."""

        with self.assertRaises(ValidationError):
            self._crear_linea(
                esperada=10,
                entregada=12,
            )

    def test_08_destino_estudiante_no_aplica_almacen(self):
        """Si el útil permanece con el estudiante, no va a almacén."""

        linea = self._crear_linea(
            esperada=5,
            entregada=5,
            destino="estudiante",
        )

        self.assertEqual(
            linea.cantidad_pendiente_almacen,
            0,
        )

        self.assertEqual(
            linea.estado_envio_almacen,
            "no_aplica",
        )

    def test_09_envio_almacen_pendiente(self):
        """Una cantidad recibida aún no enviada debe estar pendiente."""

        linea = self._crear_linea(
            esperada=5,
            entregada=5,
            destino="almacen",
            enviada=0,
        )

        self.assertEqual(
            linea.cantidad_pendiente_almacen,
            5,
        )

        self.assertEqual(
            linea.estado_envio_almacen,
            "pendiente",
        )

    def test_10_envio_almacen_parcial(self):
        """Una parte enviada al almacén debe quedar como parcial."""

        linea = self._crear_linea(
            esperada=5,
            entregada=5,
            destino="almacen",
            enviada=2,
        )

        self.assertEqual(
            linea.cantidad_pendiente_almacen,
            3,
        )

        self.assertEqual(
            linea.estado_envio_almacen,
            "parcial",
        )

    def test_11_envio_almacen_completo(self):
        """Cuando se envía todo, el estado debe ser enviado."""

        linea = self._crear_linea(
            esperada=5,
            entregada=5,
            destino="almacen",
            enviada=5,
        )

        self.assertEqual(
            linea.cantidad_pendiente_almacen,
            0,
        )

        self.assertEqual(
            linea.estado_envio_almacen,
            "enviado",
        )