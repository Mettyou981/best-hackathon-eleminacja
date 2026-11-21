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