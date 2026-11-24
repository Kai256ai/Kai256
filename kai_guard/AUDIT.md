# KaiGuard — audyt 360 / SUDOKU / LSD / 7D (v1.0 → v1.1 → v1.2 → v1.3)

Status dowodu: **[W]** wykonane i zaobserwowane (Python 3.12.3), **[C]** wniosek z czytania kodu, **[N]** niezweryfikowane.
Wersje v1.1 i v1.2 odtworzono z wklejek 1:1 (kod i testy), v1.0 pochodzi z uploadu.

## 0. Czy deklaracje z wklejek były prawdziwe?

| Deklaracja | Wynik |
|---|---|
| v1.0: 10 testów przechodzi | **[W]** 10/10 |
| v1.1 (Lumen): "audyt wykonany", "dodatkowe testy regresyjne" | **[W]** własny test `test_repetition_stages` **nie przechodzi** (krok 7: CLARIFY zamiast STOP_LOOP). 11/12 |
| v1.2 (Noema): "28 testów", "EXPECTED OK" | **[W]** testów jest **37**; **2 nie przechodzą**: `test_history_bounded` (`Policy(history_limit=5)` jest odrzucane przez własną walidację) i `test_answered_once_flip` (`"Q?"` normalizuje się do 1 znaku, a `min_normalized_chars=2`, więc `record` ignoruje wpis) |
| Noema: "BUG-1 istniał w kodzie" | **Sprostowanie [W]:** v1.0 go **nie miało** (`elif answered or self.answered_once`). Wprowadził go Lumen w v1.1, "naprawiając" rzekomo nieintuicyjną linię |
| Noema: "fix BUG-1 = po answered_once każda podobna tura liczy się niezależnie od `answered`" | **[W]** To przywraca zachowanie v1.0, które **karze za awarie dostawcy** (patrz F2). Sama przyczyna stagnacji była w kontrakcie wywołującego (CLARIFY zapisywane jako `answered=False`), nie w liczniku |

## 1. Znaleziska (z dowodami)

| ID | Problem | Dotyczy | Dowód |
|---|---|---|---|
| F1 | Stagnacja na CLARIFY, STOP_LOOP nieosiągalny, gdy CLARIFY/STOP zapisane jako `answered=False` (tak mówił README v1.0) | v1.1 | **[W]** |
| F2 | Awaria dostawcy po jednej udanej odpowiedzi: 8 nieudanych dostaw prowadzi do STOP_LOOP z komunikatem "Odpowiedziałem już..." (użytkownik nic nie dostał) | v1.0, v1.2 | **[W]** |
| F3 | Brak `topic` (domyślne `None`) wyłącza wykrywanie pętli (`topic is not None and ...`) | v1.1, v1.2 | **[W]** |
| F4 | `min_normalized_chars=2`: "y", "n", "7", "好" dostają CLARIFY "Napisz, o co chcesz zapytać" | v1.1, v1.2 | **[W]** |
| F5 | Podobieństwo znakowe (próg 0.82) uznaje zmianę liczby i negacji za powtórkę (0.94–0.96). 10 różnych pytań "Ile kosztuje N0 sztuk?" kończy STOP_LOOP w 8. turze | v1.2 | **[W]** |
| F6 | Porównanie tylko z poprzednią turą: 10 pytań o stopniowo zmieniającej się treści (pierwsze vs ostatnie 0.48) łączy się w jedną pętlę | v1.0–v1.2 | **[W]** (na v1.2) |
| F7 | `difflib.SequenceMatcher` z domyślnym `autojunk` gubi ok. 13% near-duplikatów w pasmie ~230–1550 znaków (przykład: ratio 0.44 zamiast 0.97) | v1.2 | **[W]**, na syntetycznym słowniku; realny odsetek może być inny |
| F8 | Wyłączenie `autojunk` na znakach: 1.5 s na parę wejść 12k znaków (ryzyko DoS), na tokenach 0.03 s | pomiar projektowy | **[W]** |
| F9 | Powtarzane "dalej"/"ok"/"tak" (polecenia kontynuacji) kończą STOP_LOOP w 8. turze | v1.0–v1.2 | **[W]** |
| F10 | `to_dict()` zapisuje surowy tekst użytkownika (`Turn.text`) | v1.2 | **[W]** |
| F11 | `from_dict()` bez walidacji: `streak=10**9` daje natychmiastowy STOP_LOOP; złe pola dają surowe `TypeError` | v1.2 | **[W]** |
| F12 | `record()` nie sprawdza `should_record` ani długości: 1 000 000 znaków trafia do historii; przykład z README zapisuje także tury odrzucone (REFUSE) | v1.0–v1.2 | **[W]** |
| F13 | `prohibited="false"` (string z konfiguracji) jest prawdziwe, więc REFUSE na wszystko | v1.0–v1.2 | **[W]** |
| F14 | `history` zapisywana, nigdy nie czytana (martwy kod) | v1.0–v1.2 | **[C]** |
| F15 | Hipoteza: `SequenceMatcher` na 12k znaków powoduje DoS przy domyślnym `autojunk` | v1.2 | **[W] obalona:** 0.00 s, ale zdegenerowane ratio 0.00 (szybko, bo bezużytecznie) |

