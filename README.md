# 🎓 Podsieciowe Maskarady — Inteligentny Planner Zadań dla Studenta

> **Zadanie eliminacyjne — kategoria SmartApp**
>
> **Drużyna:** Podsieciowe Maskarady

**Podsieciowe Maskarady (SmartApp)** to aplikacja desktopowa napisana w Pythonie (`CustomTkinter`), stworzona po to, aby pomóc studentowi zapanować nad kolokwiami, projektami, sprawozdaniami i codziennymi sprawami. Łączy wygodę pracy na **tablicy Kanban (z przeciąganiem kart)**, **interaktywnym kalendarzu** oraz **klasycznej liście** z autorskim systemem grywalizacji nagradzającym planowanie z wyprzedzeniem i sesje głębokiej pracy.

## 1. Jak uruchomić aplikację

### Wymagania wstępne

* **Python 3.10+** (zalecany Python 3.11 / 3.12)
* Jedyna zewnętrzna biblioteka to **`customtkinter`** (wszystkie pozostałe funkcje — w tym generator plików PDF, kalendarz oraz powiadomienia systemowe — opierają się na bibliotece standardowej Pythona: `json`, `re`, `datetime`, `calendar`, `pathlib`, `subprocess`, `tkinter`).

### Instalacja i start (Windows — PowerShell / CMD)

```bash
# 1. Sklonuj repozytorium i wejdź do folderu projektu
git clone <link-do-tego-repozytorium>
cd best-hackathon-eleminacja

# 2. Utwórz i aktywuj środowisko wirtualne
python -m venv .venv
.\.venv\Scripts\activate

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Uruchom aplikację
python main.py
```

### Instalacja i start (Linux / macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### Testowanie na własnym pliku `zadania.json`

* Przy uruchomieniu program automatycznie wczytuje plik `zadania.json`, jeśli znajduje się w katalogu głównym aplikacji.
* W dowolnym momencie można kliknąć przycisk **`Wczytaj JSON`** na górnym pasku, aby załadować dowolny plik testowy jury, oraz **`Zapisz JSON`** / **`Zapisz jako JSON`**, aby wyeksportować stan zadań w dokładnie tym samym schemacie (`"wersja": 1`, `"zadania": [...]`).
* Stan grywalizacji (punkty, streak, liga, sesje Pomodoro) zapisywany jest w osobnym pliku lokalnym `gamification_stats.json`, dzięki czemu plik `zadania.json` pozostaje w 100% zgodny ze specyfikacją.

## 2. Co działa, a czego nie zdążyliśmy zrobić

### ✅ Co działa w pełni

* **Pełny CRUD i obsługa schematu JSON:**
  * Wyświetlanie listy zadań, dodawanie nowych, edycja wszystkich pól (`tytul`, `opis`, `termin`, `priorytet`, `tagi`), oznaczanie jako zrobione (z możliwością cofnięcia) oraz usuwanie.
  * Pełna zgodność importu i eksportu z formatem `zadania.json` (poprawna obsługa `termin: null`, pustych opisów `""`, pustych list tagów `[]` oraz priorytetów `niski`, `sredni`, `wysoki`).
* **3 zsynchronizowane widoki pracy:**
  * **Tablica Kanban (Drag & Drop):** Podział na 6 kolumn (*Po terminie*, *Na dziś*, *Na ten tydzień*, *Na przyszły tydzień*, *Brak terminu*, *Zrobione*). Przeciągnięcie karty myszką do innej kolumny automatycznie aktualizuje datę `termin` lub status `wykonane`.
  * **Kalendarz miesięczny:** Kolorowe oznaczenia priorytetów, wykrywanie spiętrzeń (`🔥` przy minimum 3 niewykonanych zadaniach jednego dnia) oraz panel inspektora wybranego dnia z podglądem puli punktów i szybkim dodawaniem zadań na wybraną datę.
  * **Lista klasyczna:** Szczegółowy widok kart z metadanymi i szybkimi akcjami.
* **Wyszukiwarka na żywo i filtrowanie po każdym parametrze:** Natychmiastowe filtrowanie po ID, tytule, opisie, statusie (`Wszystkie`, `Do zrobienia`, `Po terminie`, `Zrobione`), priorytecie, rodzaju terminu (`Na dziś`, `Po terminie`, `Z terminem`, `Bez terminu (null)`) oraz dynamicznie wykrywanych `#tagach`.
* **Warstwa „Smart”, Pomodoro 25/5, raport PDF i powiadomienia 24h:** Algorytm *Smart Focus* z wbudowanym timerem Pomodoro (`+3 pkt`), parser *Quick-Add*, cotygodniowe cele, licznik *Streak*, system 5 lig z wysuwanym panelem bocznym (`▶ Ligi`), eksport podsumowania tygodnia do PDF (`📄 Raport PDF`) oraz natywne przypomnienia systemowe o terminach do 24h (`🔔`).

### 🚧 Pomysły na dalszy rozwój (poza zakresem eliminacji)

