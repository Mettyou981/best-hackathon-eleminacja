import platform
import subprocess
import textwrap
from datetime import date, datetime
from pathlib import Path
from smart import is_overdue

# Mapowanie polskich znaków diakrytycznych na kody oktalne zdefiniowane w /Differences
POLISH_PDF_MAP = {
    "Ą": "\\200",
    "Ć": "\\201",
    "Ę": "\\202",
    "Ł": "\\203",
    "Ń": "\\204",
    "Ś": "\\205",
    "Ź": "\\206",
    "Ż": "\\207",
    "ą": "\\210",
    "ć": "\\211",
    "ę": "\\212",
    "ł": "\\213",
    "ń": "\\214",
    "ś": "\\215",
    "ź": "\\216",
    "ż": "\\217",
}


def _encode_pdf_text(text: str) -> str:
    """Konwertuje tekst z polskimi znakami na format bezpieczny dla strumienia PDF 1.4."""
    cleaned = text.replace("✓", "[OK]").replace("•", "-")
    out_chars: list[str] = []
    for ch in cleaned:
        if ch == "\\":
            out_chars.append("\\\\")
        elif ch == "(":
            out_chars.append("\\(")
        elif ch == ")":
            out_chars.append("\\)")
        elif ch in POLISH_PDF_MAP:
            out_chars.append(POLISH_PDF_MAP[ch])
        else:
            try:
                ch.encode("cp1252")
                out_chars.append(ch)
            except UnicodeEncodeError:
                # Pomijamy znaki spoza zestawu (np. emoji)
                continue
    return "".join(out_chars).encode("cp1252", errors="ignore").decode("latin1")


def export_weekly_summary_pdf(filepath: str | Path, tasks: list[dict], gamification_state: dict, league_info: dict) -> Path:
    """Generuje czysty, wielostronicowy raport podsumowania tygodnia w formacie PDF 1.4."""
    today = date.today()
    _, iso_week, _ = today.isocalendar()

    done_tasks = [t for t in tasks if t.get("wykonane")]
    overdue_tasks = [t for t in tasks if not t.get("wykonane") and is_overdue(t)]
    upcoming_tasks = [t for t in tasks if not t.get("wykonane") and not is_overdue(t)]

    # Lista wierszy: (tekst, czy_pogrubiony, rozmiar_czcionki)
    lines: list[tuple[str, bool, int]] = [
        ("SmartApp - Raport Podsumowania Tygodnia", True, 17),
        (f"Data wygenerowania: {today.strftime('%d.%m.%Y')}  |  Tydzien roku: #{iso_week}", False, 10),
        ("-" * 82, False, 10),
        ("1. STATYSTYKI SYSTEMATYCZNOSCI I LIGI", True, 12),
        (f"   Aktualna liga: {league_info['name'].upper()}", True, 11),
        (f"   Suma punktow: {gamification_state.get('points', 0)} pkt (w tym tygodniu: +{gamification_state.get('points_this_week', 0)} pkt)", False, 10),
        (f"   Cel tygodniowy: {gamification_state.get('completed_this_week', 0)} / {gamification_state.get('weekly_goal', 3)} ukonczonych zadan", False, 10),
        (f"   Aktywny streak: {gamification_state.get('streak', 0)} tyg.", False, 10),
        (f"   Ukonczone sesje skupienia Pomodoro (25 min): {gamification_state.get('pomodoro_sessions', 0)}", False, 10),
        ("", False, 10),
        (f"2. ZADANIA WYKONANE ({len(done_tasks)})", True, 12),
    ]

    if not done_tasks:
        lines.append(("   Brak ukonczonych zadan na liscie.", False, 10))
    else:
        for t in done_tasks:
            termin = t.get("termin") or "brak terminu"
            entry = f"   [OK] #{t['id']} {t['tytul']} (priorytet: {t['priorytet']}, termin: {termin})"
            for wrapped in textwrap.wrap(entry, width=84):
                lines.append((wrapped, False, 10))

    lines.append(("", False, 10))
    lines.append((f"3. ZADANIA PO TERMINIE - WYMAGAJACE UWAGI ({len(overdue_tasks)})", True, 12))
    if not overdue_tasks:
        lines.append(("   Brak zaleglych zadan - swietna robota!", False, 10))
    else:
        for t in overdue_tasks:
            entry = f"   [!] #{t['id']} {t['tytul']} (termin: {t.get('termin')}, priorytet: {t['priorytet']})"
            for wrapped in textwrap.wrap(entry, width=84):
                lines.append((wrapped, False, 10))

    lines.append(("", False, 10))
    lines.append((f"4. ZADANIA DO ZROBIENIA W PLANIE ({len(upcoming_tasks)})", True, 12))
    if not upcoming_tasks:
        lines.append(("   Wszystkie zaplanowane zadania zostaly juz zrealizowane.", False, 10))
    else:
        for t in upcoming_tasks:
            termin = t.get("termin") or "brak terminu"
            tags_str = (" [" + ", ".join(f"#{tg}" for tg in t.get("tagi", [])) + "]") if t.get("tagi") else ""
            entry = f"   - #{t['id']} {t['tytul']} | termin: {termin} | priorytet: {t['priorytet']}{tags_str}"
            for wrapped in textwrap.wrap(entry, width=84):
                lines.append((wrapped, False, 10))

    # Podział linii na strony A4 (ok. 45 linii na stronę)
    lines_per_page = 45
    pages_lines = [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[("Brak danych", False, 11)]]

    # Budowa obiektów PDF 1.4
    objects: list[bytes] = []

    # 1: Catalog, 2: Pages (uzupełnimy kids później)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")  # placeholder dla 2 0 obj

    # 3: Czcionka zwykła z polskim kodowaniem (obiekt 5)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding 5 0 R >>")
    # 4: Czcionka pogrubiona z polskim kodowaniem (obiekt 5)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding 5 0 R >>")
    # 5: Słownik kodowania polskich znaków
    encoding_dict = (
        b"<< /Type /Encoding /BaseEncoding /WinAnsiEncoding "
        b"/Differences [128 /Aogonek /Cacute /Eogonek /Lslash /Nacute /Sacute /Zacute /Zdotaccent "
        b"136 /aogonek /cacute /eogonek /lslash /nacute /sacute /zacute /zdotaccent] >>"
    )
    objects.append(encoding_dict)

    page_obj_ids: list[int] = []
    for page_idx, p_lines in enumerate(pages_lines, start=1):
        stream_cmds = ["BT"]
        y_pos = 785
        for text_line, is_bold, font_size in p_lines:
            font_ref = "/F2" if is_bold else "/F1"
            encoded = _encode_pdf_text(text_line)
            stream_cmds.append(f"{font_ref} {font_size} Tf")
            stream_cmds.append(f"1 0 0 1 48 {y_pos} Tm")
            stream_cmds.append(f"({encoded}) Tj")
            y_pos -= (font_size + 5)

        # Stopka numeru strony
        footer_txt = _encode_pdf_text(f"SmartApp  |  Strona {page_idx} z {len(pages_lines)}")
        stream_cmds.append("/F1 9 Tf")
        stream_cmds.append("1 0 0 1 48 32 Tm")
        stream_cmds.append(f"({footer_txt}) Tj")
        stream_cmds.append("ET")

        stream_bytes = "\n".join(stream_cmds).encode("latin1")
        content_obj_id = len(objects) + 1
        objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"\nendstream")

        page_obj_id = len(objects) + 1
        page_obj_ids.append(page_obj_id)
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        ).encode("ascii")
        objects.append(page_dict)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode("ascii")

    # Składanie pliku PDF z dokładną tablicą przesunięć xref
    pdf_buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = [0]

    for idx, obj_data in enumerate(objects, start=1):
        offsets.append(len(pdf_buf))
        pdf_buf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf_buf.extend(obj_data)
        pdf_buf.extend(b"\nendobj\n")

    xref_offset = len(pdf_buf)
    pdf_buf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf_buf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf_buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    pdf_buf.extend(trailer)

    out_path = Path(filepath)
    out_path.write_bytes(pdf_buf)
    return out_path


