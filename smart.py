import re
from datetime import date, datetime, timedelta

KEYWORDS_BOOST = ("kolokwium", "egzamin", "projekt", "oddanie", "sprawozdanie", "zaliczenie")

KNOWN_CITIES = {
    "warszawa": (52.2297, 21.0122, "Warszawa"),
    "warsaw": (52.2297, 21.0122, "Warszawa"),
    "kraków": (50.0647, 19.9450, "Kraków"),
    "krakow": (50.0647, 19.9450, "Kraków"),
    "wrocław": (51.1079, 17.0385, "Wrocław"),
    "wroclaw": (51.1079, 17.0385, "Wrocław"),
    "poznań": (52.4064, 16.9252, "Poznań"),
    "poznan": (52.4064, 16.9252, "Poznań"),
    "gdańsk": (54.3520, 18.6466, "Gdańsk"),
    "gdansk": (54.3520, 18.6466, "Gdańsk"),
    "łódź": (51.7592, 19.4560, "Łódź"),
    "lodz": (51.7592, 19.4560, "Łódź"),
    "szczecin": (53.4285, 14.5528, "Szczecin"),
    "lublin": (51.2465, 22.5684, "Lublin"),
    "katowice": (50.2649, 19.0238, "Katowice"),
    "białystok": (53.1325, 23.1688, "Białystok"),
    "bialystok": (53.1325, 23.1688, "Białystok"),
    "bydgoszcz": (53.1235, 18.0084, "Bydgoszcz"),
    "toruń": (53.0138, 18.5984, "Toruń"),
    "torun": (53.0138, 18.5984, "Toruń"),
    "rzeszów": (50.0412, 21.9991, "Rzeszów"),
    "rzeszow": (50.0412, 21.9991, "Rzeszów"),
    "zakopane": (49.2992, 19.9496, "Zakopane"),
    "berlin": (52.5200, 13.4050, "Berlin"),
    "londyn": (51.5074, -0.1278, "Londyn"),
    "london": (51.5074, -0.1278, "Londyn"),
    "paryż": (48.8566, 2.3522, "Paryż"),
    "paris": (48.8566, 2.3522, "Paryż"),
    "rzym": (41.9028, 12.4964, "Rzym"),
    "rome": (41.9028, 12.4964, "Rzym"),
    "madryt": (40.4168, -3.7038, "Madryt"),
    "madrid": (40.4168, -3.7038, "Madryt"),
    "praga": (50.0755, 14.4378, "Praga"),
    "prague": (50.0755, 14.4378, "Praga"),
    "wiedeń": (48.2082, 16.3738, "Wiedeń"),
    "vienna": (48.2082, 16.3738, "Wiedeń"),
    "nowy jork": (40.7128, -74.0060, "Nowy Jork"),
    "new york": (40.7128, -74.0060, "Nowy Jork"),
    "tokio": (35.6762, 139.6503, "Tokio"),
    "tokyo": (35.6762, 139.6503, "Tokio"),
    "sydney": (-33.8688, 151.2093, "Sydney"),
    "pekin": (39.9042, 116.4074, "Pekin"),
    "beijing": (39.9042, 116.4074, "Pekin"),
    "san francisco": (37.7749, -122.4194, "San Francisco"),
    "kair": (30.0444, 31.2357, "Kair"),
    "cairo": (30.0444, 31.2357, "Kair"),
}


def parse_coordinates(raw_loc: str | None) -> tuple[float, float, str] | None:
    """Parsuje ciąg koordynatów lub nazwę miasta na (szerokość, długość, etykieta)."""
    if not raw_loc:
        return None
    s = str(raw_loc).strip()
    if not s:
        return None

    # Sprawdzenie czy wpisano nazwę znanego miasta
    s_lower = s.lower()
    for city_key, (c_lat, c_lon, c_name) in KNOWN_CITIES.items():
        if city_key in s_lower:
            return c_lat, c_lon, c_name

    # Sprawdzenie koordynatów w formacie: 52.23, 21.01 lub 52.23; 21.01
    coord_match = re.search(r"(-?\d+(?:\.\d+)?)[,\s;]+(-?\d+(?:\.\d+)?)", s)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                label_match = re.search(r"\((.*?)\)", s)
                label = label_match.group(1) if label_match else f"{lat:.2f}, {lon:.2f}"
                return lat, lon, label
        except (ValueError, TypeError):
            pass

    return None


