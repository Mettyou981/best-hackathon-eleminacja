import json
from datetime import date
from pathlib import Path

PRIORITY_POINTS = {
    "niski": 5,
    "sredni": 4,
    "wysoki": 3,
}

LEAGUES = [
    (0, "Brązowa", "#cd7f32"),
    (15, "Srebrna", "#bdc3c7"),
    (35, "Złota", "#f1c40f"),
    (60, "Platynowa", "#1abc9c"),
    (90, "Diamentowa", "#3498db"),
]

INACTIVITY_PENALTY = 10


def _current_iso_week(d: date | None = None) -> str:
    d = d or date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _week_index(week_str: str) -> int:
    year_s, week_s = week_str.split("-W")
    return int(year_s) * 53 + int(week_s)


class GamificationManager:
    def __init__(self, stats_path: Path | None = None):
        base_dir = Path(__file__).resolve().parent
        self.stats_path = stats_path or (base_dir / "gamification_stats.json")
        self.state = self._load_state()
        self.startup_notice = self._process_week_rollover()

    def _default_state(self) -> dict:
        return {
            "points": 0,
            "points_this_week":0,
            "streak": 0,
            "weekly_goal": 3,
            "goal_set_for_week": None,
            "active_week": _current_iso_week(),
            "completed_this_week": 0,
            "rewarded_tasks": [],
        }

    def _load_state(self) -> dict:
        if not self.stats_path.exists():
            return self._default_state()
        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = self._default_state()
            state.update(data)
            return state
        except Exception:
            return self._default_state()

    def save_state(self) -> None:
        with open(self.stats_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def get_league_info(self, points: int | None = None) -> dict:
        pts = self.state["points"] if points is None else points
        current_name, current_color, current_min = "Brązowa", "#cd7f32", 0
        next_name, next_min = None, None

        for idx, (min_pts, name, color) in enumerate(LEAGUES):
            if pts >= min_pts:
                current_name = name
                current_color = color
                current_min = min_pts
                if idx + 1 < len(LEAGUES):
                    next_min, next_name, _ = LEAGUES[idx + 1]
                else:
                    next_min, next_name = None, None

        return {
            "name": current_name,
            "color": current_color,
            "min_pts": current_min,
            "next_name": next_name,
            "next_min": next_min,
            "pts_to_next": (next_min - pts) if next_min is not None else 0,
        }

    def needs_weekly_goal_prompt(self) -> bool:
        return self.state.get("goal_set_for_week") != _current_iso_week()

    def set_weekly_goal(self, goal: int) -> None:
        self.state["weekly_goal"] = max(1, int(goal))
        self.state["goal_set_for_week"] = _current_iso_week()
        self.save_state()

    def _process_week_rollover(self) -> str | None:
        now_week = _current_iso_week()
        saved_week = self.state.get("active_week", now_week)
        if saved_week == now_week:
            return None

        old_league = self.get_league_info()["name"]
        weeks_diff = max(1, _week_index(now_week) - _week_index(saved_week))
        messages = []

        # Rozliczenie ostatniego aktywnego tygodnia
        if self.state["completed_this_week"] >= self.state["weekly_goal"]:
            self.state["streak"] += 1
            messages.append(
                f"Cel z tygodnia {saved_week} zrealizowany! Twój streak wynosi teraz {self.state['streak']} tyg."
            )
        else:
            self.state["streak"] = 0
            self.state["points"] = max(0, self.state["points"] - INACTIVITY_PENALTY)
            messages.append(
                f"Nie udało się dowieźć celu w tygodniu {saved_week} ({self.state['completed_this_week']}/{self.state['weekly_goal']}). "
                f"Streak wyzerowany, kara -{INACTIVITY_PENALTY} pkt."
            )

        # Dodatkowe kary za w pełni pominięte tygodnie (brak otwierania aplikacji)
        extra_missed = weeks_diff - 1
        if extra_missed > 0:
            extra_penalty = extra_missed * INACTIVITY_PENALTY
            self.state["streak"] = 0
            self.state["points"] = max(0, self.state["points"] - extra_penalty)
            messages.append(f"Brak aktywności przez kolejne {extra_missed} tyg.: -{extra_penalty} pkt.")

        new_league = self.get_league_info()["name"]
        if new_league != old_league:
            messages.append(f"Zmiana ligi: {old_league} → {new_league}!")

        self.state["active_week"] = now_week
        self.state["completed_this_week"] = 0
        self.state["points_this_week"] = 0
        self.save_state()
        return "\n".join(messages)

    def simulate_week_end(self) -> str:
        """Funkcja demonstracyjna do natychmiastowego przetestowania końca tygodnia na prezentacji."""
        old_league = self.get_league_info()["name"]
        goal = self.state["weekly_goal"]
        done = self.state["completed_this_week"]

        if done >= goal:
            self.state["streak"] += 1
            msg = (
                f"Podsumowanie tygodnia: Zrobiono {done}/{goal} zadań!\n"
                f"🔥 Streak rośnie do {self.state['streak']} tyg.!"
            )
        else:
            self.state["streak"] = 0
            self.state["points"] = max(0, self.state["points"] - INACTIVITY_PENALTY)
            msg = (
                f"Podsumowanie tygodnia: Zrobiono tylko {done}/{goal} zadań.\n"
                f"❄️ Streak wyzerowany, odjęto {INACTIVITY_PENALTY} pkt za brak systematyczności."
            )

        new_league = self.get_league_info()["name"]
        if new_league != old_league:
            msg += f"\n📉 Zmiana ligi: {old_league} → {new_league}!"

        self.state["completed_this_week"] = 0
        self.state["points_this_week"] = 0
        self.save_state()
        return msg

    def record_task_completed(self, task: dict) -> tuple[int, str]:
        """Przyznaje punkty za ukończenie zadania (z blokadą ponownego naliczania)."""
        signature = f"{task.get('id')}|{str(task.get('tytul', '')).strip().lower()}"
        if signature in self.state["rewarded_tasks"]:
            return 0, "To zadanie było już wcześniej punktowane (brak duplikacji punktów)."

        old_league = self.get_league_info()["name"]
        prio = task.get("priorytet", "sredni")
        earned = PRIORITY_POINTS.get(prio, 4)

        self.state["rewarded_tasks"].append(signature)
        self.state["points"] += earned
        self.state["points_this_week"] = self.state.get("points_this_week", 0) + earned
        self.state["completed_this_week"] += 1
        self.save_state()

        new_league = self.get_league_info()["name"]
        feedback = f"+{earned} pkt (priorytet {prio} — premia za planowanie!)"
        if new_league != old_league:
            feedback += f"  |  🎉 AWANS DO LIGI: {new_league.upper()}!"
        elif self.state["completed_this_week"] == self.state["weekly_goal"]:
            feedback += "  |  🎯 Cel tygodniowy osiągnięty!"

        return earned, feedback

    def reset_weekly_progress(self) -> None:
        """Resetuje postęp i punkty z bieżącego tygodnia przy wczytaniu nowej listy zadań."""
        weekly_pts = self.state.get("points_this_week", 0)
        self.state["points"] = max(0, self.state["points"] - weekly_pts)
        self.state["points_this_week"] = 0
        self.state["completed_this_week"] = 0
        self.state["rewarded_tasks"] = []
        self.save_state()