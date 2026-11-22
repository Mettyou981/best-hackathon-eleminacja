import math
from datetime import date
import customtkinter as ctk
from smart import parse_coordinates, KNOWN_CITIES
from gamification import PRIORITY_POINTS
from jarvis_theme import JARVIS

# Uproszczone zarysy głównych kontynentów (szerokość, długość w stopniach)
# Pozwalają narysować rozpoznawalny globus Ziemi na płótnie
CONTINENTS = [
    # Europa i Azja (Eurazja)
    [
        (71, 28), (68, 50), (60, 60), (70, 75), (75, 100), (77, 105), (70, 130), (72, 145), (66, 170),
        (60, 165), (55, 160), (52, 142), (43, 132), (38, 120), (32, 122), (22, 114), (21, 108), (10, 105),
        (1, 104), (8, 98), (16, 96), (22, 89), (13, 80), (8, 77), (23, 70), (25, 62), (30, 48), (27, 50),
        (24, 55), (13, 45), (12, 43), (30, 32), (31, 35), (37, 36), (41, 28), (40, 23), (38, 24), (36, 22),
        (40, 18), (44, 13), (41, 15), (37, 15), (38, 9), (43, 5), (43, -3), (36, -6), (37, -9), (43, -9),
        (47, -2), (49, -1), (51, 2), (54, 8), (55, 12), (58, 11), (59, 18), (65, 23), (70, 28), (71, 28)
    ],
    # Afryka
    [
        (37, 10), (32, 25), (31, 32), (28, 34), (22, 37), (12, 44), (12, 51), (2, 45), (-11, 40),
        (-25, 33), (-34, 26), (-34, 18), (-22, 14), (-15, 12), (-5, 12), (4, 9), (5, 1), (4, -7),
        (10, -14), (15, -17), (21, -17), (28, -13), (35, -6), (36, -1), (37, 10)
    ],
    # Ameryka Północna
    [
        (72, -156), (70, -135), (69, -115), (60, -85), (62, -75), (58, -65), (52, -56), (47, -53),
        (44, -66), (41, -70), (35, -75), (30, -81), (25, -80), (29, -89), (26, -97), (19, -96),
        (15, -88), (9, -79), (8, -83), (16, -95), (20, -105), (24, -110), (32, -117), (37, -122),
        (48, -125), (54, -130), (59, -140), (60, -150), (58, -158), (65, -168), (71, -156), (72, -156)
    ],
    # Ameryka Południowa
    [
        (12, -72), (10, -62), (5, -52), (-3, -40), (-8, -35), (-13, -39), (-23, -42), (-32, -52),
        (-40, -62), (-52, -68), (-55, -67), (-50, -75), (-40, -74), (-25, -70), (-18, -71), (-14, -76),
        (-5, -81), (1, -80), (8, -77), (12, -72)
    ],
    # Australia
    [
        (-12, 131), (-12, 136), (-17, 141), (-11, 142), (-15, 145), (-24, 153), (-28, 153), (-37, 150),
        (-38, 145), (-35, 137), (-32, 132), (-34, 123), (-34, 115), (-22, 114), (-20, 119), (-15, 124),
        (-15, 130), (-12, 131)
    ],
    # Wielka Brytania & Irlandia
    [
        (58, -5), (58, -2), (53, 0), (50, 1), (50, -5), (54, -5), (58, -5)
    ],
    # Japonia
    [
        (45, 142), (43, 145), (35, 140), (33, 130), (35, 133), (40, 140), (45, 142)
    ],
    # Madagaskar
    [
        (-12, 49), (-16, 50), (-25, 47), (-25, 44), (-16, 44), (-12, 49)
    ],
    # Skandynawia
    [
        (71, 26), (69, 18), (62, 5), (58, 6), (58, 11), (65, 21), (70, 28), (71, 26)
    ]
]

