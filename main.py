import os
import sys
import subprocess
from pathlib import Path
from datetime import date, timedelta
import customtkinter as ctk
from tkinter import filedialog, messagebox
from storage import load_tasks, save_tasks, load_locations, save_locations
from smart import parse_quick_add, get_smart_focus_task, is_overdue, parse_coordinates, KNOWN_CITIES
from gamification import (
    GamificationManager,
    PRIORITY_POINTS,
    POMODORO_BONUS_POINTS,
    LEAGUES,
    INACTIVITY_PENALTY,
)
from kanban import KanbanBoardFrame, COLUMNS, target_date_for_column
from calendar_view import CalendarViewFrame
from globe_view import GlobeViewFrame
from reports_and_alerts import (
    export_weekly_summary_pdf,
    get_upcoming_24h_tasks,
    send_system_notification,
)
from jarvis_theme import JARVIS, JarvisParticleCanvas, JarvisArcReactor, get_inspo_image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PRIO_COLORS = {
    "wysoki": JARVIS["neon_red"],
    "sredni": JARVIS["neon_amber"],
    "niski": JARVIS["neon_green"],
}

POMODORO_WORK_SECONDS = 25 * 60
POMODORO_BREAK_SECONDS = 5 * 60


class WeeklyGoalDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_goal: int, on_confirm):
        super().__init__(parent)
        self.title("Cel na ten tydzień")
        self.geometry("400x260")
        self.resizable(False, False)
        self.configure(fg_color=JARVIS["glass_panel"])
        self.grab_set()
        self.on_confirm = on_confirm
        self.confirmed = False

        ctk.CTkLabel(
            self,
            text="Jaki masz cel zadań na ten tydzień?",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=JARVIS["cyan"],
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self,
            text="Planuj z wyprzedzeniem: niski priorytet = 5 pkt,\nśredni = 4 pkt, wysoki = 3 pkt.",
            font=ctk.CTkFont(size=12),
            text_color=JARVIS["text_muted"],
        ).pack(pady=(0, 12))

        presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        presets_frame.pack(pady=4)

        self.goal_entry = ctk.CTkEntry(
            self,
            width=120,
            justify="center",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.goal_entry.insert(0, str(current_goal))
        self.goal_entry.pack(pady=8)

        for val in (3, 5, 7, 10):
            ctk.CTkButton(
                presets_frame,
                text=f"{val} zad.",
                width=65,
                fg_color=JARVIS["btn_glass_bg"],
                hover_color=JARVIS["btn_glass_hover"],
                border_width=1,
                border_color=JARVIS["border_subtle"],
                text_color=JARVIS["text_ice"],
                command=lambda v=val: self._set_preset(v),
            ).pack(side="left", padx=4)

        ctk.CTkButton(
            self,
            text="Zatwierdź cel",
            width=160,
            fg_color=JARVIS["btn_cyan_bg"],
            hover_color=JARVIS["btn_cyan_hover"],
            border_width=1,
            border_color=JARVIS["cyan"],
            text_color=JARVIS["text_ice"],
            command=self._save,
        ).pack(pady=(10, 15))
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
        self.geometry("420x510")
        self.configure(fg_color=JARVIS["glass_panel"])
        self.grab_set()
        self.task = task
        self.on_save = on_save

        ctk.CTkLabel(self, text="Tytuł:", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(15, 2))
        self.title_entry = ctk.CTkEntry(
            self,
            width=380,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.title_entry.insert(0, task["tytul"])
        self.title_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Opis:", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(10, 2))
        self.desc_entry = ctk.CTkEntry(
            self,
            width=380,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.desc_entry.insert(0, task.get("opis", ""))
        self.desc_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Termin (RRRR-MM-DD lub puste):", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(10, 2))
        self.date_entry = ctk.CTkEntry(
            self,
            width=380,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        if task.get("termin"):
            self.date_entry.insert(0, task["termin"])
        self.date_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Priorytet:", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(10, 2))
        self.prio_menu = ctk.CTkOptionMenu(
            self,
            values=["niski", "sredni", "wysoki"],
            width=380,
            fg_color=JARVIS["input_bg"],
            button_color=JARVIS["btn_cyan_bg"],
            button_hover_color=JARVIS["btn_cyan_hover"],
            text_color=JARVIS["text_ice"],
        )
        self.prio_menu.set(task.get("priorytet", "sredni"))
        self.prio_menu.pack(padx=20)

        ctk.CTkLabel(self, text="Tagi (oddzielone przecinkiem):", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(10, 2))
        self.tags_entry = ctk.CTkEntry(
            self,
            width=380,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.tags_entry.insert(0, ", ".join(task.get("tagi", [])))
        self.tags_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Lokalizacja (np. 52.23, 21.01 lub Warszawa):", text_color=JARVIS["cyan"]).pack(anchor="w", padx=20, pady=(10, 2))
        self.loc_entry = ctk.CTkEntry(
            self,
            width=380,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        if task.get("lokalizacja"):
            self.loc_entry.insert(0, str(task["lokalizacja"]))
        self.loc_entry.pack(padx=20)

        ctk.CTkButton(
            self,
            text="Zapisz zmiany",
            fg_color=JARVIS["btn_cyan_bg"],
            hover_color=JARVIS["btn_cyan_hover"],
            border_width=1,
            border_color=JARVIS["cyan"],
            text_color=JARVIS["text_ice"],
            command=self.save,
        ).pack(pady=18)

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
        
        # Lokalizacja zapisywana jest OSOBNO w lokalizacje.json, nie w pliku JSON zadań
        raw_loc = self.loc_entry.get().strip()
        if hasattr(self.master, "locations"):
            tid = int(self.task["id"])
            if raw_loc:
                self.master.locations[tid] = raw_loc
                self.task["lokalizacja"] = raw_loc
            else:
                self.master.locations.pop(tid, None)
                self.task["lokalizacja"] = None
            save_locations(self.master.locations, self.master.locations_path)
        else:
            self.task["lokalizacja"] = raw_loc if raw_loc else None

        self.on_save()
        self.destroy()


class SmartPlannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1500x900")
        self.configure(fg_color=JARVIS["bg_root"])

        base_dir = Path(__file__).resolve().parent
        self.locations_path = base_dir / "lokalizacje.json"
        self.locations = load_locations(self.locations_path)

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

        self._link_locations_to_tasks()

        self.sidebar_visible = False
        self.bind("<Escape>", lambda _: self.toggle_sidebar() if self.sidebar_visible else None)

        # Stan wbudowanego timera Pomodoro (25/5 min)
        self.pomo_mode = "work"  # "work" albo "break"
        self.pomo_seconds_left = POMODORO_WORK_SECONDS
        self.pomo_running = False
        self.pomo_after_id: str | None = None
        self.current_focus_task: dict | None = None

        self.view_mode = ctk.StringVar(value="📋 Tablica")
        self.filter_mode = ctk.StringVar(value="Wszystkie")
        self.search_var = ctk.StringVar(value="")
        self.search_var.trace_add("write", lambda *_: self.refresh_ui())
        self.prio_filter_var = ctk.StringVar(value="Priorytet: Wszystkie")
        self.date_filter_var = ctk.StringVar(value="Termin: Wszystkie")
        self.tag_filter_var = ctk.StringVar(value="Tag: Wszystkie")

        self.gamification = GamificationManager()
        self.last_event_text = (
            f"Przeciągaj karty, odhaczaj zadania z wyprzedzeniem (+5/+4/+3 pkt) lub ukończ sesję Pomodoro (+{POMODORO_BONUS_POINTS} pkt)."
        )

        self._build_ui()
        self.refresh_ui()
        self.after(300, self._startup_checks)

    def _startup_checks(self):
        if self.gamification.startup_notice:
            messagebox.showinfo("Podsumowanie tygodnia", self.gamification.startup_notice, parent=self)
        if self.gamification.needs_weekly_goal_prompt():
            self.open_goal_dialog()
        self.check_deadline_notifications(manual=False)

    def _link_locations_to_tasks(self):
        """Łączy zadania w pamięci z osobnym plikiem lokalizacje.json bez modyfikowania struktury pliku JSON zadań."""
        for t in self.data.get("zadania", []):
            try:
                tid = int(t.get("id", 0))
            except (ValueError, TypeError):
                continue
            loc = self.locations.get(tid)
            if loc:
                t["lokalizacja"] = loc
            elif "lokalizacja" not in t:
                t["lokalizacja"] = None

    def check_deadline_notifications(self, manual: bool = True):
        """Sprawdza zadania z terminem do 24h (dziś/jutro) oraz zaległe i wysyła powiadomienie systemowe."""
        due_soon, overdue = get_upcoming_24h_tasks(self.data.get("zadania", []))
        if not due_soon and not overdue:
            if manual:
                messagebox.showinfo(
                    "Brak pilnych terminów",
                    "Wszystko pod kontrolą! Nie masz żadnych zadań z terminem w ciągu najbliższych 24 godzin.",
                    parent=self,
                )
            return

        parts = []
        if due_soon:
            titles = ", ".join(t["tytul"] for t in due_soon[:3])
            parts.append(f"Do 24h ({len(due_soon)}): {titles}")
        if overdue:
            titles = ", ".join(t["tytul"] for t in overdue[:3])
            parts.append(f"Po terminie ({len(overdue)}): {titles}")

        summary_msg = " | ".join(parts)
        send_system_notification("Podsieciowe Maskarady — Przypomnienie o terminach!", summary_msg)
        self.last_event_text = f"🔔 Przypomnienie: {summary_msg}"
        self.gami_status_label.configure(text=self.last_event_text)

        if manual:
            messagebox.showwarning("Zbliżające się terminy (24h)", "\n\n".join(parts), parent=self)

    def export_weekly_pdf(self):
        """Eksportuje podsumowanie tygodnia oraz listę zadań do pliku PDF."""
        default_name = f"raport_tygodniowy_{date.today().isoformat()}.pdf"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("Dokument PDF", "*.pdf")],
        )
        if not path:
            return

        try:
            saved_path = export_weekly_summary_pdf(
                filepath=path,
                tasks=self.data.get("zadania", []),
                gamification_state=self.gamification.state,
                league_info=self.gamification.get_league_info(),
            )
        except Exception as e:
            messagebox.showerror("Błąd eksportu PDF", f"Nie udało się wygenerować pliku PDF:\n{e}", parent=self)
            return

        self.last_event_text = f"📄 Wyeksportowano raport tygodniowy PDF: {saved_path.name}"
        self.gami_status_label.configure(text=self.last_event_text)

        if messagebox.askyesno(
            "Raport PDF gotowy",
            f"Zapisano podsumowanie tygodnia w pliku:\n{saved_path}\n\nCzy chcesz teraz otworzyć ten plik PDF?",
            parent=self,
        ):
            self._open_file_in_os(saved_path)

    def _open_file_in_os(self, filepath: Path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(filepath))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(filepath)])
            else:
                subprocess.Popen(["xdg-open", str(filepath)])
        except Exception:
            pass

    # === LOGIKA WBUDOWANEGO TIMERA POMODORO (25/5 MIN) ===
    def _format_pomo_time(self) -> str:
        mins, secs = divmod(max(0, self.pomo_seconds_left), 60)
        return f"{mins:02d}:{secs:02d}"

    def _update_pomodoro_display(self):
        time_str = self._format_pomo_time()
        if self.pomo_mode == "work":
            self.pomo_label.configure(
                text=f"🍅 Skupienie: {time_str}",
                text_color="#f39c12" if self.pomo_running else "#ecf0f1",
            )
            self.pomo_start_btn.configure(text="⏸ Pauza" if self.pomo_running else "▶ Start")
        else:
            self.pomo_label.configure(
                text=f"☕ Przerwa: {time_str}",
                text_color="#2ecc71",
            )
            self.pomo_start_btn.configure(text="⏸ Pauza" if self.pomo_running else "▶ Przerwa")

    def toggle_pomodoro(self):
        if self.pomo_running:
            self.pomo_running = False
            if self.pomo_after_id is not None:
                self.after_cancel(self.pomo_after_id)
                self.pomo_after_id = None
            self._update_pomodoro_display()
        else:
            self.pomo_running = True
            if self.pomo_mode == "work" and self.current_focus_task:
                self.last_event_text = f"🍅 Trwa sesja skupienia nad: „{self.current_focus_task['tytul']}” (nie przerywaj, aby zdobyć +{POMODORO_BONUS_POINTS} pkt)."
                self.gami_status_label.configure(text=self.last_event_text)
            self._update_pomodoro_display()
            self._tick_pomodoro()

    def reset_pomodoro(self):
        if self.pomo_after_id is not None:
            self.after_cancel(self.pomo_after_id)
            self.pomo_after_id = None
        self.pomo_running = False
        self.pomo_mode = "work"
        self.pomo_seconds_left = POMODORO_WORK_SECONDS
        self._update_pomodoro_display()

    def _tick_pomodoro(self):
        if not self.pomo_running:
            return

        if self.pomo_seconds_left > 0:
            self.pomo_seconds_left -= 1
            self._update_pomodoro_display()
            self.pomo_after_id = self.after(1000, self._tick_pomodoro)
            return

        # Koniec odliczania (00:00)
        self.pomo_running = False
        self.pomo_after_id = None
        try:
            self.bell()
        except Exception:
            pass

        if self.pomo_mode == "work":
            task_title = self.current_focus_task["tytul"] if self.current_focus_task else None
            earned, feedback = self.gamification.record_pomodoro_completed(task_title)
            self.last_event_text = feedback
            self.pomo_mode = "break"
            self.pomo_seconds_left = POMODORO_BREAK_SECONDS
            self._update_pomodoro_display()
            self.refresh_ui()
            send_system_notification(
                "Podsieciowe Maskarady — Sesja Pomodoro ukończona!",
                f"Zdobyto +{earned} pkt! Czas na 5 minut przerwy.",
            )
            messagebox.showinfo(
                "Sesja skupienia ukończona!",
                f"{feedback}\n\nTimer przełączył się na 5-minutową przerwę.",
                parent=self,
            )
        else:
            self.pomo_mode = "work"
            self.pomo_seconds_left = POMODORO_WORK_SECONDS
            self._update_pomodoro_display()
            send_system_notification(
                "Podsieciowe Maskarady — Koniec przerwy",
                "Wracamy do pracy! Możesz rozpocząć kolejną sesję 25 min.",
            )

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

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar_frame.place_forget()
            self.sidebar_visible = False
        else:
            self.sidebar_frame.place(x=0, y=0, relheight=1.0)
            self.sidebar_frame.lift()
            self.sidebar_visible = True

    def _on_particle_slider_change(self, value):
        count = int(value)
        if hasattr(self, "particle_slider_lbl"):
            self.particle_slider_lbl.configure(text=f"🌐 Cząsteczki: {count}")
        if hasattr(self, "particle_canvas"):
            self.particle_canvas.set_num_particles(count)

    def _on_window_resize(self, event):
        if event.widget == self:
            w = event.width
            h = event.height
            target_w = min(self._max_content_width, max(500, w - 40))
            for widget_name in ("top_bar", "tiles_row", "filter_bar", "view_switcher_box"):
                if hasattr(self, widget_name):
                    try:
                        getattr(self, widget_name).configure(width=target_w)
                    except Exception:
                        pass
            if hasattr(self, "workspace_frame") and hasattr(self, "_ws_y"):
                if "Sfera" not in self.view_mode.get():
                    ws_h = max(200, h - self._ws_y - 14)
                    try:
                        self.workspace_frame.configure(width=target_w, height=ws_h)
                    except Exception:
                        pass

    def _build_ui(self):
        # Maksymalna szerokość kontenera centralnego
        self._max_content_width = 1200

        # === TŁO CZĄSTECZKOWE: WIRUJĄCA 3D SFERA PLEXUS JARVIS (WARSTWA TŁA) ===
        # Umieszczone w oknie głównym jako warstwa tła, widoczna pod kafelkami i dookoła nich
        self.particle_canvas = JarvisParticleCanvas(self, num_particles=110)
        self.particle_canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # === LEWY WYSUWANY PASEK BOCZNY NA LIGI (NAKŁADKA OVERLAY) ===
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=265,
            fg_color=JARVIS["glass_panel"],
            border_width=2,
            border_color=JARVIS["cyan"],
            corner_radius=0,
        )
        self.sidebar_frame.pack_propagate(False)

        sb_header = ctk.CTkFrame(self.sidebar_frame, fg_color=JARVIS["glass_panel_alt"], corner_radius=0)
        sb_header.pack(fill="x")

        ctk.CTkLabel(
            sb_header,
            text=f"🏆 Ligi ({len(LEAGUES)})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=JARVIS["cyan"],
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            sb_header,
            text="◀",
            width=30,
            height=28,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.toggle_sidebar,
        ).pack(side="right", padx=10, pady=10)

        self.sb_summary_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=JARVIS["text_cyan"],
            justify="left",
            anchor="w",
        )
        self.sb_summary_label.pack(fill="x", padx=12, pady=(10, 6))

        self.sb_leagues_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.sb_leagues_scroll.pack(fill="both", expand=True, padx=6, pady=4)

        rules_box = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=JARVIS["glass_panel_alt"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            corner_radius=8,
        )
        rules_box.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            rules_box,
            text=(
                "Zasady punktacji:\n"
                "• Niski priorytet: +5 pkt\n"
                "• Średni priorytet: +4 pkt\n"
                "• Wysoki priorytet: +3 pkt\n"
                f"• Sesja Pomodoro 25 min: +{POMODORO_BONUS_POINTS} pkt\n"
                f"• Brak celu w tyg.: -{INACTIVITY_PENALTY} pkt"
            ),
            font=ctk.CTkFont(size=11),
            text_color=JARVIS["text_ice"],
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=8)

        # === GÓRNY PASEK — Arc Reactor HUD + Tytuł + Data + Slider Cząsteczek + Przyciski ===
        self.top_bar = ctk.CTkFrame(
            self,
            width=self._max_content_width,
            height=52,
            fg_color=JARVIS["glass_panel"],
            border_width=1,
            border_color=JARVIS["border_cyan"],
            corner_radius=10,
        )

        # Miniaturowy obracający się Reaktor Łukowy HUD (kółko) obok tytułu aplikacji
        self.arc_reactor = JarvisArcReactor(self.top_bar, size=38, bg=JARVIS["glass_panel"])
        self.arc_reactor.pack(side="left", padx=(12, 6), pady=6)

        ctk.CTkLabel(
            self.top_bar,
            text="PODSIECIOWE MASKARADY",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=JARVIS["cyan"],
        ).pack(side="left", padx=(0, 14), pady=10)

        # Wycentrowana data w top_barze z wyróżniającą się plakietką (tak jak na szkicu)
        dni_tyg = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        dzis = date.today()
        _, nr_tygodnia, _ = dzis.isocalendar()

        date_center = ctk.CTkFrame(
            self.top_bar,
            fg_color=JARVIS["glass_panel_alt"],
            corner_radius=8,
            border_width=1,
            border_color=JARVIS["border_cyan"],
        )
        date_center.pack(side="left", expand=True, pady=6)

        ctk.CTkLabel(
            date_center,
            text=f"📅  {dni_tyg[dzis.weekday()]}, {dzis.strftime('%d.%m.%Y')}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=JARVIS["text_ice"],
        ).pack(side="left", padx=(12, 8), pady=5)

        ctk.CTkLabel(
            date_center,
            text=f"Tydzień #{nr_tygodnia}",
            fg_color=JARVIS["btn_cyan_bg"],
            text_color=JARVIS["text_ice"],
            corner_radius=5,
            padx=8,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=(0, 10), pady=5)

        # Przyciski po prawej — półprzezroczyste szklane przyciski z delikatnym obramowaniem
        ctk.CTkButton(
            self.top_bar,
            text="Zapisz jako JSON",
            width=115,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.export_json,
        ).pack(side="right", padx=(4, 14), pady=10)

        ctk.CTkButton(
            self.top_bar,
            text="Zapisz JSON",
            width=95,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.save_current_json,
        ).pack(side="right", padx=4, pady=10)

        ctk.CTkButton(
            self.top_bar,
            text="Wczytaj JSON",
            width=105,
            fg_color=JARVIS["btn_cyan_bg"],
            hover_color=JARVIS["btn_cyan_hover"],
            border_width=1,
            border_color=JARVIS["cyan"],
            text_color=JARVIS["text_ice"],
            command=self.import_json,
        ).pack(side="right", padx=4, pady=10)

        ctk.CTkButton(
            self.top_bar,
            text="📄 Raport PDF",
            width=105,
            fg_color="#3a1c54",
            hover_color="#532777",
            border_width=1,
            border_color="#9b59b6",
            text_color=JARVIS["text_ice"],
            command=self.export_weekly_pdf,
        ).pack(side="right", padx=4, pady=10)

        ctk.CTkButton(
            self.top_bar,
            text="🔔",
            width=36,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=lambda: self.check_deadline_notifications(manual=True),
        ).pack(side="right", padx=4, pady=10)

        # Kontrolka cząsteczek tła ze sliderem (wymóg: slider zmieniający ich ilość w sferze)
        particle_ctrl = ctk.CTkFrame(
            self.top_bar,
            fg_color=JARVIS["glass_panel_alt"],
            corner_radius=8,
            border_width=1,
            border_color=JARVIS["border_cyan"],
        )
        particle_ctrl.pack(side="right", padx=(4, 6), pady=8)

        self.particle_slider_lbl = ctk.CTkLabel(
            particle_ctrl,
            text=f"🌐 Cząsteczki: {self.particle_canvas.num_particles}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=JARVIS["cyan"],
        )
        self.particle_slider_lbl.pack(side="left", padx=(8, 4), pady=4)

        self.particle_slider = ctk.CTkSlider(
            particle_ctrl,
            from_=30,
            to=300,
            number_of_steps=54,
            width=90,
            height=14,
            progress_color=JARVIS["cyan"],
            button_color=JARVIS["cyan"],
            button_hover_color=JARVIS["text_ice"],
            command=self._on_particle_slider_change,
        )
        self.particle_slider.set(self.particle_canvas.num_particles)
        self.particle_slider.pack(side="left", padx=(2, 8), pady=4)

        # === TRZY KAFELKI W JEDNYM RZĘDZIE ===
        # Dodawanie zadania jest znacznie szersze (weight=5), a Liga i Smart Focus węższe (weight=3)
        TILE_HEIGHT = 172
        self.tiles_row = ctk.CTkFrame(
            self,
            width=self._max_content_width,
            height=TILE_HEIGHT,
            fg_color="transparent",
        )
        tiles_row = self.tiles_row
        self.tiles_row.grid_columnconfigure(0, weight=5, uniform="tile_col")
        self.tiles_row.grid_columnconfigure(1, weight=3, uniform="tile_col")
        self.tiles_row.grid_columnconfigure(2, weight=3, uniform="tile_col")

        # --- KAFELEK 1: Dodawanie zadania (SZEROKI z osobnymi polami na priorytet, datę, # i lokalizację) ---
        add_tile = ctk.CTkFrame(
            tiles_row,
            fg_color=JARVIS["glass_panel"],
            corner_radius=10,
            border_width=1,
            border_color=JARVIS["border_cyan"],
            height=TILE_HEIGHT,
        )
        add_tile.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        add_tile.pack_propagate(False)

        ctk.CTkLabel(
            add_tile,
            text="➕  Dodaj nowe zadanie",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=JARVIS["cyan"],
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 4))

        # Wiersz 1: Tytuł zadania
        self.quick_entry = ctk.CTkEntry(
            add_tile,
            placeholder_text="Wpisz treść / tytuł zadania...",
            height=32,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.quick_entry.pack(fill="x", padx=14, pady=(0, 6))
        self.quick_entry.bind("<Return>", lambda _: self.add_task())

        # Wiersz 2: Osobne pola (Priorytet, Data/Termin, Tagi, Lokalizacja / Koordynaty)
        fields_row = ctk.CTkFrame(add_tile, fg_color="transparent")
        fields_row.pack(fill="x", padx=14, pady=(0, 6))

        self.add_prio_menu = ctk.CTkOptionMenu(
            fields_row,
            values=["sredni", "wysoki", "niski"],
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["input_bg"],
            button_color=JARVIS["btn_cyan_bg"],
            button_hover_color=JARVIS["btn_cyan_hover"],
            text_color=JARVIS["text_ice"],
        )
        self.add_prio_menu.set("sredni")
        self.add_prio_menu.pack(side="left", padx=(0, 4))

        self.add_date_entry = ctk.CTkEntry(
            fields_row,
            placeholder_text="📅 Termin (@jutro)",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.add_date_entry.pack(side="left", fill="x", expand=True, padx=4)

        self.add_tags_entry = ctk.CTkEntry(
            fields_row,
            placeholder_text="#tagi",
            height=28,
            width=95,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.add_tags_entry.pack(side="left", padx=4)

        self.add_loc_entry = ctk.CTkEntry(
            fields_row,
            placeholder_text="📍 Koordynaty / miasto",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.add_loc_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Wiersz 3: Przycisk dodawania zadania
        ctk.CTkButton(
            add_tile,
            text="+ Dodaj zadanie do planera",
            height=30,
            fg_color=JARVIS["btn_cyan_bg"],
            hover_color=JARVIS["btn_cyan_hover"],
            border_width=1,
            border_color=JARVIS["cyan"],
            text_color=JARVIS["text_ice"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.add_task,
        ).pack(fill="x", padx=14, pady=(0, 10))

        # --- KAFELEK 2: Liga (WĘŻSZY) ---
        league_tile = ctk.CTkFrame(
            tiles_row,
            fg_color=JARVIS["glass_panel"],
            corner_radius=10,
            border_width=1,
            border_color=JARVIS["border_cyan"],
            height=TILE_HEIGHT,
        )
        league_tile.grid(row=0, column=1, sticky="nsew", padx=4)
        league_tile.pack_propagate(False)

        league_header = ctk.CTkFrame(league_tile, fg_color="transparent")
        league_header.pack(fill="x", padx=12, pady=(10, 2))

        self.league_badge = ctk.CTkLabel(
            league_header,
            text="LIGA: BRĄZOWA",
            fg_color="#cd7f32",
            text_color="#111111",
            corner_radius=6,
            padx=8,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold"),
            cursor="hand2",
        )
        self.league_badge.pack(side="left")
        self.league_badge.bind("<Button-1>", lambda _: self.toggle_sidebar())

        self.sidebar_toggle_btn = ctk.CTkButton(
            league_header,
            text="☰",
            width=32,
            height=26,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["cyan"],
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.toggle_sidebar,
        )
        self.sidebar_toggle_btn.pack(side="right")

        stats_row = ctk.CTkFrame(league_tile, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=(1, 1))

        self.points_label = ctk.CTkLabel(
            stats_row,
            text="0 pkt",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=JARVIS["cyan"],
        )
        self.points_label.pack(side="left")

        self.streak_label = ctk.CTkLabel(
            stats_row,
            text="🔥 0 tyg.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=JARVIS["neon_amber"],
        )
        self.streak_label.pack(side="right")

        self.goal_progress_label = ctk.CTkLabel(
            league_tile,
            text="Cel tygodnia: 0 / 3",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=JARVIS["text_ice"],
            anchor="w",
        )
        self.goal_progress_label.pack(fill="x", padx=12, pady=(1, 1))

        self.goal_progress_bar = ctk.CTkProgressBar(
            league_tile,
            height=7,
            progress_color=JARVIS["cyan"],
            fg_color=JARVIS["input_bg"],
        )
        self.goal_progress_bar.pack(fill="x", padx=12, pady=(0, 2))
        self.goal_progress_bar.set(0)

        self.gami_status_label = ctk.CTkLabel(
            league_tile,
            text=self.last_event_text,
            font=ctk.CTkFont(size=10),
            text_color=JARVIS["text_muted"],
            anchor="w",
            wraplength=270,
        )
        self.gami_status_label.pack(fill="x", padx=12, pady=(0, 4))

        league_btns = ctk.CTkFrame(league_tile, fg_color="transparent")
        league_btns.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkButton(
            league_btns,
            text="Zmień cel",
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.open_goal_dialog,
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            league_btns,
            text="Symuluj",
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self._simulate_week,
        ).pack(side="right", fill="x", expand=True, padx=(3, 0))

        # --- KAFELEK 3: Smart Focus + Pomodoro (WĘŻSZY) ---
        self.focus_frame = ctk.CTkFrame(
            tiles_row,
            fg_color=JARVIS["glass_panel_focus"],
            corner_radius=10,
            border_width=1,
            border_color=JARVIS["cyan"],
            height=TILE_HEIGHT,
        )
        self.focus_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self.focus_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.focus_frame,
            text="🎯  Smart Focus",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=JARVIS["cyan"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))

        self.focus_label = ctk.CTkLabel(
            self.focus_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            justify="left",
            anchor="w",
            wraplength=270,
            text_color=JARVIS["text_ice"],
        )
        self.focus_label.pack(fill="x", padx=12, pady=(0, 4))

        pomo_box = ctk.CTkFrame(
            self.focus_frame,
            fg_color=JARVIS["input_bg"],
            border_width=1,
            border_color=JARVIS["neon_amber"],
            corner_radius=6,
        )
        pomo_box.pack(fill="x", padx=12, pady=(0, 6))

        self.pomo_label = ctk.CTkLabel(
            pomo_box,
            text="🍅 25:00",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=JARVIS["text_ice"],
        )
        self.pomo_label.pack(side="left", padx=(8, 4), pady=4)

        self.pomo_start_btn = ctk.CTkButton(
            pomo_box,
            text="▶ Start",
            width=58,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#854600",
            hover_color="#a85800",
            border_width=1,
            border_color=JARVIS["neon_amber"],
            command=self.toggle_pomodoro,
        )
        self.pomo_start_btn.pack(side="left", padx=2, pady=4)

        self.pomo_reset_btn = ctk.CTkButton(
            pomo_box,
            text="↺ Reset",
            width=54,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.reset_pomodoro,
        )
        self.pomo_reset_btn.pack(side="left", padx=2, pady=4)

        self.focus_done_btn = ctk.CTkButton(
            self.focus_frame,
            text="✓ Odhacz zadanie",
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#006655",
            hover_color="#008870",
            border_width=1,
            border_color=JARVIS["neon_green"],
            text_color="#ffffff",
        )
        self.focus_done_btn.pack(fill="x", padx=12, pady=(0, 8))

        # === SEKCJA: Wyszukiwanie + Filtry ===
        self.filter_bar = ctk.CTkFrame(
            self,
            width=self._max_content_width,
            height=48,
            fg_color=JARVIS["glass_panel"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            corner_radius=10,
        )

        self.search_entry = ctk.CTkEntry(
            self.filter_bar,
            textvariable=self.search_var,
            placeholder_text="🔍 Szukaj po tytule, opisie, ID, dacie, tagu lub lokalizacji...",
            height=32,
            width=270,
            fg_color=JARVIS["input_bg"],
            border_color=JARVIS["input_border"],
            text_color=JARVIS["text_ice"],
        )
        self.search_entry.pack(side="left", padx=(12, 6), pady=8)

        ctk.CTkSegmentedButton(
            self.filter_bar,
            values=["Wszystkie", "Do zrobienia", "Po terminie", "Zrobione"],
            variable=self.filter_mode,
            command=lambda _: self.refresh_ui(),
            selected_color=JARVIS["btn_cyan_bg"],
            selected_hover_color=JARVIS["btn_cyan_hover"],
            unselected_color=JARVIS["btn_glass_bg"],
            unselected_hover_color=JARVIS["btn_glass_hover"],
            text_color=JARVIS["text_ice"],
        ).pack(side="left", padx=6, pady=8)

        self.prio_filter_menu = ctk.CTkOptionMenu(
            self.filter_bar,
            values=["Priorytet: Wszystkie", "wysoki", "sredni", "niski"],
            variable=self.prio_filter_var,
            width=150,
            height=30,
            command=lambda _: self.refresh_ui(),
            fg_color=JARVIS["input_bg"],
            button_color=JARVIS["btn_cyan_bg"],
            button_hover_color=JARVIS["btn_cyan_hover"],
            text_color=JARVIS["text_ice"],
        )
        self.prio_filter_menu.pack(side="left", padx=4, pady=8)

        self.date_filter_menu = ctk.CTkOptionMenu(
            self.filter_bar,
            values=["Termin: Wszystkie", "Na dziś", "Po terminie", "Z terminem", "Bez terminu (null)"],
            variable=self.date_filter_var,
            width=160,
            height=30,
            command=lambda _: self.refresh_ui(),
            fg_color=JARVIS["input_bg"],
            button_color=JARVIS["btn_cyan_bg"],
            button_hover_color=JARVIS["btn_cyan_hover"],
            text_color=JARVIS["text_ice"],
        )
        self.date_filter_menu.pack(side="left", padx=4, pady=8)

        self.tag_filter_menu = ctk.CTkOptionMenu(
            self.filter_bar,
            values=["Tag: Wszystkie"],
            variable=self.tag_filter_var,
            width=140,
            height=30,
            command=lambda _: self.refresh_ui(),
            fg_color=JARVIS["input_bg"],
            button_color=JARVIS["btn_cyan_bg"],
            button_hover_color=JARVIS["btn_cyan_hover"],
            text_color=JARVIS["text_ice"],
        )
        self.tag_filter_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            self.filter_bar,
            text="✕ Reset",
            width=65,
            height=30,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.reset_filters,
        ).pack(side="left", padx=(4, 12), pady=8)

        # === WYRÓŻNIAJĄCY SIĘ, WIĘKSZY PRZEŁĄCZNIK WIDOKU NAD SAMYM WIDOKIEM ===
        self.view_switcher_box = ctk.CTkFrame(
            self,
            width=self._max_content_width,
            height=42,
            fg_color="transparent",
        )

        self.view_switcher = ctk.CTkSegmentedButton(
            self.view_switcher_box,
            values=["📋 Tablica", "📅 Kalendarz", "📝 Lista", "🌍 Globus 3D", "🌐 Sfera 3D"],
            variable=self.view_mode,
            command=lambda _: self.refresh_ui(),
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color=JARVIS["btn_cyan_bg"],
            selected_hover_color=JARVIS["btn_cyan_hover"],
            unselected_color=JARVIS["glass_panel"],
            unselected_hover_color=JARVIS["glass_panel_alt"],
            text_color=JARVIS["text_ice"],
            corner_radius=8,
        )
        self.view_switcher.pack(anchor="center")

        # === KONTENER ROBOCZY (Tablica Kanban / Kalendarz / Lista / Globus 3D) ===
        self.workspace_frame = ctk.CTkFrame(
            self,
            width=self._max_content_width,
            height=520,
            fg_color="transparent",
        )

        # Pozycjonowanie sekcji interfejsu bezpośrednio na oknie nad animowaną sferą cząsteczkową w tle
        self._ws_y = 358
        self.top_bar.place(relx=0.5, y=12, anchor="n")
        self.tiles_row.place(relx=0.5, y=72, anchor="n")
        self.filter_bar.place(relx=0.5, y=252, anchor="n")
        self.view_switcher_box.place(relx=0.5, y=308, anchor="n")
        self.workspace_frame.place(relx=0.5, y=self._ws_y, anchor="n")

        self.bind("<Configure>", self._on_window_resize)

        self.kanban_board = KanbanBoardFrame(
            self.workspace_frame,
            on_move_task=self.move_task_to_column,
            on_toggle_task=self.toggle_task,
            on_edit_task=self.edit_task,
            on_delete_task=self.delete_task,
            on_add_in_column=self.quick_add_in_column,
        )

        self.calendar_view = CalendarViewFrame(
            self.workspace_frame,
            on_toggle_task=self.toggle_task,
            on_edit_task=self.edit_task,
            on_delete_task=self.delete_task,
            on_add_on_date=self.quick_add_on_date,
        )

        self.task_list_frame = ctk.CTkScrollableFrame(self.workspace_frame)

        self.globe_view = GlobeViewFrame(
            self.workspace_frame,
            on_toggle_task=self.toggle_task,
            on_edit_task=self.edit_task,
            on_delete_task=self.delete_task,
            on_add_with_loc=self.quick_add_with_loc,
        )

    def _render_sidebar(self):
        pts = self.gamification.state["points"]
        current_league = self.gamification.get_league_info()["name"]
        unlocked_count = sum(1 for min_pts, _, _ in LEAGUES if pts >= min_pts)

        self.sb_summary_label.configure(
            text=f"Twoje punkty: {pts} pkt\nOdblokowano: {unlocked_count} z {len(LEAGUES)} lig"
        )

        for widget in self.sb_leagues_scroll.winfo_children():
            widget.destroy()

        # Wyświetlamy od najwyższej ligi (Diamentowa) w dół do Brązowej
        for idx in range(len(LEAGUES) - 1, -1, -1):
            min_pts, name, color = LEAGUES[idx]
            is_current = (name == current_league)
            is_unlocked = (pts >= min_pts)

            card = ctk.CTkFrame(
                self.sb_leagues_scroll,
                fg_color=JARVIS["glass_panel_alt"] if is_current else (JARVIS["glass_panel"] if is_unlocked else JARVIS["input_bg"]),
                border_width=2 if is_current else 1,
                border_color=color if is_current else (JARVIS["border_cyan"] if is_unlocked else JARVIS["border_subtle"]),
                corner_radius=8,
            )
            card.pack(fill="x", pady=5, padx=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            badge = ctk.CTkLabel(
                top_row,
                text=name.upper(),
                fg_color=color if is_unlocked else "#3b4652",
                text_color="#111111" if is_unlocked else "#bdc3c7",
                corner_radius=5,
                padx=8,
                pady=1,
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            badge.pack(side="left")

            ctk.CTkLabel(
                top_row,
                text=f"od {min_pts} pkt",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#d0d3d4" if is_unlocked else "#7f8c8d",
            ).pack(side="right")

            if is_current:
                status_txt = "★ TWOJA OBECNA LIGA"
                status_col = color
            elif is_unlocked:
                status_txt = "✓ Zdobyta"
                status_col = "#2ecc71"
            else:
                missing = min_pts - pts
                status_txt = f"🔒 Brakuje: {missing} pkt"
                status_col = "#f39c12"

            ctk.CTkLabel(
                card,
                text=status_txt,
                font=ctk.CTkFont(size=12, weight="bold" if (is_current or not is_unlocked) else "normal"),
                text_color=status_col,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(2, 8))

        if self.sidebar_visible:
            self.sidebar_frame.lift()

    def _next_id(self) -> int:
        tasks = self.data.get("zadania", [])
        return max((int(t["id"]) for t in tasks), default=0) + 1

    def quick_add_with_loc(self, lat: float, lon: float):
        if hasattr(self, "add_loc_entry"):
            self.add_loc_entry.delete(0, "end")
            self.add_loc_entry.insert(0, f"{lat:.2f}, {lon:.2f}")
        if hasattr(self, "quick_entry"):
            self.quick_entry.focus()

    def add_task(self):
        raw = self.quick_entry.get().strip()
        if not raw:
            return
        parsed = parse_quick_add(raw)

        # Osobne pola formularza mają pierwszeństwo i wzbogacają zadanie
        prio = self.add_prio_menu.get() if hasattr(self, "add_prio_menu") else parsed["priorytet"]
        raw_date = self.add_date_entry.get().strip() if hasattr(self, "add_date_entry") else ""
        if raw_date:
            today = date.today()
            if raw_date.lower() in ("dzis", "dziś"):
                termin = today.isoformat()
            elif raw_date.lower() == "jutro":
                termin = (today + timedelta(days=1)).isoformat()
            else:
                termin = raw_date
        else:
            termin = parsed["termin"]

        raw_tags = self.add_tags_entry.get().strip() if hasattr(self, "add_tags_entry") else ""
        explicit_tags = [t.strip().lstrip("#") for t in raw_tags.split(",") if t.strip()]
        all_tags = list(dict.fromkeys(parsed["tagi"] + explicit_tags))

        raw_loc = self.add_loc_entry.get().strip() if hasattr(self, "add_loc_entry") else ""
        lokalizacja = raw_loc or parsed.get("lokalizacja")

        tid = self._next_id()
        new_task = {
            "id": tid,
            "tytul": parsed["tytul"],
            "opis": "",
            "termin": termin,
            "priorytet": prio,
            "wykonane": False,
            "tagi": all_tags,
            "lokalizacja": lokalizacja,
        }
        self.data["zadania"].append(new_task)
        if lokalizacja:
            self.locations[tid] = lokalizacja
            save_locations(self.locations, self.locations_path)

        self.quick_entry.delete(0, "end")
        if hasattr(self, "add_date_entry"):
            self.add_date_entry.delete(0, "end")
        if hasattr(self, "add_tags_entry"):
            self.add_tags_entry.delete(0, "end")
        if hasattr(self, "add_loc_entry"):
            self.add_loc_entry.delete(0, "end")
        self.refresh_ui()

    def quick_add_in_column(self, col_key: str):
        col_names = {k: name for k, name, _ in COLUMNS}
        dialog = ctk.CTkInputDialog(
            text=f"Wpisz treść zadania dla kolumny „{col_names.get(col_key, '')}”\n(możesz użyć !wysoki / !niski oraz #tag):",
            title="Dodaj zadanie w kolumnie",
        )
        raw = dialog.get_input()
        if not raw or not raw.strip():
            return
        parsed = parse_quick_add(raw)
        is_done_col = (col_key == "done")
        tid = self._next_id()
        loc = parsed.get("lokalizacja")
        new_task = {
            "id": tid,
            "tytul": parsed["tytul"],
            "opis": "",
            "termin": parsed["termin"] if is_done_col else (parsed["termin"] or target_date_for_column(col_key)),
            "priorytet": parsed["priorytet"],
            "wykonane": is_done_col,
            "tagi": parsed["tagi"],
            "lokalizacja": loc,
        }
        self.data["zadania"].append(new_task)
        if loc:
            self.locations[tid] = loc
            save_locations(self.locations, self.locations_path)

        if is_done_col:
            _, feedback = self.gamification.record_task_completed(new_task)
            self.last_event_text = feedback
        self.refresh_ui()

    def move_task_to_column(self, task: dict, target_col: str):
        col_names = {k: name for k, name, _ in COLUMNS}
        if target_col == "done":
            if not task.get("wykonane"):
                task["wykonane"] = True
                _, feedback = self.gamification.record_task_completed(task)
                self.last_event_text = f"Ukończono „{task['tytul']}” → {feedback}"
            self.refresh_ui()
            return

        was_done = task.get("wykonane", False)
        task["wykonane"] = False
        new_date = target_date_for_column(target_col)
        task["termin"] = new_date
        date_info = new_date if new_date else "null (brak terminu)"
        prefix = "Przywrócono i przeniesiono" if was_done else "Przeniesiono"
        self.last_event_text = f"{prefix} „{task['tytul']}” → {col_names.get(target_col)} (nowy termin: {date_info})."
        self.refresh_ui()

    def quick_add_on_date(self, date_str: str):
        dialog = ctk.CTkInputDialog(
            text=f"Wpisz treść zadania na dzień {date_str}\n(możesz użyć !wysoki / !niski oraz #tag):",
            title="Dodaj zadanie w kalendarzu",
        )
        raw = dialog.get_input()
        if not raw or not raw.strip():
            return
        parsed = parse_quick_add(raw)
        tid = self._next_id()
        loc = parsed.get("lokalizacja")
        new_task = {
            "id": tid,
            "tytul": parsed["tytul"],
            "opis": "",
            "termin": parsed["termin"] or date_str,
            "priorytet": parsed["priorytet"],
            "wykonane": False,
            "tagi": parsed["tagi"],
            "lokalizacja": loc,
        }
        self.data["zadania"].append(new_task)
        if loc:
            self.locations[tid] = loc
            save_locations(self.locations, self.locations_path)

        self.last_event_text = f"Dodano zadanie „{new_task['tytul']}” na dzień {new_task['termin']}."
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
        if int(task_id) in self.locations:
            self.locations.pop(int(task_id), None)
            save_locations(self.locations, self.locations_path)
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
        self._link_locations_to_tasks()
        self.gamification.reset_weekly_progress()
        self.last_event_text = f"Wczytano nową listę ({Path(path).name}) — postęp tygodniowy został wyzerowany."
        self.refresh_ui()

    def save_current_json(self):
        if not self.current_file:
            self.export_json()
            return
        save_tasks(self.current_file, self.data)
        save_locations(self.locations, self.locations_path)
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
        save_locations(self.locations, self.locations_path)
        self.current_file = path
        self.refresh_ui()
        messagebox.showinfo("Zapisano", f"Wyeksportowano zadania do:\n{path}")

    def reset_filters(self):
        self.filter_mode.set("Wszystkie")
        self.prio_filter_var.set("Priorytet: Wszystkie")
        self.date_filter_var.set("Termin: Wszystkie")
        self.tag_filter_var.set("Tag: Wszystkie")
        self.search_var.set("")

    def _get_filtered_tasks(self) -> list[dict]:
        mode = self.filter_mode.get()
        prio_filter = self.prio_filter_var.get()
        date_filter = self.date_filter_var.get()
        tag_filter = self.tag_filter_var.get()
        query = self.search_var.get().strip().lower()
        today_str = date.today().isoformat()

        result = []
        for t in self.data["zadania"]:
            if mode == "Do zrobienia" and t["wykonane"]:
                continue
            if mode == "Zrobione" and not t["wykonane"]:
                continue
            if mode == "Po terminie" and not is_overdue(t):
                continue

            if prio_filter != "Priorytet: Wszystkie" and t.get("priorytet") != prio_filter:
                continue

            termin_val = t.get("termin")
            if date_filter == "Na dziś" and termin_val != today_str:
                continue
            if date_filter == "Po terminie" and not is_overdue(t):
                continue
            if date_filter == "Z terminem" and not termin_val:
                continue
            if date_filter == "Bez terminu (null)" and termin_val is not None:
                continue

            if tag_filter != "Tag: Wszystkie":
                clean_tag = tag_filter.lstrip("#")
                if clean_tag not in t.get("tagi", []):
                    continue

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
                    str(t.get("lokalizacja", "")).lower(),
                ])
                if query not in searchable and q_no_hash not in searchable:
                    continue

            result.append(t)
        return result

    def refresh_ui(self):
        file_status = Path(self.current_file).name if self.current_file else "Brak wczytanego pliku"
        self.title(f"Podsieciowe Maskarady — {file_status} (zadań: {len(self.data['zadania'])})")

        # 1. Odśwież boczny pasek lig
        self._render_sidebar()

        # 2. Odśwież panel grywalizacji
        st = self.gamification.state
        league = self.gamification.get_league_info()
        self.league_badge.configure(text=f"🏆 LIGA: {league['name'].upper()}", fg_color=league["color"])

        if league["next_name"]:
            pts_txt = f"{st['points']} pkt  •  -{league['pts_to_next']} do {league['next_name']}"
        else:
            pts_txt = f"{st['points']} pkt  •  Max liga!"
        self.points_label.configure(text=pts_txt)
        self.streak_label.configure(text=f"🔥 Streak: {st['streak']} tyg.")

        done_wk = st["completed_this_week"]
        goal_wk = max(1, st["weekly_goal"])
        self.goal_progress_label.configure(text=f"Cel tygodnia: {done_wk} / {goal_wk}")
        self.goal_progress_bar.set(min(1.0, done_wk / goal_wk))
        self.gami_status_label.configure(text=self.last_event_text)

        # 3. Odśwież Smart Focus + powiązanie z Pomodoro
        best_task, reason = get_smart_focus_task(self.data["zadania"])
        self.current_focus_task = best_task
        if best_task:
            self.focus_label.configure(text=f"{best_task['tytul']}\n{reason}")
            self.focus_done_btn.configure(state="normal", command=lambda tid=best_task["id"]: self.toggle_task(tid))
        else:
            self.focus_label.configure(text=reason)
            self.focus_done_btn.configure(state="disabled")

        # 4. Odśwież listę dostępnych tagów w menu filtrowania
        all_tags = sorted({tag for task in self.data["zadania"] for tag in task.get("tagi", [])})
        tag_options = ["Tag: Wszystkie"] + [f"#{tag}" for tag in all_tags]
        self.tag_filter_menu.configure(values=tag_options)
        if self.tag_filter_var.get() not in tag_options:
            self.tag_filter_var.set("Tag: Wszystkie")

        filtered_tasks = self._get_filtered_tasks()

        # 5. Wyświetl wybrany widok: Tablica Kanban, Kalendarz, Lista, Globus 3D lub Sfera 3D
        current_view = self.view_mode.get()
        self.task_list_frame.pack_forget()
        self.calendar_view.pack_forget()
        self.kanban_board.pack_forget()
        self.globe_view.pack_forget()

        if "Sfera" in current_view:
            # W widoku Sfera 3D ukrywamy ramkę roboczą, odsłaniając wirującą kulę cząsteczek w pełnej krasie pod kafelkami
            self.workspace_frame.place_forget()
        else:
            w = self.winfo_width()
            h = self.winfo_height()
            target_w = min(self._max_content_width, max(500, w - 40)) if w > 50 else self._max_content_width
            ws_h = max(200, h - self._ws_y - 14) if h > 50 else 520
            self.workspace_frame.configure(width=target_w, height=ws_h)
            self.workspace_frame.place(relx=0.5, y=self._ws_y, anchor="n")

            if "Tablica" in current_view:
                self.kanban_board.pack(fill="both", expand=True)
                self.kanban_board.render(filtered_tasks)
            elif "Kalendarz" in current_view:
                self.calendar_view.pack(fill="both", expand=True)
                self.calendar_view.render(filtered_tasks)
            elif "Lista" in current_view:
                self.task_list_frame.pack(fill="both", expand=True)
                self._render_list_view(filtered_tasks)
            elif "Globus" in current_view:
                self.globe_view.pack(fill="both", expand=True)
                self.globe_view.render(filtered_tasks)

    def _render_list_view(self, tasks: list[dict]):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not tasks:
            ctk.CTkLabel(
                self.task_list_frame,
                text="Brak zadań spełniających wybrane kryteria filtrowania.",
                font=ctk.CTkFont(size=14),
                text_color=JARVIS["text_muted"],
            ).pack(pady=30)
            return

        for t in tasks:
            card = ctk.CTkFrame(
                self.task_list_frame,
                fg_color=JARVIS["glass_panel"],
                border_width=1,
                border_color=JARVIS["border_cyan"] if not t["wykonane"] else JARVIS["neon_green"],
                corner_radius=8,
            )
            card.pack(fill="x", pady=4, padx=4)

            cb = ctk.CTkCheckBox(
                card,
                text="",
                width=24,
                command=lambda tid=t["id"]: self.toggle_task(tid),
                fg_color=JARVIS["cyan"],
                hover_color=JARVIS["cyan_dim"],
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
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=JARVIS["text_muted"] if t["wykonane"] else JARVIS["text_ice"],
            ).pack(anchor="w")

            pts_value = PRIORITY_POINTS.get(t["priorytet"], 4)
            termin_val = t.get("termin")
            meta_parts = [f"ID: #{t['id']}", f"Priorytet: {t['priorytet'].upper()} (+{pts_value} pkt)"]
            if termin_val:
                overdue_tag = " [PO TERMINIE]" if is_overdue(t) else ""
                meta_parts.append(f"Termin: {termin_val}{overdue_tag}")
            if t.get("tagi"):
                meta_parts.append("Tagi: " + ", ".join(f"#{tag}" for tag in t["tagi"]))
            if t.get("lokalizacja"):
                meta_parts.append(f"Lokalizacja: 📍 {t['lokalizacja']}")
            if t.get("opis"):
                meta_parts.append(f"Opis: {t['opis']}")

            ctk.CTkLabel(
                info_frame,
                text="  |  ".join(meta_parts),
                font=ctk.CTkFont(size=11),
                text_color=JARVIS["neon_red"] if is_overdue(t) else JARVIS["cyan_dim"],
            ).pack(anchor="w")

            prio_badge = ctk.CTkLabel(
                card,
                text=t["priorytet"].upper(),
                fg_color=PRIO_COLORS.get(t["priorytet"], "#555555"),
                text_color="#111111" if t["priorytet"] in ("sredni", "niski") else "#ffffff",
                corner_radius=6,
                width=70,
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            prio_badge.pack(side="right", padx=(5, 10))

            ctk.CTkButton(
                card,
                text="Usuń",
                width=65,
                fg_color="#5a1823",
                hover_color="#7a2030",
                border_width=1,
                border_color=JARVIS["neon_red"],
                command=lambda tid=t["id"]: self.delete_task(tid),
            ).pack(side="right", padx=4)

            ctk.CTkButton(
                card,
                text="Edytuj",
                width=65,
                fg_color=JARVIS["btn_glass_bg"],
                hover_color=JARVIS["btn_glass_hover"],
                border_width=1,
                border_color=JARVIS["border_subtle"],
                text_color=JARVIS["text_ice"],
                command=lambda task=t: self.edit_task(task),
            ).pack(side="right", padx=4)


if __name__ == "__main__":
    app = SmartPlannerApp()
    app.mainloop()