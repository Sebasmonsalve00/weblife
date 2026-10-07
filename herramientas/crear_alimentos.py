# ============================================================
#  crear_alimentos.py - Prepara la lista de alimentos del buscador
#
#  Lee la tabla CIQUAL completa (un JSON grande, con ~60 nutrientes por
#  alimento) y guarda en static/alimentos.json solo lo que usa la web:
#  nombre, grupo y, por 100 g, calorías, proteínas, carbohidratos, azúcares,
#  grasas, grasas saturadas, fibra y sal. Así el archivo pesa mucho menos.
#
#  Uso:  python herramientas/crear_alimentos.py ruta/al/alimentos_nutricion_ciqual_es.json
# ============================================================
import json
import sys
from pathlib import Path

# (columna en la web, nombre en CIQUAL)
CAMPOS = [
    ("kcal", "energia_kcal"),
    ("proteinas", "proteinas"),
    ("carbohidratos", "hidratos_de_carbono"),
    ("azucares", "azucares"),
    ("grasas", "grasas"),
    ("saturadas", "grasas_saturadas"),
    ("fibra", "fibra"),
    ("sal", "sal"),
]


def numero(valor):
    """CIQUAL usa números, "trazas", "<0.5" (por debajo de lo medible) o null (no se sabe)."""
    if valor is None:
        return None
    if isinstance(valor, str):
        return 0   # "trazas" y "<X" son cantidades mínimas: cuentan como 0
    return round(valor, 2)


def main(origen):
    datos = json.loads(Path(origen).read_text(encoding="utf-8"))
    grupos = []
    alimentos = []
    for nombre, info in sorted(datos["alimentos"].items()):
        if info["grupo"] not in grupos:
            grupos.append(info["grupo"])
        valores = info["por_100g"]
        kcal = valores.get("energia_kcal")
        if kcal is None:
            kcal = valores.get("energia_jones_kcal")
        fila = [nombre, grupos.index(info["grupo"]), numero(kcal)]
        fila += [numero(valores.get(clave)) for columna, clave in CAMPOS[1:]]
        alimentos.append(fila)
    salida = {
        "fuente": "CIQUAL 2025, ANSES (Licencia abierta Etalab 2.0)",
        "campos": ["nombre", "grupo"] + [columna for columna, clave in CAMPOS],
        "grupos": grupos,
        "alimentos": alimentos,
    }
    destino = Path(__file__).resolve().parent.parent / "static" / "alimentos.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(alimentos)} alimentos guardados en {destino} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
