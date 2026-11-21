import re
from datetime import date, datetime, timedelta

KEYWORDS_BOOST = ("kolokwium", "egzamin", "projekt", "oddanie", "sprawozdanie", "zaliczenie")


def parse_quick_add(raw_text: str) -> dict:
    """Parsuje tekst typu: 'Nauka Bazy Danych !wysoki @jutro #studia #pilne'"""
    text = raw_text.strip()

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