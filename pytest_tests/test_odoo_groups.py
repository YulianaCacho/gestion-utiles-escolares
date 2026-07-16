import subprocess

import pytest


MODULE = "gestion_utiles_escolares"
DATABASE = "genios_unit_test"

GRUPOS_PRUEBA = [
    (
        "almacen",
        "TestAlmacenUtiles",
        1,
        8072,
    ),
    (
        "listas_utiles",
        "TestListaUtiles",
        5,
        8073,
    ),
    (
        "matricula",
        "TestMatriculaEscolar",
        5,
        8074,
    ),
    (
        "recepcion",
        "TestRecepcionUtiles",
        11,
        8075,
    ),
    (
        "sobrantes",
        "TestSobrantesUtiles",
        3,
        8076,
    ),
]


@pytest.mark.parametrize(
    "nombre_grupo,clase_odoo,cantidad_esperada,puerto",
    GRUPOS_PRUEBA,
    ids=[
        grupo[0]
        for grupo in GRUPOS_PRUEBA
    ],
)
def test_grupo_unitario_odoo(
    nombre_grupo,
    clase_odoo,
    cantidad_esperada,
    puerto,
):
    """
    Ejecuta mediante Pytest cada grupo de pruebas unitarias
    definido con TransactionCase dentro del módulo Odoo.
    """

    comando = [
        "/usr/bin/odoo",
        "-c",
        "/etc/odoo/odoo.conf",
        "-d",
        DATABASE,
        "-u",
        MODULE,
        "--test-tags",
        f"/{MODULE}:{clase_odoo}",
        "--stop-after-init",
        f"--http-port={puerto}",
        "--http-interface=127.0.0.1",
        "--workers=0",
        "--log-level=test",
    ]

    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    salida = (
        (resultado.stdout or "")
        +
        "\n"
        +
        (resultado.stderr or "")
    )

    resumen_esperado = (
        f"0 failed, 0 error(s) "
        f"of {cantidad_esperada} tests"
    )

    assert resultado.returncode == 0, (
        f"El grupo '{nombre_grupo}' terminó con "
        f"código {resultado.returncode}.\n\n"
        f"{salida}"
    )

    assert resumen_esperado in salida, (
        f"No se encontró el resultado esperado para "
        f"'{nombre_grupo}': {resumen_esperado}\n\n"
        f"{salida}"
    )

    print(
        f"{nombre_grupo}: "
        f"{cantidad_esperada} pruebas Odoo aprobadas."
    )