import json
from pathlib import Path

VALID_PRIORITIES = ("niski", "sredni", "wysoki")


def load_tasks(filepath: str | Path) -> dict:
    path = Path(filepath)
    if not path.exists():
        return {"wersja": 1, "zadania": []}

    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    tasks = data.get("zadania", [])
    for t in tasks:
        t.setdefault("opis", "")
        t.setdefault("termin", None)
        if t.get("priorytet") not in VALID_PRIORITIES:
            t["priorytet"] = "sredni"
        t.setdefault("wykonane", False)
        t.setdefault("tagi", [])

    return {"wersja": data.get("wersja", 1), "zadania": tasks}


def save_tasks(filepath: str | Path, data: dict) -> None:
    """Zapisuje zadania w ścisłym formacie pierwotnym (BEZ lokalizacji ani dodatkowych pól)."""
    clean_tasks = []
    for t in data.get("zadania", []):
        termin = t.get("termin")
        clean_tasks.append({
            "id": int(t["id"]),
            "tytul": str(t["tytul"]).strip(),
            "opis": str(t.get("opis") or ""),
            "termin": termin if termin else None,
            "priorytet": t["priorytet"] if t.get("priorytet") in VALID_PRIORITIES else "sredni",
            "wykonane": bool(t.get("wykonane", False)),
            "tagi": [str(tag).strip() for tag in (t.get("tagi") or []) if str(tag).strip()],
        })

    payload = {
        "wersja": int(data.get("wersja", 1)),
        "zadania": clean_tasks,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_locations(filepath: str | Path = "lokalizacje.json") -> dict[int, str]:
    """Wczytuje mapowanie lokalizacji zadań (id_zadania -> koordynaty/miasto) z osobnego pliku."""
    path = Path(filepath)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {int(k): str(v).strip() for k, v in raw.items() if v and str(v).strip()}
    except Exception:
        return {}


def save_locations(locations: dict[int, str], filepath: str | Path = "lokalizacje.json") -> None:
    """Zapisuje mapowanie lokalizacji w osobnym pliku lokalizacje.json bez ingerencji w pliki zadań."""
    path = Path(filepath)
    payload = {str(k): str(v).strip() for k, v in locations.items() if v and str(v).strip()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)