* **Synchronizacja z zewnętrznymi kalendarzami (Google Calendar / iCal / plan zajęć uczelni):** Automatyczny import terminów kolokwiów i oddań projektów z planu studiów.
* **Tryb projektów grupowych:** Współdzielenie tablicy zadań między członkami zespołu projektowego na studiach wraz ze wspólnym celem tygodniowym.

## 3. Co dodaliśmy od siebie i dlaczego akurat to

Zależało nam, aby aplikacja nie była kolejną pasywną listą „to-do”, lecz realnie zmieniała nawyki studenta i przeciwdziałała odkładaniu nauki na ostatnią chwilę:

1. **Odwrócona punktacja za planowanie z wyprzedzeniem (`+5 / +4 / +3 pkt`):**
   * Zamiast nagradzać „gaszenie pożarów”, przyznajemy **5 pkt za priorytet niski**, **4 pkt za średni** i **3 pkt za wysoki**.
   * *Dlaczego?* Zadania o niskim priorytecie to zazwyczaj sprawy z odległym terminem. System motywuje studenta, aby zamykał je zawczasu, zanim urosną do rangi pilnego kryzysu przed sesją.
2. **Tygodniowy cel, licznik Streak oraz Ligi Systematyczności (inspiracja Duolingo):**
   * Na początku tygodnia aplikacja pyta studenta o realny cel liczby zadań do zrealizowania. Dowiezienie celu podbija cotygodniowy **Streak (`🔥`)**, a zdobyte punkty pozwalają awansować przez **5 lig** (*Brązowa → Srebrna → Złota → Platynowa → Diamentowa*), których postęp można podejrzeć w wysuwanym pasku bocznym (`▶ Ligi`).
   * Jeśli student przez cały tydzień nie zrealizuje swojego celu, traci streak oraz **10 punktów**, co może spowodować spadek do niższej ligi — utrzymanie wysokiej rangi wymaga regularnej pracy.
   * **Zabezpieczenie przed „farmieniem” punktów:** Aplikacja blokuje ponowne punktowanie tych samych zadań po odznaczeniu, a przy wczytaniu nowego pliku JSON ostrzega użytkownika i zeruje postęp bieżącego tygodnia.
   * *Wskazówka dla Jury:* W panelu ligowym umieściliśmy przycisk **`Symuluj koniec tyg.`**, który pozwala od razu przetestować rozliczenie tygodnia (wzrost streaku lub karną utratę punktów i spadek z ligi) bez konieczności czekania 7 dni.
3. **Algorytm „Smart Focus” + wbudowany tryb skupienia Pomodoro (25/5 min):**
   * Aplikacja automatycznie analizuje wszystkie niewykonane zadania pod kątem bliskości terminu, zaległości, priorytetu oraz słów kluczowych typowych dla studiów (*kolokwium*, *egzamin*, *projekt*, *oddanie*, *sprawozdanie*, *zaliczenie*) i przypina na górze jedno najważniejsze zadanie wraz z uzasadnieniem.
   * Bezpośrednio obok zadania *Smart Focus* znajduje się timer **Pomodoro (25 min pracy / 5 min przerwy)** — ukończenie pełnej sesji bez przerywania nagradzane jest bonusem **+3 pkt** do ligi oraz sygnałem dźwiękowym.
4. **Szybkie dodawanie z parsowaniem tekstu (Quick-Add):**
   * Wpisanie w jedno pole np. `Kolokwium z sieci !wysoki @jutro #studia` automatycznie rozpoznaje tytuł, priorytet (`!wysoki`), datę (`@dzis`, `@jutro`, `@RRRR-MM-DD`) oraz tagi (`#studia`), oszczędzając czas podczas wykładów.
5. **Eksport podsumowania tygodnia do PDF (`📄 Raport PDF`) i powiadomienia 24h (`🔔`):**
   * Jednym kliknięciem można wygenerować estetyczny raport PDF z postępami w lidze, liczbą sesji Pomodoro oraz listą zadań wykonanych i zaległych, a przy starcie aplikacji (lub po kliknięciu ikony dzwonka) system wysyła powiadomienie o zadaniach zbliżających się w ciągu najbliższych 24 godzin.

## Struktura projektu

* `main.py` — główne okno aplikacji, integracja widoków, timera Pomodoro, filtrów oraz wysuwanego panelu lig.
* `storage.py` — walidacja, odczyt i zapis pliku `zadania.json` zgodnie ze specyfikacją.
* `smart.py` — parser szybkiego dodawania (*Quick-Add*), wykrywanie zaległości oraz silnik rekomendacji *Smart Focus*.
* `gamification.py` — logika odwróconej punktacji, sesji Pomodoro, cotygodniowych celów, streaku oraz awansów i spadków w ligach.
* `kanban.py` — interaktywna tablica Kanban z obsługą przeciągania kart (*Drag & Drop*).
* `calendar_view.py` — widok kalendarza miesięcznego z kolorowymi pigułkami priorytetów i inspektorem dnia.
* `reports_and_alerts.py` — generator wielostronicowego raportu PDF (z obsługą polskich znaków) oraz powiadomienia systemowe o terminach 24h.
* `zadania.json` — przykładowy zestaw zadań zgodny ze schematem konkursowym.
* `requirements.txt` — lista zależności projektu.