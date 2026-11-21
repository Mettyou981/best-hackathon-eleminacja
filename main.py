from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from storage import load_tasks, save_tasks
from smart import parse_quick_add, get_smart_focus_task, is_overdue
from gamification import GamificationManager, PRIORITY_POINTS
from datetime import date

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PRIO_COLORS = {
    "wysoki": "#e74c3c",
    "sredni": "#f39c12",
    "niski": "#2ecc71",
}


class WeeklyGoalDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_goal: int, on_confirm):
        super().__init__(parent)
        self.title("Cel na ten tydzień")
        self.geometry("400x260")
        self.resizable(False, False)
        self.grab_set()
        self.on_confirm = on_confirm
        self.confirmed = False

        ctk.CTkLabel(
            self,
            text="Jaki masz cel zadań na ten tydzień?",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self,
            text="Planuj z wyprzedzeniem: niski priorytet = 5 pkt,\nśredni = 4 pkt, wysoki = 3 pkt.",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa",
        ).pack(pady=(0, 12))

        presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        presets_frame.pack(pady=4)

        self.goal_entry = ctk.CTkEntry(self, width=120, justify="center", font=ctk.CTkFont(size=15, weight="bold"))
        self.goal_entry.insert(0, str(current_goal))
        self.goal_entry.pack(pady=8)

        for val in (3, 5, 7, 10):
            ctk.CTkButton(
                presets_frame,
                text=f"{val} zad.",
                width=65,
                fg_color="#34495e",
                command=lambda v=val: self._set_preset(v),
            ).pack(side="left", padx=4)

        ctk.CTkButton(self, text="Zatwierdź cel", width=160, command=self._save).pack(pady=(10, 15))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_preset(self, val: int):
        self.goal_entry.delete(0, "end")
        self.goal_entry.insert(0, str(val))

    def _save(self):
        try:
            goal = int(self.goal_entry.get().strip())
            if goal < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Nieprawidłowa wartość", "Podaj liczbę całkowitą większą od 0.", parent=self)
            return
        self.confirmed = True
        self.on_confirm(goal)
        self.destroy()

    def _on_close(self):
        if not self.confirmed:
            try:
                fallback = max(1, int(self.goal_entry.get().strip()))
            except ValueError:
                fallback = 3
            self.on_confirm(fallback)
        self.destroy()


class EditDialog(ctk.CTkToplevel):
    def __init__(self, parent, task: dict, on_save):
        super().__init__(parent)
        self.title(f"Edycja zadania #{task['id']}")
        self.geometry("420x430")
        self.grab_set()
        self.task = task
        self.on_save = on_save

        ctk.CTkLabel(self, text="Tytuł:").pack(anchor="w", padx=20, pady=(15, 2))
        self.title_entry = ctk.CTkEntry(self, width=380)
        self.title_entry.insert(0, task["tytul"])
        self.title_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Opis:").pack(anchor="w", padx=20, pady=(10, 2))
        self.desc_entry = ctk.CTkEntry(self, width=380)
        self.desc_entry.insert(0, task.get("opis", ""))
        self.desc_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Termin (RRRR-MM-DD lub puste):").pack(anchor="w", padx=20, pady=(10, 2))
        self.date_entry = ctk.CTkEntry(self, width=380)
        if task.get("termin"):
            self.date_entry.insert(0, task["termin"])
        self.date_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Priorytet:").pack(anchor="w", padx=20, pady=(10, 2))
        self.prio_menu = ctk.CTkOptionMenu(self, values=["niski", "sredni", "wysoki"], width=380)
        self.prio_menu.set(task.get("priorytet", "sredni"))
        self.prio_menu.pack(padx=20)

        ctk.CTkLabel(self, text="Tagi (oddzielone przecinkiem):").pack(anchor="w", padx=20, pady=(10, 2))
        self.tags_entry = ctk.CTkEntry(self, width=380)
        self.tags_entry.insert(0, ", ".join(task.get("tagi", [])))
        self.tags_entry.pack(padx=20)

        ctk.CTkButton(self, text="Zapisz zmiany", command=self.save).pack(pady=20)

    def save(self):
        new_title = self.title_entry.get().strip()
        if not new_title:
            messagebox.showwarning("Błąd", "Tytuł nie może być pusty.", parent=self)
            return
        self.task["tytul"] = new_title
        self.task["opis"] = self.desc_entry.get().strip()
        raw_date = self.date_entry.get().strip()
        self.task["termin"] = raw_date if raw_date else None
        self.task["priorytet"] = self.prio_menu.get()
        self.task["tagi"] = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        self.on_save()
        self.destroy()


class SmartPlannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1000x740")

        base_dir = Path(__file__).resolve().parent
        default_path = base_dir / "zadania.json"
        if default_path.exists():
            try:
                self.data = load_tasks(default_path)
                self.current_file = str(default_path)
            except Exception:
                self.data = {"wersja": 1, "zadania": []}
                self.current_file = None
        else:
            self.data = {"wersja": 1, "zadania": []}
            self.current_file = None
        self.filter_mode = ctk.StringVar(value="Wszystkie")
        self.search_var = ctk.StringVar(value="")
        self.search_var.trace_add("write", lambda *_: self.refresh_ui())
        self.prio_filter_var = ctk.StringVar(value="Priorytet: Wszystkie")
        self.date_filter_var = ctk.StringVar(value="Termin: Wszystkie")
        self.tag_filter_var = ctk.StringVar(value="Tag: Wszystkie")
        self.gamification = GamificationManager()
        self.last_event_text = "Wykonuj zadania z wyprzedzeniem (niski = 5 pkt, średni = 4 pkt, wysoki = 3 pkt)."

        self._build_ui()
        self.refresh_ui()
        self.after(250, self._startup_checks)

    def _startup_checks(self):
        if self.gamification.startup_notice:
            messagebox.showinfo("Podsumowanie tygodnia", self.gamification.startup_notice, parent=self)
        if self.gamification.needs_weekly_goal_prompt():
            self.open_goal_dialog()

    def open_goal_dialog(self):
        WeeklyGoalDialog(
            self,
            current_goal=self.gamification.state["weekly_goal"],
            on_confirm=self._apply_weekly_goal,
        )

    def _apply_weekly_goal(self, goal: int):
        self.gamification.set_weekly_goal(goal)
        self.last_event_text = f"Ustawiono cel tygodniowy: {goal} zadań."
        self.refresh_ui()

    def _simulate_week(self):
        summary = self.gamification.simulate_week_end()
        self.last_event_text = summary.replace("\n", " ")
        self.refresh_ui()
        messagebox.showinfo("Symulacja końca tygodnia", summary, parent=self)

    def _build_ui(self):
        # Górny pasek narzędziowy
        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=15, pady=(15, 6))

        ctk.CTkLabel(top_bar, text="SmartApp", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(top_bar, text="Zapisz jako JSON", width=130, command=self.export_json).pack(side="right", padx=(5, 12))
        ctk.CTkButton(top_bar, text="Zapisz JSON", width=110, command=self.save_current_json).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="Wczytaj JSON", width=120, fg_color="#2980b9", command=self.import_json).pack(side="right", padx=5)

        ctk.CTkSegmentedButton(
            top_bar,
            values=["Wszystkie", "Do zrobienia", "Po terminie", "Zrobione"],
            variable=self.filter_mode,
            command=lambda _: self.refresh_ui(),
        ).pack(side="right", padx=12)
        #Pasek z datą
        dni_tyg = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        dzis = date.today()
        _, nr_tygodnia, _ = dzis.isocalendar()
        date_text = f"📅 Dzisiaj: {dni_tyg[dzis.weekday()]}, {dzis.strftime('%d.%m.%Y')}  |  Tydzień #{nr_tygodnia}"
        date_bar = ctk.CTkFrame(self, height=30, fg_color="#16202a")
        date_bar.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(
            date_bar,
            text=date_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#85c1e9",
        ).pack(side="left", padx=12, pady=4)
        # Panel Grywalizacji: Liga Systematyczności + Tygodniowy Cel + Streak
        league_card = ctk.CTkFrame(self, fg_color="#1b2631", border_width=1, border_color="#2c3e50")
        league_card.pack(fill="x", padx=15, pady=6)

        left_gami = ctk.CTkFrame(league_card, fg_color="transparent")
        left_gami.pack(side="left", fill="x", expand=True, padx=14, pady=10)

        top_gami_row = ctk.CTkFrame(left_gami, fg_color="transparent")
        top_gami_row.pack(fill="x")

        self.league_badge = ctk.CTkLabel(
            top_gami_row,
            text="LIGA: BRĄZOWA",
            fg_color="#cd7f32",
            text_color="#111111",
            corner_radius=6,
            padx=10,
            pady=2,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.league_badge.pack(side="left")

        self.points_label = ctk.CTkLabel(
            top_gami_row,
            text="0 pkt",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.points_label.pack(side="left", padx=12)

        self.streak_label = ctk.CTkLabel(
            top_gami_row,
            text="🔥 Streak: 0 tyg.",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f39c12",
        )
        self.streak_label.pack(side="left", padx=12)

        self.goal_progress_label = ctk.CTkLabel(
            top_gami_row,
            text="Cel tygodnia: 0 / 3",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.goal_progress_label.pack(side="right", padx=6)

        self.goal_progress_bar = ctk.CTkProgressBar(left_gami, height=10)
        self.goal_progress_bar.pack(fill="x", pady=(8, 4))
        self.goal_progress_bar.set(0)

        self.gami_status_label = ctk.CTkLabel(
            left_gami,
            text=self.last_event_text,
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
            anchor="w",
        )
        self.gami_status_label.pack(fill="x")

        right_gami = ctk.CTkFrame(league_card, fg_color="transparent")
        right_gami.pack(side="right", padx=12, pady=10)

        ctk.CTkButton(
            right_gami,
            text="Zmień cel",
            width=135,
            height=28,
            fg_color="#34495e",
            command=self.open_goal_dialog,
        ).pack(pady=(0, 6))

        ctk.CTkButton(
            right_gami,
            text="Symuluj koniec tyg.",
            width=135,
            height=28,
            fg_color="#5d6d7e",
            command=self._simulate_week,
        ).pack()

        # Karta Smart Focus
        self.focus_frame = ctk.CTkFrame(self, fg_color="#1f2d3d", border_width=1, border_color="#3498db")
        self.focus_frame.pack(fill="x", padx=15, pady=6)

        self.focus_label = ctk.CTkLabel(
            self.focus_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            justify="left",
        )
        self.focus_label.pack(side="left", padx=15, pady=10)

        self.focus_done_btn = ctk.CTkButton(self.focus_frame, text="Odhacz teraz", width=110)
        self.focus_done_btn.pack(side="right", padx=15, pady=10)

        # Pasek Quick-Add
        add_bar = ctk.CTkFrame(self)
        add_bar.pack(fill="x", padx=15, pady=6)

        self.quick_entry = ctk.CTkEntry(
            add_bar,
            placeholder_text="Wpisz zadanie, np. Kolokwium z sieci !wysoki @jutro #studia i wciśnij Enter...",
            height=38,
        )
        self.quick_entry.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10)
        self.quick_entry.bind("<Return>", lambda _: self.add_task())

        ctk.CTkButton(add_bar, text="+ Dodaj", width=100, height=38, command=self.add_task).pack(side="right", padx=(0, 10))
        # Pasek wyszukiwania na żywo i filtrowania po wszystkich parametrach
        filter_bar = ctk.CTkFrame(self, fg_color="#1b2631")
        filter_bar.pack(fill="x", padx=15, pady=(2, 6))

        self.search_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self.search_var,
            placeholder_text="🔍 Szukaj po tytule, opisie, ID, dacie lub #tagu...",
            height=32,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=8)

        self.prio_filter_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["Priorytet: Wszystkie", "wysoki", "sredni", "niski"],
            variable=self.prio_filter_var,
            width=155,
            height=32,
            command=lambda _: self.refresh_ui(),
        )
        self.prio_filter_menu.pack(side="left", padx=4, pady=8)

        self.date_filter_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["Termin: Wszystkie", "Na dziś", "Po terminie", "Z terminem", "Bez terminu (null)"],
            variable=self.date_filter_var,
            width=165,
            height=32,
            command=lambda _: self.refresh_ui(),
        )
        self.date_filter_menu.pack(side="left", padx=4, pady=8)

        self.tag_filter_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["Tag: Wszystkie"],
            variable=self.tag_filter_var,
            width=145,
            height=32,
            command=lambda _: self.refresh_ui(),
        )
        self.tag_filter_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            filter_bar,
            text="✕ Reset",
            width=70,
            height=32,
            fg_color="#5d6d7e",
            command=self.reset_filters,
        ).pack(side="left", padx=(4, 10), pady=8)
        # Lista zadań
        self.task_list_frame = ctk.CTkScrollableFrame(self)
        self.task_list_frame.pack(fill="both", expand=True, padx=15, pady=(6, 15))

    def _next_id(self) -> int:
        tasks = self.data.get("zadania", [])
        return max((int(t["id"]) for t in tasks), default=0) + 1

    def add_task(self):
        raw = self.quick_entry.get().strip()
        if not raw:
            return
        parsed = parse_quick_add(raw)
        new_task = {
            "id": self._next_id(),
            "tytul": parsed["tytul"],
            "opis": "",
            "termin": parsed["termin"],
            "priorytet": parsed["priorytet"],
            "wykonane": False,
            "tagi": parsed["tagi"],
        }
        self.data["zadania"].append(new_task)
        self.quick_entry.delete(0, "end")
        self.refresh_ui()

    def toggle_task(self, task_id: int):
        for t in self.data["zadania"]:
            if t["id"] == task_id:
                t["wykonane"] = not t["wykonane"]
                if t["wykonane"]:
                    _, feedback = self.gamification.record_task_completed(t)
                    self.last_event_text = feedback
                else:
                    self.last_event_text = f"Cofnięto ukończenie: {t['tytul']}"
                break
        self.refresh_ui()

    def delete_task(self, task_id: int):
        self.data["zadania"] = [t for t in self.data["zadania"] if t["id"] != task_id]
        self.refresh_ui()

    def edit_task(self, task: dict):
        EditDialog(self, task, self.refresh_ui)

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("Pliki JSON", "*.json")])
        if not path:
            return

        has_existing_state = (
            self.current_file is not None
            or len(self.data.get("zadania", [])) > 0
            or self.gamification.state.get("completed_this_week", 0) > 0
        )
        if has_existing_state:
            confirmed = messagebox.askyesno(
                "Reset postępu tygodniowego",
                "Wczytanie nowej listy zadań usunie Twój postęp z bieżącego tygodnia "
                "(licznik wykonanych zadań oraz punkty zdobyte w tym tygodniu), "
                "aby zapobiec wielokrotnemu punktowaniu tych samych zadań.\n\n"
                "Czy na pewno chcesz wczytać nowy plik?",
                parent=self,
            )
            if not confirmed:
                return

        try:
            new_data = load_tasks(path)
        except Exception as e:
            messagebox.showerror("Błąd wczytywania", f"Nie udało się wczytać pliku:\n{e}", parent=self)
            return

        self.data = new_data
        self.current_file = path
        self.gamification.reset_weekly_progress()
        self.last_event_text = f"Wczytano nową listę ({Path(path).name}) — postęp tygodniowy został wyzerowany."
        self.refresh_ui()

    def save_current_json(self):
        if not self.current_file:
            self.export_json()
            return
        save_tasks(self.current_file, self.data)
        messagebox.showinfo("Zapisano", f"Zapisano zmiany w pliku:\n{self.current_file}")

    def export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="zadania.json",
            filetypes=[("Pliki JSON", "*.json")],
        )
        if not path:
            return
        save_tasks(path, self.data)
        self.current_file = path
        self.refresh_ui()
        messagebox.showinfo("Zapisano", f"Wyeksportowano zadania do:\n{path}")

    def reset_filters(self):
        self.filter_mode.set("Wszystkie")
        self.prio_filter_var.set("Priorytet: Wszystkie")
        self.date_filter_var.set("Termin: Wszystkie")
        self.tag_filter_var.set("Tag: Wszystkie")
        self.search_var.set("")
    def refresh_ui(self):
        file_status = Path(self.current_file).name if self.current_file else "Brak wczytanego pliku"
        self.title(f"SmartApp — {file_status} (zadań: {len(self.data['zadania'])})")

        # 1. Odśwież panel grywalizacji (Liga, Punkty, Streak, Cel tygodniowy)
        st = self.gamification.state
        league = self.gamification.get_league_info()
        self.league_badge.configure(text=f"🏆 LIGA: {league['name'].upper()}", fg_color=league["color"])

        if league["next_name"]:
            pts_txt = f"{st['points']} pkt (brakuje {league['pts_to_next']} pkt do ligi {league['next_name']})"
        else:
            pts_txt = f"{st['points']} pkt (Najwyższa liga!)"
        self.points_label.configure(text=pts_txt)
        self.streak_label.configure(text=f"🔥 Streak: {st['streak']} tyg.")

        done_wk = st["completed_this_week"]
        goal_wk = max(1, st["weekly_goal"])
        self.goal_progress_label.configure(text=f"Cel tygodnia: {done_wk} / {goal_wk}")
        self.goal_progress_bar.set(min(1.0, done_wk / goal_wk))
        self.gami_status_label.configure(text=self.last_event_text)

        # 2. Odśwież kartę Smart Focus
        best_task, reason = get_smart_focus_task(self.data["zadania"])
        if best_task:
            self.focus_label.configure(text=f"SMART FOCUS: {best_task['tytul']}\nPowód: {reason}")
            self.focus_done_btn.configure(state="normal", command=lambda tid=best_task["id"]: self.toggle_task(tid))
        else:
            self.focus_label.configure(text=f"SMART FOCUS: {reason}")
            self.focus_done_btn.configure(state="disabled")

        # 3. Dynamiczna aktualizacja listy dostępnych tagów w menu filtrowania
        all_tags = sorted({tag for task in self.data["zadania"] for tag in task.get("tagi", [])})
        tag_options = ["Tag: Wszystkie"] + [f"#{tag}" for tag in all_tags]
        self.tag_filter_menu.configure(values=tag_options)
        if self.tag_filter_var.get() not in tag_options:
            self.tag_filter_var.set("Tag: Wszystkie")

        # 4. Wyczyść obecną listę kart zadań
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        # 5. Pobierz aktywne kryteria filtrowania
        mode = self.filter_mode.get()
        prio_filter = self.prio_filter_var.get()
        date_filter = self.date_filter_var.get()
        tag_filter = self.tag_filter_var.get()
        query = self.search_var.get().strip().lower()
        today_str = date.today().isoformat()
        shown_count = 0

        # 6. Filtruj i renderuj zadania
        for t in self.data["zadania"]:
            # Filtr statusu (wykonane / po terminie)
            if mode == "Do zrobienia" and t["wykonane"]:
                continue
            if mode == "Zrobione" and not t["wykonane"]:
                continue
            if mode == "Po terminie" and not is_overdue(t):
                continue

            # Filtr priorytetu
            if prio_filter != "Priorytet: Wszystkie" and t.get("priorytet") != prio_filter:
                continue

            # Filtr terminu
            termin_val = t.get("termin")
            if date_filter == "Na dziś" and termin_val != today_str:
                continue
            if date_filter == "Po terminie" and not is_overdue(t):
                continue
            if date_filter == "Z terminem" and not termin_val:
                continue
            if date_filter == "Bez terminu (null)" and termin_val is not None:
                continue

            # Filtr tagu
            if tag_filter != "Tag: Wszystkie":
                clean_tag = tag_filter.lstrip("#")
                if clean_tag not in t.get("tagi", []):
                    continue

            # Wyszukiwarka na żywo (id, tytul, opis, termin, priorytet, tagi)
            if query:
                q_no_hash = query.lstrip("#")
                searchable = " ".join([
                    f"id:{t.get('id', '')}",
                    str(t.get("id", "")),
                    t.get("tytul", "").lower(),
                    t.get("opis", "").lower(),
                    str(termin_val or "").lower(),
                    t.get("priorytet", "").lower(),
                    " ".join(t.get("tagi", [])).lower(),
                ])
                if query not in searchable and q_no_hash not in searchable:
                    continue

            shown_count += 1

            # Karta pojedynczego zadania
            card = ctk.CTkFrame(self.task_list_frame)
            card.pack(fill="x", pady=4, padx=4)

            cb = ctk.CTkCheckBox(
                card,
                text="",
                width=24,
                command=lambda tid=t["id"]: self.toggle_task(tid),
            )
            if t["wykonane"]:
                cb.select()
            cb.pack(side="left", padx=(10, 5), pady=10)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, pady=6)

            title_text = f"✓ {t['tytul']}" if t["wykonane"] else t["tytul"]
            ctk.CTkLabel(
                info_frame,
                text=title_text,
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#888888" if t["wykonane"] else "#ffffff",
            ).pack(anchor="w")

            pts_value = PRIORITY_POINTS.get(t["priorytet"], 4)
            meta_parts = [f"ID: #{t['id']}", f"Priorytet: {t['priorytet'].upper()} (+{pts_value} pkt)"]
            if termin_val:
                overdue_tag = " [PO TERMINIE]" if is_overdue(t) else ""
                meta_parts.append(f"Termin: {termin_val}{overdue_tag}")
            if t.get("tagi"):
                meta_parts.append("Tagi: " + ", ".join(f"#{tag}" for tag in t["tagi"]))
            if t.get("opis"):
                meta_parts.append(f"Opis: {t['opis']}")

            ctk.CTkLabel(
                info_frame,
                text="  |  ".join(meta_parts),
                font=ctk.CTkFont(size=12),
                text_color="#e74c3c" if is_overdue(t) else "#aaaaaa",
            ).pack(anchor="w")

            prio_badge = ctk.CTkLabel(
                card,
                text=t["priorytet"].upper(),
                fg_color=PRIO_COLORS.get(t["priorytet"], "#555555"),
                corner_radius=6,
                width=70,
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            prio_badge.pack(side="right", padx=(5, 10))

            ctk.CTkButton(
                card,
                text="Usuń",
                width=65,
                fg_color="#c0392b",
                hover_color="#962d22",
                command=lambda tid=t["id"]: self.delete_task(tid),
            ).pack(side="right", padx=4)

            ctk.CTkButton(
                card,
                text="Edytuj",
                width=65,
                command=lambda task=t: self.edit_task(task),
            ).pack(side="right", padx=4)

        if shown_count == 0:
            ctk.CTkLabel(
                self.task_list_frame,
                text="Brak zadań spełniających wybrane kryteria filtrowania.",
                font=ctk.CTkFont(size=14),
                text_color="#888888",
            ).pack(pady=30)


if __name__ == "__main__":
    app = SmartPlannerApp()
    app.mainloop()