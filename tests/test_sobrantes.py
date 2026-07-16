from odoo.tests.common import TransactionCase


class TestSobrantesUtiles(TransactionCase):
    """Pruebas unitarias de los sobrantes de útiles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.producto = cls.env["product.product"].create({
            "name": "Cuaderno de prueba",
        })

        cls.anio_2026 = cls.env["anio.escolar"].create({
            "anio": 2026,
            "estado": "cerrado",
            "es_anio_prueba": True,
        })

        cls.anio_2027 = cls.env["anio.escolar"].create({
            "anio": 2027,
            "estado": "borrador",
            "es_anio_prueba": True,
        })

    def _crear_sobrante(self, inicial, usada):
        return self.env["sobrante.utiles.anio"].create({
            "anio_origen_id": self.anio_2026.id,
            "anio_destino_id": self.anio_2027.id,
            "product_id": self.producto.id,
            "cantidad_inicial": inicial,
            "cantidad_usada": usada,
        })

    def test_01_calcular_cantidad_disponible(self):
        sobrante = self._crear_sobrante(
            inicial=20,
            usada=7,
        )

        self.assertEqual(
            sobrante.cantidad_disponible,
            13,
        )

    def test_02_estado_disponible(self):
        sobrante = self._crear_sobrante(
            inicial=20,
            usada=7,
        )

        self.assertEqual(
            sobrante.estado,
            "disponible",
        )

    def test_03_estado_agotado(self):
        sobrante = self._crear_sobrante(
            inicial=10,
            usada=10,
        )

        self.assertEqual(
            sobrante.cantidad_disponible,
            0,
        )
        self.assertEqual(
            sobrante.estado,
            "agotado",
        )