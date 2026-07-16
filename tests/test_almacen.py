from odoo.tests.common import TransactionCase


class TestAlmacenUtiles(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.producto = cls.env["product.product"].create({
            "name": "Lápiz de prueba",
        })

    def test_01_stock_entradas_menos_salidas(self):
        Movimiento = self.env["almacen.utiles.movimiento"]

        Movimiento.create({
            "tipo_movimiento": "entrada",
            "product_id": self.producto.id,
            "cantidad": 10,
        })

        Movimiento.create({
            "tipo_movimiento": "salida",
            "product_id": self.producto.id,
            "cantidad": 4,
        })

        movimientos = Movimiento.search([
            ("product_id", "=", self.producto.id),
        ])

        entradas = sum(
            movimientos.filtered(
                lambda movimiento:
                movimiento.tipo_movimiento == "entrada"
            ).mapped("cantidad")
        )

        salidas = sum(
            movimientos.filtered(
                lambda movimiento:
                movimiento.tipo_movimiento == "salida"
            ).mapped("cantidad")
        )

        stock_disponible = entradas - salidas

        self.assertEqual(
            stock_disponible,
            6,
        )