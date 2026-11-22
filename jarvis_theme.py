import math
import random
from pathlib import Path
import customtkinter as ctk

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# === PALETA KOLORYSTYCZNA JARVIS / IRON MAN HUD ===
# Głęboki błękit kosmiczny, półprzezroczyste szkło, neonowy cyjan i błękit
JARVIS = {
    # Tła
    "bg_root": "#040810",         # Głęboka czerń z odcieniem granatu
    "bg_canvas": "#040810",
    "glass_panel": "#071424",     # Półprzezroczyste ciemnoniebieskie szkło
    "glass_panel_alt": "#0a1c32", # Akcentowane panele
    "glass_panel_focus": "#09223e",
    
    # Obramowania i poświaty neonowe
    "border_subtle": "#004870",   # Dyskretna cyber-ramka
    "border_cyan": "#00a8e8",     # Jasnoniebieska ramka HUD
    "border_glow": "#00e5ff",     # Elektryczny cyjan
    "border_danger": "#ff2a4b",   # Alarm HUD
    
    # Akcenty Jarvis HUD
    "cyan": "#00e5ff",            # Główny neonowy cyjan
    "cyan_dim": "#0099cc",
    "blue_core": "#0077ff",       # Błękit reaktora łukowego
    "neon_amber": "#ffaa00",      # Ostrzeżenie / średni priorytet
    "neon_red": "#ff3355",        # Wysoki priorytet
    "neon_green": "#00ffaa",      # Niski priorytet / wykonane
    "neon_emerald": "#1abc9c",
    
    # Przyciski ze szkła (translucent glass buttons)
    "btn_glass_bg": "#091e36",
    "btn_glass_hover": "#11335a",
    "btn_glass_border": "#0077aa",
    "btn_cyan_bg": "#00558f",
    "btn_cyan_hover": "#0077c2",
    "btn_cyan_border": "#00e5ff",
    
    # Pola tekstowe i wejścia
    "input_bg": "#05101c",
    "input_border": "#004766",
    "input_border_focus": "#00d2ff",
    
    # Typografia HUD
    "text_ice": "#e0f7ff",        # Lodowy biało-błękitny
    "text_cyan": "#00d2ff",       # Informacyjny cyjan
    "text_muted": "#5588a3",      # Przygaszony błękitny
}


class JarvisParticleCanvas(ctk.CTkCanvas):
    """
    Płótno generujące płynną, futurystyczną animację cząsteczek (particles plexus)
    w stylu Jarvis / Iron Man HUD.
    Cząsteczki unoszą się powoli w przestrzeni, a gdy zbliżają się do siebie,
    są łączone delikatnymi liniami lasera/danych.
    W tle widoczne są subtelne koncentryczne okręgi radaru HUD.
    """

    def __init__(self, master, num_particles: int = 55, **kwargs):
        kwargs.setdefault("bg", JARVIS["bg_root"])
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(master, **kwargs)

        self.num_particles = num_particles
        self.particles: list[dict] = []
        self._anim_running = True
        self._after_id = None
        self._hud_angle = 0.0

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._init_particles)
        self.after(100, self._tick)

    def _init_particles(self):
        w = max(400, self.winfo_width())
        h = max(300, self.winfo_height())
        self.particles = []

        colors = ["#00e5ff", "#00a8e8", "#0077ff", "#4de5ff", "#00558f"]
        for _ in range(self.num_particles):
            self.particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "vx": random.uniform(-0.35, 0.35),
                "vy": random.uniform(-0.35, 0.35),
                "r": random.uniform(1.2, 2.8),
                "color": random.choice(colors),
            })

    def _on_resize(self, event):
        # Dopasuj cząsteczki do nowego rozmiaru okna
        w = event.width
        h = event.height
        for p in self.particles:
            if p["x"] > w:
                p["x"] = random.uniform(0, w)
            if p["y"] > h:
                p["y"] = random.uniform(0, h)

    def _tick(self):
        if not self._anim_running:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w > 20 and h > 20:
            self._render_frame(w, h)

        self._hud_angle = (self._hud_angle + 0.25) % 360.0
        self._after_id = self.after(35, self._tick)

    def _render_frame(self, w: int, h: int):
        self.delete("all")

        cx = w / 2.0
        cy = h / 2.0

        # 1. Subtelne tło radarowe HUD (koncentryczne okręgi w stylu Jarvis)
        radar_radii = [180, 360, 540]
        for rad in radar_radii:
            self.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline="#071b30", width=1)

        # 2. Ruch i odbijanie cząsteczek
        pts = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]

            # Zawijanie na krawędziach
            if p["x"] < -10:
                p["x"] = w + 10
            elif p["x"] > w + 10:
                p["x"] = -10
            if p["y"] < -10:
                p["y"] = h + 10
            elif p["y"] > h + 10:
                p["y"] = -10

            pts.append((p["x"], p["y"], p["r"], p["color"]))

        # 3. Linie danych łączące bliskie cząsteczki (plexus effect)
        max_dist_sq = 85.0 ** 2
        for i in range(len(pts)):
            x1, y1, _, _ = pts[i]
            for j in range(i + 1, len(pts)):
                x2, y2, _, _ = pts[j]
                dx = x2 - x1
                dy = y2 - y1
                dist_sq = dx * dx + dy * dy
                if dist_sq < max_dist_sq:
                    # Im bliżej, tym jaśniejsza linia lasera
                    if dist_sq < 40.0 ** 2:
                        line_col = "#004d73"
                    else:
                        line_col = "#002b40"
                    self.create_line(x1, y1, x2, y2, fill=line_col, width=1)

        # 4. Rysowanie świecących punktów cząsteczek
        for px, py, pr, pcol in pts:
            # Poświata
            self.create_oval(px - pr - 1, py - pr - 1, px + pr + 1, py + pr + 1, fill="", outline="#003859", width=1)
            # Rdzeń
            self.create_oval(px - pr, py - pr, px + pr, py + pr, fill=pcol, outline="")