def parse_quick_add(raw_text: str) -> dict:
    """Parsuje tekst typu: 'Nauka Bazy Danych !wysoki @jutro #studia #pilne ~Warszawa'"""
    text = raw_text.strip()

    # Lokalizacja (~miasto lub ~lat,lon lub loc:...)
    lokalizacja = None
    loc_match = re.search(r"(?:~|loc:|geo:)([\w\s\.,\-+]+?)(?=\s+[!@#~]|$)", text, re.IGNORECASE)
    if loc_match:
        lokalizacja = loc_match.group(1).strip()
        text = re.sub(r"(?:~|loc:|geo:)[\w\s\.,\-+]+?(?=\s+[!@#~]|$)", "", text, flags=re.IGNORECASE)

    # Tagi (#tag)
    tags = re.findall(r"#([\w\-]+)", text)
    text = re.sub(r"#[\w\-]+", "", text)

    # Priorytet (!wysoki, !sredni, !niski)
    prio_match = re.search(r"!(niski|sredni|wysoki)", text, re.IGNORECASE)
    priorytet = prio_match.group(1).lower() if prio_match else "sredni"
    text = re.sub(r"!(niski|sredni|wysoki)", "", text, flags=re.IGNORECASE)

    # Termin (@YYYY-MM-DD, @dzis, @jutro)
    termin = None
    date_match = re.search(r"@(\d{4}-\d{2}-\d{2}|dzis|dziś|jutro)", text, re.IGNORECASE)
    if date_match:
        token = date_match.group(1).lower()
        today = date.today()
        if token in ("dzis", "dziś"):
            termin = today.isoformat()
        elif token == "jutro":
            termin = (today + timedelta(days=1)).isoformat()
        else:
            termin = token
        text = re.sub(r"@(\d{4}-\d{2}-\d{2}|dzis|dziś|jutro)", "", text, flags=re.IGNORECASE)

    tytul = re.sub(r"\s+", " ", text).strip()
    return {
        "tytul": tytul or "Nowe zadanie",
        "termin": termin,
        "priorytet": priorytet,
        "tagi": tags,
        "lokalizacja": lokalizacja,
    }


def is_overdue(task: dict) -> bool:
    if task.get("wykonane") or not task.get("termin"):
        return False
    try:
        due = datetime.strptime(task["termin"], "%Y-%m-%d").date()
        return due < date.today()
    except ValueError:
        return False


def get_smart_focus_task(tasks: list[dict]) -> tuple[dict | None, str]:
    """Zwraca najlepiej punktowane niewykonane zadanie oraz krótkie uzasadnienie."""
    pending = [t for t in tasks if not t.get("wykonane")]
    if not pending:
        return None, "Wszystkie zadania zrobione! Czas na przerwę."

    today = date.today()
    best_task = None
    best_score = -1
    best_reason = ""

    prio_weights = {"wysoki": 50, "sredni": 25, "niski": 10}

    for t in pending:
        score = prio_weights.get(t.get("priorytet", "sredni"), 25)
        reasons = [f"priorytet: {t.get('priorytet')}"]

        if t.get("termin"):
            try:
                due = datetime.strptime(t["termin"], "%Y-%m-%d").date()
                days_left = (due - today).days
                if days_left < 0:
                    score += 100
                    reasons.append("PO TERMINIE!")
                elif days_left == 0:
                    score += 80
                    reasons.append("termin DZISIAJ")
                elif days_left <= 2:
                    score += 55
                    reasons.append(f"zostały {days_left} dni")
                elif days_left <= 5:
                    score += 30
            except ValueError:
                pass

        title_lower = t.get("tytul", "").lower()
        if any(kw in title_lower for kw in KEYWORDS_BOOST):
            score += 20
            reasons.append("ważny etap studiów")

        if score > best_score:
            best_score = score
            best_task = t
            best_reason = ", ".join(reasons)

    return best_task, best_reason