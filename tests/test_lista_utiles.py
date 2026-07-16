from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestListaUtiles(TransactionCase):
    """Pruebas unitarias de listas de útiles por grado."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.anio_2026 = cls.env["anio.escolar"].create({
            "anio": 2026,
            "estado": "activo",
            "es_anio_prueba": True,
        })

        cls.env.user.write({
            "anio_escolar_actual_id": cls.anio_2026.id,
        })

        cls.producto_1 = cls.env["product.template"].create({
            "name": "Cuaderno para lista de prueba",
            "tipo_uso_escolar": "personal",
        })

        cls.producto_2 = cls.env["product.template"].create({
            "name": "Lápiz para lista de prueba",
            "tipo_uso_escolar": "personal",
        })

    def _crear_lista(
        self,
        grado="1er_grado",
        anio="2026",
    ):
        valores = {
            "anio": anio,
            "grado_escolar": grado,
        }

        ModeloLista = self.env["lista.utiles.grado"]

        # El campo se incorpora mediante la gestión de períodos escolares.
        if "anio_escolar_id" in ModeloLista._fields:
            valores["anio_escolar_id"] = self.anio_2026.id

        return ModeloLista.create(valores)

    def _crear_linea(
        self,
        lista,
        producto,
        cantidad=1,
    ):
        return self.env["lista.utiles.grado.linea"].create({
            "lista_id": lista.id,
            "product_id": producto.id,
            "cantidad_esperada": cantidad,
        })

    def test_01_crear_lista_nombre_calculado(self):
        """Debe crear la lista y calcular su nombre."""

        lista = self._crear_lista()

        self.assertTrue(
            lista.exists(),
            "La lista de útiles debería haberse creado.",
        )

        self.assertEqual(
            lista.name,
            "Lista de útiles 1er grado - 2026",
            "El nombre calculado de la lista es incorrecto.",
        )

    def test_02_contar_productos_lista(self):
        """Debe contar correctamente los productos registrados."""

        lista = self._crear_lista(
            grado="2do_grado",
        )

        self._crear_linea(
            lista,
            self.producto_1,
            cantidad=4,
        )

        self._crear_linea(
            lista,
            self.producto_2,
            cantidad=2,
        )

        self.assertEqual(
            lista.cantidad_productos,
            2,
            "La lista debería contener dos productos diferentes.",
        )

    def test_03_rechazar_lista_duplicada(self):
        """No debe permitir dos listas para el mismo grado y año."""

        self._crear_lista(
            grado="3er_grado",
        )

        with self.assertRaises(ValidationError):
            self._crear_lista(
                grado="3er_grado",
            )

    def test_04_rechazar_cantidad_cero(self):
        """La cantidad esperada no puede ser igual a cero."""

        lista = self._crear_lista(
            grado="4to_grado",
        )

        with self.assertRaises(ValidationError):
            self._crear_linea(
                lista,
                self.producto_1,
                cantidad=0,
            )

    def test_05_rechazar_cantidad_negativa(self):
        """La cantidad esperada no puede ser negativa."""

        lista = self._crear_lista(
            grado="5to_grado",
        )

        with self.assertRaises(ValidationError):
            self._crear_linea(
                lista,
                self.producto_2,
                cantidad=-2,
            )