class JarvisArcReactor(ctk.CTkCanvas):
    """
    Animowany miniaturowy Reaktor Łukowy / Kółko HUD w stylu Iron Man Jarvis.
    Zawiera obracające się koncentryczne pierścienie z podziałką i pulsujący rdzeń.
    Inspirowany obrazami kółko i kółko2 z folderu Jarvis Inspo.
    """

    def __init__(self, master, size: int = 46, **kwargs):
        kwargs.setdefault("bg", JARVIS["glass_panel"])
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(master, width=size, height=size, **kwargs)

        self.size = size
        self.angle_outer = 0.0
        self.angle_inner = 0.0
        self.pulse = 0.0
        self.pulse_dir = 1

        self.after(60, self._animate)

    def _animate(self):
        self.angle_outer = (self.angle_outer + 2.5) % 360.0
        self.angle_inner = (self.angle_inner - 3.8) % 360.0

        self.pulse += 0.08 * self.pulse_dir
        if self.pulse > 1.0:
            self.pulse_dir = -1
        elif self.pulse < 0.0:
            self.pulse_dir = 1

        self._draw_reactor()
        self.after(35, self._animate)

    def _draw_reactor(self):
        self.delete("all")
        cx = self.size / 2.0
        cy = self.size / 2.0
        r_outer = (self.size / 2.0) - 3
        r_mid = r_outer - 5
        r_core = 5 + (1.5 * self.pulse)

        # 1. Zewnętrzny obrys
        self.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer, outline="#005580", width=1)

        # 2. Obracające się łuki zewnętrzne (3 segmenty)
        for i in range(3):
            start = self.angle_outer + (i * 120)
            self.create_arc(
                cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                start=start, extent=65, style="arc", outline=JARVIS["cyan"], width=2
            )

        # 3. Wewnętrzny pierścień ząbkowany obracający się w przeciwną stronę
        for j in range(6):
            rad_j = math.radians(self.angle_inner + (j * 60))
            x1 = cx + (r_mid - 3) * math.cos(rad_j)
            y1 = cy + (r_mid - 3) * math.sin(rad_j)
            x2 = cx + r_mid * math.cos(rad_j)
            y2 = cy + r_mid * math.sin(rad_j)
            self.create_line(x1, y1, x2, y2, fill="#00a8e8", width=1.5)

        self.create_oval(cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid, outline="#0077b6", width=1)

        # 4. Centralny pulsujący błękitny rdzeń (Arc Core)
        self.create_oval(cx - r_core - 2, cy - r_core - 2, cx + r_core + 2, cy + r_core + 2, fill="#004d73", outline="")
        self.create_oval(cx - r_core, cy - r_core, cx + r_core, cy + r_core, fill=JARVIS["cyan"], outline="#ffffff", width=1)


def get_inspo_image(name: str, size: tuple[int, int] = (40, 40)) -> ctk.CTkImage | None:
    """Wczytuje grafikę z folderu inspo jarvis i zwraca jako CTkImage."""
    if not HAS_PIL:
        return None
    base_dir = Path(__file__).resolve().parent
    inspo_dir = base_dir / "inspo jarvis" / "Jarvis UI Design_ Iron Man HUD Interface Skill _ Skills UI_files"
    if not inspo_dir.exists():
        inspo_dir = base_dir / "inspo jarvis"

    candidates = list(inspo_dir.glob(f"*{name}*"))
    if not candidates:
        return None
    try:
        img_path = candidates[0]
        pil_img = Image.open(img_path)
        return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
    except Exception:
        return None