# Dokładny zarys granic Polski (62 punkty graniczne z uwzględnieniem skrajnych punktów: Rozewie, Opołonek, Cedynia, Zosin)
POLAND_BORDER = [
    (53.92, 14.25),  # Świnoujście / granica zachodnia
    (54.02, 14.65),  # Wolin / Międzyzdroje
    (54.18, 15.58),  # Kołobrzeg
    (54.43, 16.40),  # Darłowo
    (54.58, 16.85),  # Ustka
    (54.76, 17.55),  # Łeba
    (54.83, 18.20),  # Jastrzębia Góra / Przylądek Rozewie (skrajny punkt N)
    (54.60, 18.80),  # Cypel Helski
    (54.52, 18.53),  # Gdynia
    (54.35, 18.65),  # Gdańsk
    (54.38, 19.45),  # Krynica Morska / Mierzeja Wiślana
    (54.43, 19.68),  # Frombork
    (54.40, 19.82),  # Braniewo
    (54.33, 20.60),  # Bartoszyce
    (54.33, 21.30),  # Węgorzewo
    (54.30, 22.30),  # Gołdap
    (54.36, 22.86),  # Trójstyk Wiżajny (PL/LT/RU)
    (54.15, 23.35),  # Sejny
    (53.93, 23.50),  # Płaska / granica wschodnia
    (53.51, 23.65),  # Kuźnica Białostocka
    (53.15, 23.95),  # Krynki
    (52.70, 23.85),  # Białowieża
    (52.33, 23.15),  # Mielnik nad Bugiem
    (52.07, 23.60),  # Terespol
    (51.55, 23.55),  # Włodawa
    (51.18, 24.02),  # Dorohusk
    (50.80, 24.09),  # Zosin / Hrubieszów (skrajny punkt E: 24°09'E)
    (50.35, 23.50),  # Tomaszów Lubelski
    (50.10, 23.15),  # Lubaczów
    (49.70, 22.75),  # Przemyśl
    (49.45, 22.60),  # Ustrzyki Dolne
    (49.00, 22.73),  # Szczyt Opołonek w Bieszczadach (skrajny punkt S: 49°00'N)
    (49.18, 22.35),  # Cisna
    (49.38, 21.65),  # Przełęcz Dukielska
    (49.42, 21.05),  # Krynica-Zdrój
    (49.40, 20.45),  # Szczawnica / Pieniny
    (49.18, 20.09),  # Tatry / Rysy
    (49.23, 19.80),  # Chochołów
    (49.50, 19.30),  # Babia Góra
    (49.50, 19.00),  # Korbielów / Beskid Żywiecki
    (49.58, 18.85),  # Koniaków / Trójstyk
    (49.75, 18.63),  # Cieszyn
    (49.90, 18.35),  # Wodzisław Śląski
    (50.08, 18.22),  # Racibórz
    (50.25, 17.55),  # Głubczyce
    (50.28, 17.30),  # Prudnik
    (50.35, 16.90),  # Paczków
    (50.44, 16.24),  # Kudowa-Zdrój / Kotlina Kłodzka
    (50.70, 16.00),  # Kamienna Góra
    (50.74, 15.74),  # Karkonosze / Śnieżka
    (50.83, 15.52),  # Szklarska Poręba
    (50.95, 15.00),  # Bogatynia / Worek Turoszowski
    (51.15, 15.00),  # Zgorzelec
    (51.50, 14.85),  # Przewóz nad Nysą Łużycką
    (51.95, 14.72),  # Gubin
    (52.35, 14.55),  # Słubice
    (52.60, 14.65),  # Kostrzyn nad Odrą
    (52.88, 14.12),  # Zakole Odry k. Cedyni (skrajny punkt W: 14°07'E)
    (53.05, 14.35),  # Chojna
    (53.30, 14.40),  # Gryfino
    (53.60, 14.35),  # Police / Zalew Szczeciński
    (53.92, 14.25),  # Świnoujście (domknięcie pętli granicy)
]

# Główne punkty odniesienia / miasta Polski dla zbliżenia HUD
POLAND_CITIES = [
    ("Warszawa", 52.23, 21.01),
    ("Kraków", 50.06, 19.95),
    ("Łódź", 51.76, 19.46),
    ("Wrocław", 51.11, 17.04),
    ("Poznań", 52.41, 16.93),
    ("Gdańsk", 54.35, 18.65),
    ("Szczecin", 53.43, 14.55),
    ("Bydgoszcz", 53.12, 18.01),
    ("Lublin", 51.25, 22.57),
    ("Białystok", 53.13, 23.16),
    ("Katowice", 50.26, 19.02),
    ("Rzeszów", 50.04, 22.00),
]

PRIO_COLORS = {
    "wysoki": JARVIS["neon_red"],
    "sredni": JARVIS["neon_amber"],
    "niski": JARVIS["neon_green"],
    "done": "#1abc9c",
}


