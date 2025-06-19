# ml/helpers.py
def attrs_dict_to_array(attrs_dict: dict) -> list[dict]:
    """Convierte el dict interno ➜ array que requiere ML."""
    arr = []
    for aid, data in attrs_dict.items():
        if not data:
            continue
        if isinstance(data, dict):
            arr.append({"id": aid, **data})
        else:
            arr.append({"id": aid, "value_name": str(data)})
    return arr
