from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMatriculaEscolar(TransactionCase):
    """Pruebas unitarias del modelo matricula.escolar."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.estudiante = cls.env["res.partner"].create({
            "name": "Estudiante de prueba",
            "tipo_contacto_escolar": "estudiante",
            "grado_escolar": "1er_grado",
        })

    def _crear_matricula(self, **valores_adicionales):
        valores = {
            "estudiante_id": self.estudiante.id,
            "anio_escolar": 2026,
            "grado_escolar": "1er_grado",
        }

        valores.update(valores_adicionales)

        return self.env["matricula.escolar"].create(valores)

    def test_01_crear_matricula(self):
        """Debe crear correctamente una matrícula escolar."""

        matricula = self._crear_matricula()

        self.assertTrue(matricula.exists())
        self.assertEqual(
            matricula.estudiante_id,
            self.estudiante,
        )
        self.assertEqual(
            matricula.grado_escolar,
            "1er_grado",
        )

    def test_02_estado_activo_por_defecto(self):
        """Una matrícula nueva debe comenzar con estado activo."""

        matricula = self._crear_matricula()

        self.assertEqual(
            matricula.estado,
            "activo",
            "La matrícula nueva debería tener estado activo.",
        )

    def test_03_nombre_calculado(self):
        """Debe generar la referencia de la matrícula."""

        matricula = self._crear_matricula()

        self.assertEqual(
            matricula.name,
            "Estudiante de prueba - 1er grado - 2026",
        )

    def test_04_matricula_duplicada(self):
        """No debe permitir dos matrículas del mismo estudiante y año."""

        self._crear_matricula()

        with self.assertRaises(ValidationError):
            self._crear_matricula()

    def test_05_anio_visual(self):
        """El año visual debe mostrarse sin decimales ni comas."""

        matricula = self._crear_matricula()

        self.assertEqual(
            matricula.anio_escolar_visual,
            "2026",
        )