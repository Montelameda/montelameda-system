import csv, firebase_config, pathlib, datetime

def export_ml_csv(outfile: str = "mercadolibre_export.csv"):
    db = firebase_config.db
    productos = db.collection("productos").stream()

    # Cabeceras mínimas que MercadoLibre requiere en carga masiva
    headers = [
        "category_id", "title", "price", "currency_id", "available_quantity",
        "listing_type_id", "condition", "description"
    ]

    # Descubrimos atributos dinámicos:
    dynamic_attrs = set()
    buffer_rows = []
    for prod in productos:
        d = prod.to_dict()
        ml_attrs = d.get("ml_attrs", {})
        dynamic_attrs.update(ml_attrs.keys())

        row = {
            "category_id": d.get("ml_cat_id", ""),
            "title": d.get("nombre_producto", ""),
            "price": d.get("precio_venta", ""),
            "currency_id": "CLP",
            "available_quantity": d.get("stock", ""),
            "listing_type_id": "gold_special",
            "condition": d.get("estado", "new").lower(),
            "description": d.get("descripcion", "")
        }
        row.update(ml_attrs)
        buffer_rows.append(row)

    headers.extend(sorted(dynamic_attrs))

    path = pathlib.Path(outfile)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in buffer_rows:
            writer.writerow(row)
    return path

if __name__ == "__main__":
    p = export_ml_csv()
    print(f"CSV generado: {p.resolve()}")