def get_upcoming_24h_tasks(tasks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Zwraca krotkę (zadania_do_24h, zadania_po_terminie) dla niewykonanych zadań."""
    today = date.today()
    due_soon: list[dict] = []
    overdue: list[dict] = []

    for t in tasks:
        if t.get("wykonane") or not t.get("termin"):
            continue
        try:
            due_date = datetime.strptime(t["termin"], "%Y-%m-%d").date()
        except ValueError:
            continue

        days_left = (due_date - today).days
        if days_left < 0:
            overdue.append(t)
        elif days_left <= 1:
            due_soon.append(t)

    return due_soon, overdue


def send_system_notification(title: str, message: str) -> bool:
    """Wysyła natywne powiadomienie systemowe bez blokowania interfejsu GUI."""
    system = platform.system()
    safe_title = title.replace('"', "'").replace("\n", " ")
    safe_msg = message.replace('"', "'").replace("\n", " ")

    try:
        if system == "Windows":
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$notify = New-Object System.Windows.Forms.NotifyIcon; "
                "$notify.Icon = [System.Drawing.SystemIcons]::Information; "
                "$notify.Visible = $true; "
                f'$notify.ShowBalloonTip(6000, "{safe_title}", "{safe_msg}", [System.Windows.Forms.ToolTipIcon]::Info); '
                "Start-Sleep -Seconds 7; "
                "$notify.Dispose()"
            )
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                creationflags=creation_flags,
            )
            return True

        if system == "Darwin":
            subprocess.Popen(
                ["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"']
            )
            return True

        # Linux / BSD
        subprocess.Popen(["notify-send", safe_title, safe_msg])
        return True
    except Exception:
        return False