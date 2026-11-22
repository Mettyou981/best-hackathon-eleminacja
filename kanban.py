from datetime import date, datetime, timedelta
import customtkinter as ctk
from gamification import PRIORITY_POINTS

COLUMNS = [
    ("overdue", "Po terminie", "#e74c3c"),
    ("today", "Na dziś", "#f1c40f"),
    ("this_week", "Na ten tydzień", "#3498db"),
    ("next_week", "Na przyszły tydzień", "#2980b9"),
    ("no_date", "Brak terminu", "#7f8c8d"),
    ("done", "Zrobione", "#27ae60"),
]

PRIO_DOT_COLORS = {
    "wysoki": "#e74c3c",
    "sredni": "#f39c12",
    "niski": "#2ecc71",
}


def classify_task_column(task: dict) -> str:
    if task.get("wykonane"):
        return "done"

    termin = task.get("termin")
    if not termin:
        return "no_date"
    try:
        due = datetime.strptime(termin, "%Y-%m-%d").date()
    except ValueError:
        return "no_date"

    diff = (due - date.today()).days
    if diff < 0:
        return "overdue"
    if diff == 0:
        return "today"
    if diff <= 7:
        return "this_week"
    return "next_week"


def target_date_for_column(col_key: str) -> str | None:
    today = date.today()
    if col_key == "overdue":
        return (today - timedelta(days=1)).isoformat()
    if col_key == "today":
        return today.isoformat()
    if col_key == "this_week":
        return (today + timedelta(days=3)).isoformat()
    if col_key == "next_week":
        return (today + timedelta(days=10)).isoformat()
    return None


