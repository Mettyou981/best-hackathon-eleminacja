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


class JarvisSphereParticleCanvas(ctk.CTkCanvas):
    """
    Futurystyczna animacja trójwymiarowej sfery cząsteczkowej (3D Particle Plexus Sphere)
    w stylu Jarvis / Iron Man HUD, dokładnie wg obrazu referencyjnego.
    Cząsteczki poruszają się w przestrzeni 3D na powłoce sfery, tworząc wirującą kulę danych.
    Węzły w kolorach elektrycznego cyjanu oraz ciepłego złota/bursztynu łączą się dynamicznymi
    wiązkami lasera (plexus effect).
    Węzły na pierwszym planie (z > 0) posiadają jaskrawe neony i poświaty, a węzły z tyłu (z < 0)
    są przygaszone, tworząc głęboki, holograficzny efekt 3D.
    """

    def __init__(self, master, num_particles: int = 110, **kwargs):
        kwargs.setdefault("bg", JARVIS["bg_root"])
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(master, **kwargs)

        self.num_particles = max(25, min(350, num_particles))
        self.particles: list[dict] = []
        self._anim_running = True
        self._after_id = None

        # Kąty obrotu sfery 3D
        self.yaw = 0.0
        self.pitch = 0.38  # Kąt nachylenia osi sfery (~22°)
        self.yaw_speed = 0.007
        self._time = 0.0

        # Interakcja myszą (obracanie kulą przez przeciąganie)
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self.bind("<Configure>", self._on_resize)
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)

        self.after(40, self._init_sphere)
        self.after(90, self._tick)

    def _init_sphere(self):
        """Generuje punkty na powłoce sfery 3D z klastrami cyjanowymi i złotymi (jak na referencji)."""
        self.particles = []
        n = self.num_particles

        # Centra klastrów złotych / bursztynowych (kontynenty danych jak na obrazie referencyjnym)
        amber_centers = [
            (0.55, 0.45, 0.65),
            (-0.60, -0.35, 0.68),
            (-0.25, 0.70, -0.65),
        ]

        for i in range(n):
            # Równomierny rozkład Fibonacciego na sferze
            y0 = 1.0 - (2.0 * i) / max(1, n - 1)
            radius_at_y = math.sqrt(max(0.0, 1.0 - y0 * y0))
            theta = 2.399963229728653 * i  # Złoty kąt

            # Wolumetryczna powłoka — subtelna dyspersja radialna
            r_shell = random.uniform(0.88, 1.12)
            bx = r_shell * radius_at_y * math.cos(theta)
            by = r_shell * y0
            bz = r_shell * radius_at_y * math.sin(theta)

            # Sprawdź przynależność do klastrów złota/bursztynu
            is_amber = False
            for acx, acy, acz in amber_centers:
                dist_sq = (bx - acx) ** 2 + (by - acy) ** 2 + (bz - acz) ** 2
                if dist_sq < 0.58 ** 2 and random.random() < 0.85:
                    is_amber = True
                    break

            self.particles.append({
                "bx": bx,
                "by": by,
                "bz": bz,
                "phase": random.uniform(0, math.pi * 2),
                "speed": random.uniform(0.6, 1.4),
                "is_amber": is_amber,
                "base_r": random.uniform(2.0, 3.4),
            })

    def set_num_particles(self, count: int):
        """Dynamicznie zmienia liczbę cząsteczek w sferze w czasie rzeczywistym ze slidera."""
        self.num_particles = max(25, min(350, int(count)))
        self._init_sphere()

    def _on_resize(self, event):
        pass

    def _on_mouse_down(self, event):
        self._is_dragging = True
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_mouse_drag(self, event):
        if not self._is_dragging:
            return
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.yaw -= dx * 0.006
        self.pitch = max(-1.4, min(1.4, self.pitch + dy * 0.006))
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_mouse_up(self, event):
        self._is_dragging = False

    def _tick(self):
        if not self._anim_running:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w > 20 and h > 20:
            self._render_frame(w, h)

        if not self._is_dragging:
            self.yaw += self.yaw_speed
        self._time += 0.035
        self._after_id = self.after(35, self._tick)

    def _render_frame(self, w: int, h: int):
        self.delete("all")

        cx = w / 2.0
        cy = h / 2.0
        sphere_r = min(w, h) * 0.38
        if sphere_r < 50:
            return

        # 1. Tło: subtelny radar HUD Jarvis w tle kuli
        for rad_mult in (0.7, 1.05, 1.35):
            rad = sphere_r * rad_mult
            self.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline="#051424", width=1)

        # 2. Oblicz pozycje cząsteczek po obrocie w 3D
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)
        # Delikatne kołysanie osi pitch
        effective_pitch = self.pitch + 0.04 * math.sin(self._time * 0.4)
        cos_pitch = math.cos(effective_pitch)
        sin_pitch = math.sin(effective_pitch)

        proj = []
        for i, p in enumerate(self.particles):
            # Płynny organiczny mikro-ruch na powłoce
            ph = p["phase"] + self._time * p["speed"]
            dx = 0.035 * math.sin(ph)
            dy = 0.035 * math.cos(ph * 1.2)
            dz = 0.035 * math.sin(ph * 0.7)

            x = p["bx"] + dx
            y = p["by"] + dy
            z = p["bz"] + dz

            # Obrót yaw (oś Y)
            x1 = x * cos_yaw - z * sin_yaw
            y1 = y
            z1 = x * sin_yaw + z * cos_yaw

            # Obrót pitch (oś X)
            x2 = x1
            y2 = y1 * cos_pitch - z1 * sin_pitch
            z2 = y1 * sin_pitch + z1 * cos_pitch

            # Rzutowanie na płaszczyznę 2D
            sx = cx + x2 * sphere_r
            sy = cy - y2 * sphere_r

            proj.append({
                "i": i,
                "x3": x2,
                "y3": y2,
                "z3": z2,
                "sx": sx,
                "sy": sy,
                "is_amber": p["is_amber"],
                "base_r": p["base_r"],
                "conn_count": 0,
            })

        # 3. Plexus — połączenia wiązkami energii między bliskimi punktami w 3D
        max_dist = 0.44 * (110.0 / max(30, self.num_particles)) ** 0.35
        max_dist_sq = max_dist * max_dist

        num_p = len(proj)
        for i in range(num_p):
            p1 = proj[i]
            for j in range(i + 1, num_p):
                p2 = proj[j]
                dx = p2["x3"] - p1["x3"]
                dy = p2["y3"] - p1["y3"]
                dz = p2["z3"] - p1["z3"]
                dist_sq = dx * dx + dy * dy + dz * dz

                if dist_sq < max_dist_sq:
                    p1["conn_count"] += 1
                    p2["conn_count"] += 1

                    avg_z = (p1["z3"] + p2["z3"]) * 0.5
                    is_both_amber = p1["is_amber"] and p2["is_amber"]
                    is_mixed = p1["is_amber"] != p2["is_amber"]

                    # Kolor i jasność wiązki w zależności od głębi Z i typu węzłów
                    if avg_z > 0.15:
                        if is_both_amber:
                            col = "#f59e0b" if dist_sq < (max_dist_sq * 0.4) else "#b45309"
                        elif is_mixed:
                            col = "#0ea5e9"
                        else:
                            col = "#00e5ff" if dist_sq < (max_dist_sq * 0.4) else "#0088cc"
                        self.create_line(p1["sx"], p1["sy"], p2["sx"], p2["sy"], fill=col, width=1.5 if dist_sq < (max_dist_sq * 0.25) else 1.0)
                    elif avg_z > -0.25:
                        if is_both_amber:
                            col = "#78350f"
                        elif is_mixed:
                            col = "#0369a1"
                        else:
                            col = "#004f7a"
                        self.create_line(p1["sx"], p1["sy"], p2["sx"], p2["sy"], fill=col, width=1.0)
                    else:
                        col = "#2a1503" if is_both_amber else "#031d33"
                        self.create_line(p1["sx"], p1["sy"], p2["sx"], p2["sy"], fill=col, width=1.0)

        # 4. Rysowanie węzłów (od tyłu do przodu — sortowanie wg z3)
        proj.sort(key=lambda item: item["z3"])

        for pt in proj:
            z = pt["z3"]
            sx = pt["sx"]
            sy = pt["sy"]
            is_amber = pt["is_amber"]
            conn = pt["conn_count"]

            if z > 0:
                # Przednia półkula — duże, świecące węzły z poświatą neonową
                r = pt["base_r"] * (0.9 + 0.5 * (z / 1.15))
                if is_amber:
                    core_col = "#ffffff" if (conn >= 3 and z > 0.4) else "#fbbf24"
                    glow_col = "#d97706"
                else:
                    core_col = "#ffffff" if (conn >= 3 and z > 0.4) else "#00e5ff"
                    glow_col = "#0077b6"

                if conn >= 3:
                    halo_r = r + 3.0
                    self.create_oval(sx - halo_r, sy - halo_r, sx + halo_r, sy + halo_r, outline=glow_col, width=1)

                self.create_oval(sx - r, sy - r, sx + r, sy + r, fill=core_col, outline=glow_col if conn >= 2 else "")
            else:
                # Tylna półkula — małe, przygaszone punkty dające głębię
                r = pt["base_r"] * max(0.4, 0.8 + 0.3 * (z / 1.15))
                dim_col = "#78350f" if is_amber else "#0369a1"
                self.create_oval(sx - r, sy - r, sx + r, sy + r, fill=dim_col, outline="")


# Alias wsteczny dla kompatybilności importów
JarvisParticleCanvas = JarvisSphereParticleCanvas


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