class GlobeViewFrame(ctk.CTkFrame):
    """
    Interaktywny widok 3D Globusa Ziemi dla CustomTkinter.
    Obsługuje:
    - Płynne obracanie globusa przeciąganiem myszą (poprawny yaw/pitch)
    - Płynny zoom kółkiem myszy i przyciskami aż do bardzo dużego powiększenia (max_radius: 25000)
    - Dedykowany tryb zoomu na Polskę (Polska zajmuje dokładnie 90% widoku) z podwójną neonową obramówką
    - Płynny auto-obrót planetarny
    - Wizualizację zadań z koordynatami geograficznymi
    - Panel boczny z listą zadań i centrowaniem
    """

    def __init__(self, parent, on_toggle_task, on_edit_task, on_delete_task, on_add_with_loc=None):
        super().__init__(parent, fg_color="transparent")
        self.on_toggle_task = on_toggle_task
        self.on_edit_task = on_edit_task
        self.on_delete_task = on_delete_task
        self.on_add_with_loc = on_add_with_loc

        # Kąty obrotu globusa: domyślnie wycentrowany na Polskę (lat ~52.06°, lon ~19.48°)
        self.yaw = math.radians(19.48)
        self.pitch = math.radians(52.06)
        self.radius = 210  # Domyślny promień globusa
        self.min_radius = 80
        self.max_radius = 25000  # Bardzo duży zakres zoomu dla dokładnej mapy krajowej i regionalnej

        # Stan interakcji myszy
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._hovered_task_id: int | None = None
        self._selected_task_id: int | None = None

        # Auto-obrót globusa
        self.auto_spin = False
        self._spin_after_id = None

        # Zadania i cache zrzutowanych punktów
        self._tasks: list[dict] = []
        self._projected_tasks: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        # Układ dwukolumnowy: Lewa strona (Globus Canvas), Prawa strona (Inspektor zadań o stałej szerokości)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=370)
        self.grid_rowconfigure(0, weight=1)

        # === LEWA KOLUMNA: PŁÓTNO GLOBUSA I KONTROLKI ===
        left_box = ctk.CTkFrame(
            self,
            fg_color=JARVIS["glass_panel"],
            corner_radius=10,
            border_width=1,
            border_color=JARVIS["border_cyan"],
        )
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)

        # Pasek narzędziowy nad globusem: szybkie skróty geograficzne i kontrolki
        toolbar = ctk.CTkFrame(left_box, fg_color=JARVIS["glass_panel_alt"], corner_radius=8)
        toolbar.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            toolbar,
            text="🌍 GLOBUS 3D",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=JARVIS["cyan"],
        ).pack(side="left", padx=(12, 10), pady=6)

        # Dedykowany przycisk zoomu na Polskę (Polska zajmuje 90% widoku z podwójną obramówką)
        ctk.CTkButton(
            toolbar,
            text="🇵🇱 Polska",
            width=88,
            height=26,
            fg_color="#00558f",
            hover_color="#0077c2",
            border_width=1,
            border_color=JARVIS["cyan"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.focus_poland,
        ).pack(side="left", padx=(3, 6), pady=6)

        # Przyciski szybkiego obrotu do regionów / kontynentów
        presets = [
            ("🇪🇺 Europa", 50.0, 15.0, 650),
            ("🇺🇸 Ameryka", 38.0, -97.0, 320),
            ("🇯🇵 Azja", 35.0, 115.0, 320),
        ]
        for name, p_lat, p_lon, p_rad in presets:
            ctk.CTkButton(
                toolbar,
                text=name,
                width=75,
                height=26,
                fg_color=JARVIS["btn_glass_bg"],
                hover_color=JARVIS["btn_glass_hover"],
                border_width=1,
                border_color=JARVIS["border_subtle"],
                text_color=JARVIS["text_ice"],
                font=ctk.CTkFont(size=11),
                command=lambda la=p_lat, lo=p_lon, ra=p_rad: self.focus_region(la, lo, ra),
            ).pack(side="left", padx=3, pady=6)

        # Przyciski powiększenia / resetu po prawej stronie
        self.spin_btn = ctk.CTkButton(
            toolbar,
            text="▶ Auto-obrót",
            width=90,
            height=26,
            fg_color="#006655",
            hover_color="#008870",
            border_width=1,
            border_color=JARVIS["neon_green"],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.toggle_auto_spin,
        )
        self.spin_btn.pack(side="right", padx=(4, 10), pady=6)

        self.zoom_lbl = ctk.CTkLabel(
            toolbar,
            text="Zoom: 100%",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=JARVIS["cyan_dim"],
        )
        self.zoom_lbl.pack(side="right", padx=(4, 8), pady=6)

        ctk.CTkButton(
            toolbar,
            text="↺ Reset",
            width=58,
            height=26,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            font=ctk.CTkFont(size=11),
            command=self.reset_view,
        ).pack(side="right", padx=3, pady=6)

        ctk.CTkButton(
            toolbar,
            text="➖",
            width=32,
            height=26,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.zoom_out,
        ).pack(side="right", padx=2, pady=6)

        ctk.CTkButton(
            toolbar,
            text="➕",
            width=32,
            height=26,
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=self.zoom_in,
        ).pack(side="right", padx=2, pady=6)

        # Płótno Canvas do renderowania wektorowego globusa
        self.canvas = ctk.CTkCanvas(
            left_box,
            bg=JARVIS["bg_root"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # Pasek podpowiedzi pod globusem
        hint_bar = ctk.CTkFrame(left_box, fg_color="transparent")
        hint_bar.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            hint_bar,
            text="💡 Przeciągaj myszką, aby obracać globus  |  Kółko myszy = Zoom  |  Najedź na pinezkę, aby podejrzeć zadanie",
            font=ctk.CTkFont(size=11),
            text_color=JARVIS["cyan_dim"],
        ).pack(side="left")

        # Przypięcie zdarzeń myszy do Canvas
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Configure>", lambda _: self._draw_globe())

        # === PRAWA KOLUMNA: INSPEKTOR ZADAŃ Z LOKALIZACJĄ ===
        right_panel = ctk.CTkFrame(
            self,
            width=370,
            fg_color=JARVIS["glass_panel"],
            corner_radius=10,
            border_width=1,
            border_color=JARVIS["border_cyan"],
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=2)
        right_panel.pack_propagate(False)

        rp_header = ctk.CTkFrame(right_panel, fg_color=JARVIS["glass_panel_alt"], corner_radius=8)
        rp_header.pack(fill="x", padx=10, pady=(10, 6))

        self.panel_title = ctk.CTkLabel(
            rp_header,
            text="📍 Zadania z lokalizacją (0)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=JARVIS["cyan"],
            anchor="w",
        )
        self.panel_title.pack(fill="x", padx=10, pady=(8, 2))

        self.panel_subtitle = ctk.CTkLabel(
            rp_header,
            text="Kliknij zadanie, aby wycentrować globus",
            font=ctk.CTkFont(size=11),
            text_color=JARVIS["text_ice"],
            anchor="w",
        )
        self.panel_subtitle.pack(fill="x", padx=10, pady=(0, 8))

        # Kontener przewijany na karty zadań
        self.tasks_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self.tasks_scroll.pack(fill="both", expand=True, padx=6, pady=2)

        # Dolny pasek z informacją o zadaniach bez lokalizacji
        self.unlocated_box = ctk.CTkFrame(right_panel, fg_color="#1b2631", corner_radius=8)
        self.unlocated_box.pack(fill="x", padx=10, pady=(6, 10))

        self.unlocated_lbl = ctk.CTkLabel(
            self.unlocated_box,
            text="ℹ️ Zadania bez lokalizacji: 0",
            font=ctk.CTkFont(size=11),
            text_color="#85929e",
        )
        self.unlocated_lbl.pack(fill="x", padx=10, pady=8)

    # === STEROWANIE OBRACANIEM I POWIĘKSZANIEM ===
    def focus_poland(self):
        """
        Precyzyjnie wyśrodkowuje i przybliża widok tak, aby Polska zajmowała dokładnie 90% widoku.
        Geometryczny środek Polski: ~52.06°N, 19.48°E.
        Rozpiętość Polski: ~10.03° lon * cos(52.06°) ≈ 0.1078 radiana sfery.
        """
        self.yaw = math.radians(19.48)
        self.pitch = math.radians(52.06)

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        dim = min(w, h) if (w > 50 and h > 50) else 600

        # Aby obszar Polski (szerokość kątowa ~0.1078 rad) zajmował 90% mniejszego boku widoku (0.90 * dim):
        target_r = int((0.90 * dim) / 0.1078)
        self.radius = max(self.min_radius, min(self.max_radius, target_r))
        self._draw_globe()

    def focus_region(self, target_lat: float, target_lon: float, target_radius: int = None):
        """Obraca globus do danego regionu z opcjonalną zmianą skali promienia."""
        self.yaw = math.radians(target_lon)
        self.pitch = math.radians(target_lat)
        if target_radius is not None:
            self.radius = max(self.min_radius, min(self.max_radius, target_radius))
        self._draw_globe()

    def rotate_to(self, target_lat: float, target_lon: float):
        """Obraca globus, aby wycentrować go na danych współrzędnych."""
        self.yaw = math.radians(target_lon)
        self.pitch = math.radians(target_lat)
        self._draw_globe()

    def zoom_in(self):
        """Proporcjonalne płynne przybliżenie widoku."""
        self.radius = min(self.max_radius, max(self.min_radius, int(self.radius * 1.35)))
        self._draw_globe()

    def zoom_out(self):
        """Proporcjonalne płynne oddalenie widoku."""
        self.radius = max(self.min_radius, int(self.radius / 1.35))
        self._draw_globe()

    def reset_view(self):
        self.yaw = math.radians(19.48)
        self.pitch = math.radians(52.06)
        self.radius = 210
        self._draw_globe()

    def toggle_auto_spin(self):
        self.auto_spin = not self.auto_spin
        if self.auto_spin:
            self.spin_btn.configure(text="⏸ Pauza", fg_color="#d35400", hover_color="#a04000")
            self._spin_step()
        else:
            self.spin_btn.configure(text="▶ Auto-obrót", fg_color="#006655", hover_color="#008870")
            if self._spin_after_id:
                self.after_cancel(self._spin_after_id)
                self._spin_after_id = None

    def _spin_step(self):
        if not self.auto_spin:
            return
        self.yaw += 0.012
        self._draw_globe()
        self._spin_after_id = self.after(35, self._spin_step)

    # === OBSŁUGA ZDARZEŃ MYSZY NA PŁÓTNIE ===
    def _on_mouse_down(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._is_dragging = False

    def _on_mouse_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y

        if abs(dx) > 2 or abs(dy) > 2:
            self._is_dragging = True

        # Skala obrotu adaptacyjna do zoomu: przy dużym powiększeniu ruch jest płynny i precyzyjny
        sensitivity = 0.007 * (210.0 / max(80, self.radius))
        # Pociągnięcie w prawo obraca teren w prawo (yaw maleje)
        self.yaw -= dx * sensitivity
        # Pociągnięcie w dół przesuwa teren w dół (pitch rośnie)
        max_pitch = math.radians(85)
        self.pitch = max(-max_pitch, min(max_pitch, self.pitch + dy * sensitivity))

        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._draw_globe()

    def _on_mouse_up(self, event):
        if not self._is_dragging:
            # Kliknięcie — sprawdź, czy kliknięto w pin zadania
            clicked_task = self._find_task_at_pixel(event.x, event.y)
            if clicked_task:
                self._select_task(clicked_task["id"])
        self._is_dragging = False

    def _on_mouse_wheel(self, event):
        factor = 1.25 if event.delta > 0 else (1.0 / 1.25)
        self.radius = max(self.min_radius, min(self.max_radius, int(self.radius * factor)))
        self._draw_globe()

    def _on_mouse_move(self, event):
        if self._is_dragging:
            return
        hovered = self._find_task_at_pixel(event.x, event.y)
        new_hover_id = hovered["id"] if hovered else None
        if new_hover_id != self._hovered_task_id:
            self._hovered_task_id = new_hover_id
            self._draw_globe()

    def _find_task_at_pixel(self, px: int, py: int) -> dict | None:
        """Wyszukuje zadanie pod współrzędnymi kursora myszy."""
        for pt in self._projected_tasks:
            if not pt["visible"]:
                continue
            dist_sq = (px - pt["sx"]) ** 2 + (py - pt["sy"]) ** 2
            if dist_sq <= (pt["radius"] + 6) ** 2:
                return pt["task"]
        return None

    def _select_task(self, task_id: int):
        self._selected_task_id = task_id
        for t in self._tasks:
            if t["id"] == task_id:
                coords = parse_coordinates(t.get("lokalizacja"))
                if coords:
                    lat, lon, _ = coords
                    self.rotate_to(lat, lon)
                break
        self._draw_globe()

    # === MATEMATYKA RZUTOWANIA 3D NA 2D (PROJEKCJA ORTOGRAFICZNA) ===
    def _project_point(self, lat_deg: float, lon_deg: float, cx: float, cy: float) -> tuple[float, float, float]:
        """
        Rzutuje współrzędne geograficzne (lat, lon) na współrzędne ekranowe (sx, sy) oraz głębokość z.
        Gdy z > 0, punkt znajduje się na widocznej półkuli.
        Gdy yaw = lon i pitch = lat, punkt jest dokładnie w centrum (cx, cy).
        """
        phi = math.radians(lat_deg)
        lam = math.radians(lon_deg)

        # Współrzędne kartezjańskie na jednostkowej sferze
        x = math.cos(phi) * math.sin(lam)
        y = math.sin(phi)
        z = math.cos(phi) * math.cos(lam)

        # Obrót o yaw (dookoła osi Y): lam - yaw
        x1 = x * math.cos(self.yaw) - z * math.sin(self.yaw)
        y1 = y
        z1 = x * math.sin(self.yaw) + z * math.cos(self.yaw)

        # Obrót o pitch (dookoła osi X): phi - pitch
        x2 = x1
        y2 = y1 * math.cos(self.pitch) - z1 * math.sin(self.pitch)
        z2 = y1 * math.sin(self.pitch) + z1 * math.cos(self.pitch)

        sx = cx + x2 * self.radius
        sy = cy - y2 * self.radius
        return sx, sy, z2

    # === RYSOWANIE GLOBUSA ===
    def _draw_globe(self):
        c = self.canvas
        c.delete("all")

        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20 or h < 20:
            return

        cx = w / 2.0
        cy = h / 2.0
        r = self.radius

        # Aktualizacja etykiety Zoom w pasku narzędzi
        if hasattr(self, "zoom_lbl"):
            zoom_pct = int((self.radius / 210.0) * 100)
            self.zoom_lbl.configure(text=f"Zoom: {zoom_pct}%")

        # 1. Tło kosmiczne — stałe gwiazdy w rogach widoku
        star_coords = [
            (w * 0.05, h * 0.12), (w * 0.18, h * 0.08), (w * 0.88, h * 0.14),
            (w * 0.94, h * 0.28), (w * 0.06, h * 0.84), (w * 0.14, h * 0.92),
            (w * 0.85, h * 0.86), (w * 0.93, h * 0.74), (w * 0.52, h * 0.04),
        ]
        for sx, sy in star_coords:
            c.create_oval(sx - 1, sy - 1, sx + 1, sy + 1, fill="#4a5d70", outline="")

        # 2. Poświata atmosfery Ziemi (glow ring w stylu Jarvis HUD, gdy globus mieści się w widoku)
        if r < 1800:
            c.create_oval(cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7, outline="#004766", width=4)
            c.create_oval(cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2, outline=JARVIS["cyan"], width=2)

        # 3. Kula oceanów (głęboki ciemnogranatowy błękit Jarvis)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#041628", outline=JARVIS["cyan"] if r < 1800 else "", width=2)

        # 4. Siatka geograficzna: Równoleżniki
        lat_step = 10 if r > 1200 else 30
        for lat in range(-80, 85, lat_step):
            is_equator = (lat == 0)
            pts = []
            for step_lon in range(0, 365, 5):
                sx, sy, z = self._project_point(lat, step_lon, cx, cy)
                if z >= -0.05:  # Widoczna strona
                    pts.extend([sx, sy])
                else:
                    if len(pts) >= 4:
                        c.create_line(pts, fill=JARVIS["cyan"] if is_equator else "#003855", width=2 if is_equator else 1)
                    pts = []
            if len(pts) >= 4:
                c.create_line(pts, fill=JARVIS["cyan"] if is_equator else "#003855", width=2 if is_equator else 1)

        # Siatka geograficzna: Południki
        lon_step = 10 if r > 1200 else 30
        for lon in range(0, 360, lon_step):
            is_prime = (lon == 0)
            pts = []
            for step_lat in range(-85, 90, 5):
                sx, sy, z = self._project_point(step_lat, lon, cx, cy)
                if z >= -0.05:
                    pts.extend([sx, sy])
                else:
                    if len(pts) >= 4:
                        c.create_line(pts, fill=JARVIS["cyan"] if is_prime else "#002840", width=2 if is_prime else 1)
                    pts = []
            if len(pts) >= 4:
                c.create_line(pts, fill=JARVIS["cyan"] if is_prime else "#002840", width=2 if is_prime else 1)

        # 5. Zarysy lądów / kontynentów (HUD Cyber Cyan)
        for polygon in CONTINENTS:
            pts = []
            for lat, lon in polygon:
                sx, sy, z = self._project_point(lat, lon, cx, cy)
                if z >= -0.05:
                    pts.extend([sx, sy])
                else:
                    if len(pts) >= 4:
                        c.create_line(pts, fill="#0088aa", width=2, capstyle="round", joinstyle="round")
                    pts = []
            if len(pts) >= 4:
                c.create_line(pts, fill="#0088aa", width=2, capstyle="round", joinstyle="round")

        # 5b. DEDYKOWANA OBRAMÓWKA I ROZBUDOWANA WIZUALIZACJA POLSKI (JARVIS TACTICAL HUD)
        pl_pts = []
        for lat, lon in POLAND_BORDER:
            psx, psy, pz = self._project_point(lat, lon, cx, cy)
            if pz >= -0.15:
                pl_pts.extend([psx, psy])

        if len(pl_pts) >= 8:
            # Wypełnienie konturu Polski taktycznym odcieniem Jarvis
            c.create_polygon(pl_pts, fill="#072b44", outline="")
            # 1. Zewnętrzna poświata granicy Polski
            c.create_polygon(pl_pts, fill="", outline="#00558f", width=5, joinstyle="round")
            # 2. Główna neonowa obramówka granicy (Cyan)
            c.create_polygon(pl_pts, fill="", outline=JARVIS["cyan"], width=2, joinstyle="round")
            # 3. Dodatkowa wewnętrzna obramówka taktyczna (Biała przerywana linia)
            c.create_polygon(pl_pts, fill="", outline="#ffffff", width=1, dash=(5, 3), joinstyle="round")

            # Etykieta kraju oraz miasta przy odpowiednim powiększeniu
            csx, csy, cz = self._project_point(52.06, 19.48, cx, cy)
            if cz > 0:
                if self.radius > 400:
                    c.create_text(
                        csx, csy - 25,
                        text="🇵🇱 POLSKA",
                        fill="#ffffff",
                        font=("Segoe UI", 13 if self.radius > 2000 else 10, "bold"),
                    )

                # Wyświetlanie głównych miast Polski przy zbliżeniu
                if self.radius > 1600:
                    for c_name, c_lat, c_lon in POLAND_CITIES:
                        city_sx, city_sy, city_z = self._project_point(c_lat, c_lon, cx, cy)
                        if city_z > 0 and 0 <= city_sx <= w and 0 <= city_sy <= h:
                            c.create_oval(city_sx - 3, city_sy - 3, city_sx + 3, city_sy + 3, fill=JARVIS["cyan"], outline="#ffffff", width=1)
                            c.create_text(
                                city_sx + 6, city_sy,
                                text=c_name,
                                fill=JARVIS["cyan_dim"],
                                font=("Segoe UI", 9, "bold"),
                                anchor="w",
                            )

        # 6. Markery zadań z koordynatami
        self._projected_tasks = []
        tooltip_to_draw = None

        for t in self._tasks:
            loc = t.get("lokalizacja")
            parsed = parse_coordinates(loc)
            if not parsed:
                continue

            lat, lon, label = parsed
            sx, sy, z = self._project_point(lat, lon, cx, cy)

            is_done = t.get("wykonane", False)
            prio = t.get("priorytet", "sredni")
            color = PRIO_COLORS.get("done" if is_done else prio, "#f39c12")
            is_hovered = (t["id"] == self._hovered_task_id)
            is_selected = (t["id"] == self._selected_task_id)

            pin_radius = 8 if (is_hovered or is_selected) else 6
            visible = (z > 0.02)

            self._projected_tasks.append({
                "task": t,
                "sx": sx,
                "sy": sy,
                "z": z,
                "visible": visible,
                "radius": pin_radius,
                "label": label,
            })

            if visible:
                # Pulsacyjny zewnętrzny pierścień
                halo_r = pin_radius + (6 if is_hovered else 3)
                c.create_oval(sx - halo_r, sy - halo_r, sx + halo_r, sy + halo_r, outline=color, width=2)

                # Środek pinezki
                c.create_oval(
                    sx - pin_radius, sy - pin_radius, sx + pin_radius, sy + pin_radius,
                    fill=color, outline="#ffffff", width=2 if is_selected else 1
                )

                # Krótki identyfikator zadania wewnątrz lub obok
                c.create_text(
                    sx + pin_radius + 4, sy - 2,
                    text=f"#{t['id']} {label}",
                    anchor="w",
                    font=("Segoe UI", 9, "bold" if is_hovered else "normal"),
                    fill="#ffffff" if is_hovered else "#d5dbdb",
                )

                if is_hovered:
                    tooltip_to_draw = (sx, sy, t, label, prio, is_done)
            else:
                # Punkt po drugiej stronie Ziemi — subtelny przerywany obrys
                c.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, outline="#566573", width=1)

        # 7. Renderowanie bogatego tooltipa po najechaniu myszką
        if tooltip_to_draw:
            tsx, tsy, t, t_label, t_prio, t_done = tooltip_to_draw
            pts_val = PRIORITY_POINTS.get(t_prio, 4)
            status_txt = "✓ ZROBIONE" if t_done else ("PO TERMINIE" if t.get("termin") and t.get("termin") < date.today().isoformat() else "DO ZROBIENIA")

            lines = [
                f"#{t['id']} {t['tytul']}",
                f"📍 {t_label}  |  {t_prio.upper()} (+{pts_val} pkt)",
                f"Status: {status_txt}" + (f"  |  Termin: {t['termin']}" if t.get("termin") else "")
            ]

            # Obliczenie rozmiaru dymka
            box_w = 260
            box_h = 68
            bx = max(10, min(w - box_w - 10, tsx + 12))
            by = max(10, min(h - box_h - 10, tsy - box_h - 6))

            c.create_rectangle(bx, by, bx + box_w, by + box_h, fill=JARVIS["glass_panel_alt"], outline=JARVIS["cyan"], width=2)
            c.create_text(bx + 10, by + 14, text=lines[0], anchor="w", font=("Segoe UI", 10, "bold"), fill=JARVIS["text_ice"])
            c.create_text(bx + 10, by + 34, text=lines[1], anchor="w", font=("Segoe UI", 9, "bold"), fill=JARVIS["cyan"])
            c.create_text(bx + 10, by + 52, text=lines[2], anchor="w", font=("Segoe UI", 9), fill=JARVIS["text_muted"])

    # === METODA PUBLICZNA: RENDEROWANIE STANU ZADAŃ ===
    def render(self, tasks: list[dict]):
        self._tasks = tasks

        located_tasks = [t for t in tasks if parse_coordinates(t.get("lokalizacja"))]
        unlocated_count = len(tasks) - len(located_tasks)

        self.panel_title.configure(text=f"📍 Zadania z lokalizacją ({len(located_tasks)})")
        self.unlocated_lbl.configure(text=f"ℹ️ Zadania bez lokalizacji (brak koordynatów): {unlocated_count}")

        # Wyczyść poprzednie widgety listy
        for w in self.tasks_scroll.winfo_children():
            w.destroy()

        if not located_tasks:
            ctk.CTkLabel(
                self.tasks_scroll,
                text="Brak zadań ze zdefiniowaną lokalizacją.\n\nDodaj koordynaty (np. 52.23, 21.01)\nlub miasto (np. Warszawa) w edycji zadania,\naby zobaczyć je na globusie!",
                font=ctk.CTkFont(size=12),
                text_color=JARVIS["text_muted"],
                justify="center",
            ).pack(pady=40)
        else:
            for t in located_tasks:
                self._create_task_card(self.tasks_scroll, t)

        # Odśwież płótno globusa
        self._draw_globe()

    def _create_task_card(self, parent, task: dict):
        is_done = task.get("wykonane", False)
        prio = task.get("priorytet", "sredni")
        pts = PRIORITY_POINTS.get(prio, 4)
        parsed = parse_coordinates(task.get("lokalizacja"))
        loc_str = parsed[2] if parsed else (task.get("lokalizacja") or "Brak")

        card = ctk.CTkFrame(
            parent,
            fg_color="#07201b" if is_done else JARVIS["glass_panel_alt"],
            border_width=1,
            border_color=JARVIS["neon_green"] if is_done else JARVIS["border_cyan"],
            corner_radius=8,
        )
        card.pack(fill="x", pady=4, padx=4)

        # Górny wiersz karty
        top_r = ctk.CTkFrame(card, fg_color="transparent")
        top_r.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(
            top_r,
            text=f"#{task['id']}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=JARVIS["cyan_dim"],
        ).pack(side="left")

        badge = ctk.CTkLabel(
            top_r,
            text=f"{prio.upper()} (+{pts} pkt)",
            fg_color=PRIO_COLORS.get(prio, "#555555"),
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#111111" if prio in ("sredni", "niski") else "#ffffff",
            padx=6,
            pady=1,
        )
        badge.pack(side="right")

        # Tytuł
        ctk.CTkLabel(
            card,
            text=f"✓ {task['tytul']}" if is_done else task["tytul"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=JARVIS["text_muted"] if is_done else JARVIS["text_ice"],
            wraplength=310,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(0, 2))

        # Etykieta lokalizacji
        loc_row = ctk.CTkFrame(card, fg_color="transparent")
        loc_row.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(
            loc_row,
            text=f"📍 {loc_str}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=JARVIS["cyan"],
            anchor="w",
        ).pack(side="left")

        if task.get("termin"):
            ctk.CTkLabel(
                loc_row,
                text=f"📅 {task['termin']}",
                font=ctk.CTkFont(size=10),
                text_color=JARVIS["text_ice"],
            ).pack(side="right")

        # Wiersz przycisków
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=6, pady=(0, 6))

        # Przycisk centrowania na globusie
        if parsed:
            lat, lon, _ = parsed
            ctk.CTkButton(
                btn_row,
                text="🎯 Pokaż na globusie",
                height=24,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=JARVIS["btn_cyan_bg"],
                hover_color=JARVIS["btn_cyan_hover"],
                border_width=1,
                border_color=JARVIS["cyan"],
                text_color=JARVIS["text_ice"],
                command=lambda la=lat, lo=lon, tid=task["id"]: self._focus_task_on_globe(la, lo, tid),
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_row,
            text="Cofnij" if is_done else "✓ Odhacz",
            width=65,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=JARVIS["btn_glass_bg"] if is_done else "#006655",
            hover_color=JARVIS["btn_glass_hover"] if is_done else "#008870",
            border_width=1,
            border_color=JARVIS["border_subtle"] if is_done else JARVIS["neon_green"],
            text_color=JARVIS["text_ice"] if is_done else "#ffffff",
            command=lambda tid=task["id"]: self.on_toggle_task(tid),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_row,
            text="✎",
            width=26,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=JARVIS["btn_glass_bg"],
            hover_color=JARVIS["btn_glass_hover"],
            border_width=1,
            border_color=JARVIS["border_subtle"],
            text_color=JARVIS["text_ice"],
            command=lambda tk=task: self.on_edit_task(tk),
        ).pack(side="right", padx=1)

    def _focus_task_on_globe(self, lat: float, lon: float, task_id: int):
        self._selected_task_id = task_id
        self._hovered_task_id = task_id
        self.yaw = math.radians(lon)
        self.pitch = math.radians(lat)
        if self.radius < 1200:
            self.radius = 1200
        self._draw_globe()