class KanbanBoardFrame(ctk.CTkFrame):
    def __init__(self, parent, on_move_task, on_toggle_task, on_edit_task, on_delete_task, on_add_in_column):
        super().__init__(parent, fg_color="transparent")
        self.on_move_task = on_move_task
        self.on_toggle_task = on_toggle_task
        self.on_edit_task = on_edit_task
        self.on_delete_task = on_delete_task
        self.on_add_in_column = on_add_in_column

        self.col_containers: dict[str, ctk.CTkFrame] = {}
        self.col_scrolls: dict[str, ctk.CTkScrollableFrame] = {}
        self.col_headers: dict[str, ctk.CTkLabel] = {}

        # Stan przeciągania (Drag & Drop)
        self._drag_task: dict | None = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._ghost_win: ctk.CTkToplevel | None = None
        self._hovered_col: str | None = None

        self._build_columns()

    def _build_columns(self):
        for idx, (col_key, title, accent_color) in enumerate(COLUMNS):
            self.grid_columnconfigure(idx, weight=1, uniform="kanban_col")
            self.grid_rowconfigure(0, weight=1)

            col_box = ctk.CTkFrame(self, fg_color="#16202a", border_width=1, border_color="#2c3e50", corner_radius=8)
            col_box.grid(row=0, column=idx, sticky="nsew", padx=3, pady=2)
            self.col_containers[col_key] = col_box

            # Kolorowy pasek nagłówka
            header_bar = ctk.CTkFrame(col_box, fg_color=accent_color, corner_radius=6, height=32)
            header_bar.pack(fill="x", padx=4, pady=(4, 2))
            header_bar.pack_propagate(False)

            text_col = "#111111" if col_key == "today" else "#ffffff"
            hdr_lbl = ctk.CTkLabel(
                header_bar,
                text=f"{title} (0)",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=text_col,
            )
            hdr_lbl.pack(side="left", padx=8)
            self.col_headers[col_key] = hdr_lbl

            # Przycisk '+' pod nagłówkiem do szybkiego dodawania w konkretnej kolumnie
            add_btn = ctk.CTkButton(
                col_box,
                text="+",
                height=24,
                fg_color="#22303c",
                hover_color="#34495e",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda ck=col_key: self.on_add_in_column(ck),
            )
            add_btn.pack(fill="x", padx=6, pady=(2, 4))

            scroll = ctk.CTkScrollableFrame(col_box, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=2, pady=(0, 4))
            self.col_scrolls[col_key] = scroll

    def render(self, tasks: list[dict]):
        for scroll in self.col_scrolls.values():
            for w in scroll.winfo_children():
                w.destroy()

        grouped: dict[str, list[dict]] = {key: [] for key, _, _ in COLUMNS}
        for t in tasks:
            col_key = classify_task_column(t)
            grouped[col_key].append(t)

        for col_key, title, _ in COLUMNS:
            col_tasks = grouped[col_key]
            self.col_headers[col_key].configure(text=f"{title} ({len(col_tasks)})")
            scroll = self.col_scrolls[col_key]

            if not col_tasks:
                ctk.CTkLabel(
                    scroll,
                    text="Upuść zadanie tutaj",
                    font=ctk.CTkFont(size=11),
                    text_color="#566573",
                ).pack(pady=24)
                continue

            for t in col_tasks:
                self._create_card(scroll, t, col_key)

    def _create_card(self, parent, task: dict, col_key: str):
        is_done = task.get("wykonane", False)
        card = ctk.CTkFrame(
            parent,
            fg_color="#1b2c25" if is_done else "#263645",
            border_width=1,
            border_color="#27ae60" if is_done else "#34495e",
            corner_radius=8,
        )
        card.pack(fill="x", pady=4, padx=2)

        # Górny wiersz karty: tytuł + kropka priorytetu
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=7, pady=(7, 2))

        prio = task.get("priorytet", "sredni")
        dot = ctk.CTkLabel(
            top_row,
            text="●",
            font=ctk.CTkFont(size=12),
            text_color=PRIO_DOT_COLORS.get(prio, "#aaaaaa"),
            width=12,
        )
        dot.pack(side="right", padx=(3, 0))

        title_str = f"✓ {task['tytul']}" if is_done else task["tytul"]
        title_lbl = ctk.CTkLabel(
            top_row,
            text=title_str,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a3e4d7" if is_done else "#ffffff",
            wraplength=130,
            justify="left",
            anchor="w",
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Opis (jeśli istnieje)
        desc_lbl = None
        if task.get("opis"):
            desc_lbl = ctk.CTkLabel(
                card,
                text=task["opis"],
                font=ctk.CTkFont(size=11),
                text_color="#aeb6bf",
                wraplength=140,
                justify="left",
                anchor="w",
            )
            desc_lbl.pack(fill="x", padx=7, pady=(0, 3))

        # Plakietka z datą i punktami
        pts = PRIORITY_POINTS.get(prio, 4)
        termin_txt = task.get("termin") or "Brak terminu"
        if is_done:
            pill_color = "#1e8449"
            pill_txt = f"✓ {termin_txt}  •  +{pts} pkt"
        elif col_key == "overdue":
            pill_color = "#c0392b"
            pill_txt = f"🕒 {termin_txt}  •  +{pts} pkt"
        else:
            pill_color = "#1b4f72"
            pill_txt = f"🕒 {termin_txt}  •  +{pts} pkt"

        pill_lbl = ctk.CTkLabel(
            card,
            text=pill_txt,
            fg_color=pill_color,
            corner_radius=5,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ecf0f1",
            padx=5,
            pady=1,
        )
        pill_lbl.pack(anchor="w", padx=7, pady=(2, 3))

        # Tagi (jeśli są)
        tags_lbl = None
        if task.get("tagi"):
            tags_str = " ".join(f"#{tg}" for tg in task["tagi"])
            tags_lbl = ctk.CTkLabel(
                card,
                text=tags_str,
                font=ctk.CTkFont(size=10),
                text_color="#85c1e9",
                anchor="w",
            )
            tags_lbl.pack(fill="x", padx=7, pady=(0, 3))

        # Dolny pasek szybkich akcji
        actions_row = ctk.CTkFrame(card, fg_color="transparent")
        actions_row.pack(fill="x", padx=5, pady=(2, 6))

        ctk.CTkButton(
            actions_row,
            text="Cofnij" if is_done else "✓ Zrobione",
            width=60,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#2e4053" if is_done else "#27ae60",
            hover_color="#1e8449",
            command=lambda tid=task["id"]: self.on_toggle_task(tid),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions_row,
            text="✕",
            width=22,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#922b21",
            hover_color="#641e16",
            command=lambda tid=task["id"]: self.on_delete_task(tid),
        ).pack(side="right", padx=1)

        ctk.CTkButton(
            actions_row,
            text="✎",
            width=22,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#34495e",
            command=lambda tk=task: self.on_edit_task(tk),
        ).pack(side="right", padx=1)

        # Podpięcie zdarzeń myszy do przeciągania całej karty
        draggable_widgets = [card, top_row, dot, title_lbl, pill_lbl, actions_row]
        if desc_lbl:
            draggable_widgets.append(desc_lbl)
        if tags_lbl:
            draggable_widgets.append(tags_lbl)

        for w in draggable_widgets:
            w.bind("<ButtonPress-1>", lambda e, tk=task: self._start_drag(e, tk))
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)

    def _start_drag(self, event, task: dict):
        self._drag_task = task
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._is_dragging = False

    def _on_drag(self, event):
        if not self._drag_task:
            return

        if not self._is_dragging:
            if abs(event.x_root - self._drag_start_x) < 6 and abs(event.y_root - self._drag_start_y) < 6:
                return
            self._is_dragging = True
            self._create_ghost(self._drag_task)

        if self._ghost_win:
            self._ghost_win.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")

        target_col = self._detect_column_at(event.x_root)
        if target_col != self._hovered_col:
            self._highlight_column(target_col)

    def _end_drag(self, event):
        if self._ghost_win:
            self._ghost_win.destroy()
            self._ghost_win = None

        self._highlight_column(None)

        if self._is_dragging and self._drag_task:
            target_col = self._detect_column_at(event.x_root)
            current_col = classify_task_column(self._drag_task)
            if target_col and target_col != current_col:
                self.on_move_task(self._drag_task, target_col)

        self._drag_task = None
        self._is_dragging = False

    def _create_ghost(self, task: dict):
        ghost = ctk.CTkToplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", 0.88)
        except Exception:
            pass

        box = ctk.CTkFrame(ghost, fg_color="#2e86c1", border_width=2, border_color="#85c1e9", corner_radius=8)
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(
            box,
            text=f"📌 {task['tytul'][:36]}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff",
            padx=12,
            pady=8,
        ).pack()
        self._ghost_win = ghost

    def _detect_column_at(self, x_root: int) -> str | None:
        for col_key, container in self.col_containers.items():
            x1 = container.winfo_rootx()
            x2 = x1 + container.winfo_width()
            if x1 <= x_root <= x2:
                return col_key
        return None

    def _highlight_column(self, active_col: str | None):
        self._hovered_col = active_col
        accent_map = {key: color for key, _, color in COLUMNS}
        for col_key, container in self.col_containers.items():
            if col_key == active_col:
                container.configure(border_width=2, border_color=accent_map[col_key])
            else:
                container.configure(border_width=1, border_color="#2c3e50")