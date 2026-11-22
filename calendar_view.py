import calendar
from datetime import date
import customtkinter as ctk
from gamification import PRIORITY_POINTS

POLISH_MONTHS = [
    "",
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
]

POLISH_DAYS_SHORT = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"]
POLISH_DAYS_FULL = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]

PRIO_PILL_COLORS = {
    "wysoki": "#c0392b",
    "sredni": "#d68910",
    "niski": "#239b56",
}


class CalendarViewFrame(ctk.CTkFrame):
    def __init__(self, parent, on_toggle_task, on_edit_task, on_delete_task, on_add_on_date):
        super().__init__(parent, fg_color="transparent")
        self.on_toggle_task = on_toggle_task
        self.on_edit_task = on_edit_task
        self.on_delete_task = on_delete_task
        self.on_add_on_date = on_add_on_date

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self._last_tasks: list[dict] = []

        self._build_layout()

    def _build_layout(self):
        # Lewa strona: elastyczna siatka kalendarza; Prawa strona: stała szerokość 350 px
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=350)
        self.grid_rowconfigure(0, weight=1)

        # === LEWA KOLUMNA: NAWIGACJA + SIATKA MIESIĄCA ===
        left_panel = ctk.CTkFrame(self, fg_color="#16202a", border_width=1, border_color="#2c3e50", corner_radius=8)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)

        # Górny pasek nawigacji miesiąca i legenda kolorów
        nav_bar = ctk.CTkFrame(left_panel, fg_color="#1b2631", corner_radius=6)
        nav_bar.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            nav_bar,
            text="◀",
            width=34,
            height=28,
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self._prev_month,
        ).pack(side="left", padx=(8, 4), pady=6)

        ctk.CTkButton(
            nav_bar,
            text="Dzisiaj",
            width=65,
            height=28,
            fg_color="#2980b9",
            command=self._go_today,
        ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(
            nav_bar,
            text="▶",
            width=34,
            height=28,
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self._next_month,
        ).pack(side="left", padx=(4, 12), pady=6)

        self.month_title_label = ctk.CTkLabel(
            nav_bar,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.month_title_label.pack(side="left", padx=6)

        # Legenda kolorów po prawej stronie paska nawigacji
        legend_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
        legend_frame.pack(side="right", padx=8)

        legend_items = [
            ("● Wysoki", "#e74c3c"),
            ("● Średni", "#f39c12"),
            ("● Niski", "#2ecc71"),
            ("✓ Zrobione", "#52be80"),
        ]
        for lbl_txt, col in legend_items:
            ctk.CTkLabel(
                legend_frame,
                text=lbl_txt,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=col,
            ).pack(side="left", padx=5)

        # Nagłówki dni tygodnia (Pon - Nd)
        days_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        days_header.pack(fill="x", padx=8, pady=(2, 2))

        for idx, day_name in enumerate(POLISH_DAYS_SHORT):
            days_header.grid_columnconfigure(idx, weight=1, uniform="cal_day_col")
            is_weekend = idx >= 5
            hdr = ctk.CTkLabel(
                days_header,
                text=day_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f5b7b1" if is_weekend else "#85c1e9",
                fg_color="#1f2d3a" if is_weekend else "#1b2631",
                corner_radius=5,
                height=26,
            )
            hdr.grid(row=0, column=idx, sticky="ew", padx=2)

        # Kontener na siatkę dni miesiąca
        self.grid_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True, padx=8, pady=(2, 8))

        # === PRAWA KOLUMNA: INSPEKTOR WYBRANEGO DNIA ===
        right_panel = ctk.CTkFrame(
            self,
            width=350,
            fg_color="#16202a",
            border_width=1,
            border_color="#2c3e50",
            corner_radius=8,
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=2)
        right_panel.pack_propagate(False)

        day_hdr_box = ctk.CTkFrame(right_panel, fg_color="#1f2d3d", corner_radius=6)
        day_hdr_box.pack(fill="x", padx=10, pady=(10, 6))

        self.selected_day_title = ctk.CTkLabel(
            day_hdr_box,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.selected_day_title.pack(fill="x", padx=10, pady=(8, 2))

        self.selected_day_subtitle = ctk.CTkLabel(
            day_hdr_box,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#85c1e9",
            anchor="w",
            wraplength=310,
            justify="left",
        )
        self.selected_day_subtitle.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(
            right_panel,
            text="+ Dodaj zadanie na ten dzień",
            height=30,
            fg_color="#2980b9",
            hover_color="#1f618d",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.on_add_on_date(self.selected_date.isoformat()),
        ).pack(fill="x", padx=10, pady=(0, 6))

        self.day_tasks_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self.day_tasks_scroll.pack(fill="both", expand=True, padx=6, pady=2)

        self.no_date_info_label = ctk.CTkLabel(
            right_panel,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#85929e",
        )
        self.no_date_info_label.pack(fill="x", padx=10, pady=(4, 8))

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render(self._last_tasks)

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render(self._last_tasks)

    def _go_today(self):
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self.render(self._last_tasks)

    def _select_day(self, day_obj: date):
        self.selected_date = day_obj
        self.render(self._last_tasks)

    def render(self, tasks: list[dict]):
        self._last_tasks = tasks
        self.month_title_label.configure(text=f"{POLISH_MONTHS[self.current_month]} {self.current_year}")

        # Grupowanie zadań po dacie YYYY-MM-DD
        tasks_by_date: dict[str, list[dict]] = {}
        no_date_count = 0
        for t in tasks:
            termin = t.get("termin")
            if termin:
                tasks_by_date.setdefault(termin, []).append(t)
            else:
                no_date_count += 1

        # Wyczyść poprzednią siatkę
        for widget in self.grid_container.winfo_children():
            widget.destroy()

        month_matrix = calendar.monthcalendar(self.current_year, self.current_month)
        today = date.today()

        for c in range(7):
            self.grid_container.grid_columnconfigure(c, weight=1, uniform="cal_grid_col")
        for r in range(len(month_matrix)):
            self.grid_container.grid_rowconfigure(r, weight=1, uniform="cal_grid_row")

        for r_idx, week in enumerate(month_matrix):
            for c_idx, day_num in enumerate(week):
                if day_num == 0:
                    empty_cell = ctk.CTkFrame(
                        self.grid_container,
                        fg_color="#111820",
                        corner_radius=6,
                    )
                    empty_cell.grid(row=r_idx, column=c_idx, sticky="nsew", padx=2, pady=2)
                    continue

                cell_date = date(self.current_year, self.current_month, day_num)
                iso_str = cell_date.isoformat()
                day_tasks = tasks_by_date.get(iso_str, [])

                is_today = (cell_date == today)
                is_selected = (cell_date == self.selected_date)
                is_weekend = (c_idx >= 5)

                if is_selected:
                    bg_color = "#1f3044"
                    border_color = "#f1c40f"
                    border_w = 2
                elif is_today:
                    bg_color = "#1b2e42"
                    border_color = "#3498db"
                    border_w = 2
                else:
                    bg_color = "#18222d" if is_weekend else "#1c2836"
                    border_color = "#2c3e50"
                    border_w = 1

                cell = ctk.CTkFrame(
                    self.grid_container,
                    fg_color=bg_color,
                    border_width=border_w,
                    border_color=border_color,
                    corner_radius=6,
                    cursor="hand2",
                )
                cell.grid(row=r_idx, column=c_idx, sticky="nsew", padx=2, pady=2)

                # Górny pasek komórki: numer dnia + licznik / ostrzeżenie o spiętrzeniu
                cell_top = ctk.CTkFrame(cell, fg_color="transparent")
                cell_top.pack(fill="x", padx=5, pady=(3, 1))

                day_num_lbl = ctk.CTkLabel(
                    cell_top,
                    text=f"{day_num}" + (" (Dziś)" if is_today else ""),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#5dade2" if is_today else ("#f5b7b1" if is_weekend else "#ecf0f1"),
                )
                day_num_lbl.pack(side="left")

                clickable_widgets = [cell, cell_top, day_num_lbl]

                if day_tasks:
                    pending_cnt = sum(1 for t in day_tasks if not t.get("wykonane"))
                    is_crunch = pending_cnt >= 3
                    badge_txt = f"🔥 {len(day_tasks)}" if is_crunch else f"{len(day_tasks)}"
                    cnt_badge = ctk.CTkLabel(
                        cell_top,
                        text=badge_txt,
                        fg_color="#c0392b" if is_crunch else "#2c3e50",
                        corner_radius=4,
                        font=ctk.CTkFont(size=10, weight="bold"),
                        text_color="#ffffff",
                        padx=5,
                    )
                    cnt_badge.pack(side="right")
                    clickable_widgets.append(cnt_badge)

                # Maksymalnie 2 kolorowe pigułki zadań w komórce
                for t in day_tasks[:2]:
                    done = t.get("wykonane", False)
                    prio = t.get("priorytet", "sredni")
                    pill_bg = "#1e8449" if done else PRIO_PILL_COLORS.get(prio, "#2e4053")
                    prefix = "✓ " if done else ""
                    short_title = (prefix + t["tytul"])[:19]

                    pill = ctk.CTkLabel(
                        cell,
                        text=short_title,
                        fg_color=pill_bg,
                        corner_radius=4,
                        font=ctk.CTkFont(size=10, weight="bold"),
                        text_color="#d5f5e3" if done else "#ffffff",
                        anchor="w",
                        padx=5,
                    )
                    pill.pack(fill="x", padx=4, pady=1)
                    clickable_widgets.append(pill)

                if len(day_tasks) > 2:
                    more_lbl = ctk.CTkLabel(
                        cell,
                        text=f"+{len(day_tasks) - 2} więcej...",
                        font=ctk.CTkFont(size=10),
                        text_color="#aeb6bf",
                        anchor="w",
                    )
                    more_lbl.pack(fill="x", padx=6, pady=(0, 2))
                    clickable_widgets.append(more_lbl)

                for w in clickable_widgets:
                    w.bind("<Button-1>", lambda _, d=cell_date: self._select_day(d))

        # Odśwież panel szczegółów wybranego dnia
        sel_iso = self.selected_date.isoformat()
        sel_tasks = tasks_by_date.get(sel_iso, [])
        self._render_day_inspector(sel_tasks, no_date_count)

    def _render_day_inspector(self, day_tasks: list[dict], no_date_count: int):
        weekday_name = POLISH_DAYS_FULL[self.selected_date.weekday()]
        self.selected_day_title.configure(
            text=f"📅 {self.selected_date.strftime('%d.%m.%Y')} ({weekday_name})"
        )

        total_pts = sum(PRIORITY_POINTS.get(t.get("priorytet", "sredni"), 4) for t in day_tasks)
        self.selected_day_subtitle.configure(
            text=f"Zadań w tym dniu: {len(day_tasks)}   |   Pula: {total_pts} pkt"
        )
        self.no_date_info_label.configure(
            text=f"ℹ️ Zadania bez terminu (null): {no_date_count}"
        )

        for widget in self.day_tasks_scroll.winfo_children():
            widget.destroy()

        if not day_tasks:
            ctk.CTkLabel(
                self.day_tasks_scroll,
                text="Brak zaplanowanych zadań na ten dzień.\nKliknij przycisk powyżej, aby coś dodać.",
                font=ctk.CTkFont(size=12),
                text_color="#7f8c8d",
                justify="center",
            ).pack(pady=35)
            return

        for t in day_tasks:
            is_done = t.get("wykonane", False)
            prio = t.get("priorytet", "sredni")
            pts = PRIORITY_POINTS.get(prio, 4)

            card = ctk.CTkFrame(
                self.day_tasks_scroll,
                fg_color="#1b2c25" if is_done else "#22303c",
                border_width=1,
                border_color="#27ae60" if is_done else PRIO_PILL_COLORS.get(prio, "#34495e"),
                corner_radius=8,
            )
            card.pack(fill="x", pady=5, padx=4)

            # Górny pasek karty: ID po lewej, plakietka priorytetu i punktów po prawej (nic nie nachodzi na tytuł)
            top_r = ctk.CTkFrame(card, fg_color="transparent")
            top_r.pack(fill="x", padx=9, pady=(7, 3))

            ctk.CTkLabel(
                top_r,
                text=f"ID #{t['id']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#85929e",
            ).pack(side="left")

            badge = ctk.CTkLabel(
                top_r,
                text=f"{prio.upper()} (+{pts} pkt)",
                fg_color=PRIO_PILL_COLORS.get(prio, "#555555"),
                corner_radius=4,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#ffffff",
                padx=7,
                pady=1,
            )
            badge.pack(side="right")

            # Pełna szerokość karty na tytuł zadania
            title_lbl = ctk.CTkLabel(
                card,
                text=f"✓ {t['tytul']}" if is_done else t["tytul"],
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#a3e4d7" if is_done else "#ffffff",
                wraplength=280,
                justify="left",
                anchor="w",
            )
            title_lbl.pack(fill="x", padx=9, pady=(0, 3))

            if t.get("opis"):
                ctk.CTkLabel(
                    card,
                    text=t["opis"],
                    font=ctk.CTkFont(size=11),
                    text_color="#bdc3c7",
                    wraplength=280,
                    justify="left",
                    anchor="w",
                ).pack(fill="x", padx=9, pady=(0, 3))

            if t.get("tagi"):
                ctk.CTkLabel(
                    card,
                    text=" ".join(f"#{tg}" for tg in t["tagi"]),
                    font=ctk.CTkFont(size=10),
                    text_color="#85c1e9",
                    wraplength=280,
                    justify="left",
                    anchor="w",
                ).pack(fill="x", padx=9, pady=(0, 4))

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(fill="x", padx=7, pady=(2, 7))

            ctk.CTkButton(
                btn_row,
                text="Cofnij" if is_done else "✓ Zrobione",
                width=82,
                height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#2e4053" if is_done else "#27ae60",
                hover_color="#1e8449",
                command=lambda tid=t["id"]: self.on_toggle_task(tid),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_row,
                text="✕",
                width=26,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#922b21",
                hover_color="#641e16",
                command=lambda tid=t["id"]: self.on_delete_task(tid),
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                btn_row,
                text="✎",
                width=26,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#34495e",
                command=lambda tk=t: self.on_edit_task(tk),
            ).pack(side="right", padx=2)