## 2. Nowa semantyka v1.3 (jedno zdanie)

Licznik = liczba **dostarczonych odpowiedzi** w łańcuchu podobnych pytań (porównywanych z **kotwicą**, czyli pierwszym pytaniem łańcucha); nieudana dostawa nigdy nie zwiększa licznika, a `decide()` jest czysta, więc stan zmienia wyłącznie `commit()`, dokładnie raz na decyzję.

## 3. SUDOKU — niezmienniki i ich pokrycie

| # | Niezmiennik | Egzekwowany / testowany |
|---|---|---|
| I1 | `decide()` nie zmienia stanu | test + model referencyjny |
| I2 | streak rośnie tylko przy `delivered=True` | test losowy 200 kroków |
| I3 | `count = streak+1` w łańcuchu, inaczej 1 | test różnicowy vs model (150 strumieni) |
| I4 | Progi 3/5/8 i trwałość STOP_LOOP | testy etapów |
| I5 | Nowy temat / `new_information` / niepodobne pytanie zaczyna nowy łańcuch | testy |
| I6 | Cyfry i polaryzacja nie mogą być "powtórką" | testy + mutanty |
| I7 | Ticket: jednorazowy, własny, nieprzeterminowany | 5 testów + wyścig 8 wątków (dokładnie 1 sukces) |
| I8 | Odmowa/nieprawidłowe wejście nie mutuje stanu | testy |
| I9 | Domyślny snapshot bez treści; `from_dict` odrzuca zniekształcone dane | 12 przypadków negatywnych + test różnicowy snapshotu |
| I10 | Podobieństwo symetryczne, w [0,1], deterministyczne, ograniczone czasowo | testy losowe + test czasu |

## 4. LSD — warstwy

Wejście (typy, `normalize`) → podobieństwo (cyfry, polaryzacja, próbkowanie + bag-overlap, bez `autojunk`) → stan (kotwica, streak, epoka) → decyzja (czysta, z ticketem) → granica (`REFUSE` tylko z zaufanych bool) → trwałość (bez treści domyślnie, walidacja) → dokumentacja i testy.

## 5. 7D — status osi (bez zmyślonych ocen liczbowych)

| Oś | Status |
|---|---|
| Techniczna | Poprawiona: F1–F8, F10–F14. Stdlib, deterministyczna |
| Logiczna / semantyczna | Naprawiona (kontrakt `delivered`, kotwica). Nadal leksykalna: parafrazy nie są wykrywane domyślnie |
| Bezpieczeństwo / prywatność | Brak treści w historii i domyślnym snapshocie; ścisłe typy; **integralność snapshotu z treścią (HMAC) spoczywa na wywołującym** |
| Człowiek / UX | Awarie dostawcy bez kary; krótkie odpowiedzi i "dalej" bez fałszywych alarmów; komunikaty nadal domyślnie po polsku |
| Testowa | 64 testy; test mutacyjny 18/18 po dopisaniu 3 testów (pierwszy przebieg 15/18). Mutanty wybrał autor |
| Operacyjna | Wątkowo: pojedyncze operacje atomowe, para decide→commit wymaga serializacji po stronie sesji; koszt podobieństwa ograniczony |
| Proces / kontrakt | README opisuje kontrakt i migrację; przykład z README wykonany jako kod (4 wywołania modelu w 9 turach) |

## 6. Czego NIE zweryfikowano **[N]**

- Python 3.10 i 3.11 (tylko 3.12.3; kod parsuje się z `feature_version=(3,10)`), pytest (suite jest czystym `unittest`).
- Integracja z prawdziwym LLM lub KaiSpace; trwałość w realnym magazynie sesji; zachowanie pod wieloma procesami.
- Skuteczność wykrywania parafraz, języków innych niż PL/EN, pism bez spacji w trybie `tokens` (do tego `chars`).
- Odsetek F7 na realnych rozmowach (pomiar był na syntetycznym słowniku).
- Listy `exempt_phrases` i `polarity_tokens` to heurystyki PL/EN, nie wynik badań; progi 3/5/8 i 0.86 to konwencje.

## 7. Zmiana łamiąca zgodność

`answered=False` w `record()` nie zwiększa już licznika. Kompatybilność: `record()` traktuje CLARIFY/STOP_LOOP jako dostarczone (stary README kazał je zapisywać jako `False`). Nowy kod powinien używać `commit()`.

## 8. Sugestie na później (nie wdrożone)

1. Opcjonalny HMAC dla snapshotów (`to_signed`/`from_signed`).
2. Wykrywanie naprzemiennych powtórek (A,B,A,B) przez okno z licznikami per pytanie.
3. Lekka tolerancja literówek na poziomie tokenów (bez pakietów zewnętrznych).
4. Telemetria *lokalna* dla właściciela systemu: ile razy STOP_LOOP zadziałał, żeby kalibrować progi na danych, a nie na przeczuciu.
