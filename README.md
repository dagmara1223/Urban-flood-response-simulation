# Flood Simulation - Instrukcja uruchomienia

## 1. Instalacja środowiska

Utwórz środowisko Conda:

```bash
conda env create -f environment.yml
````

Aktywuj środowisko:

```bash
conda activate flood-simulation
```

## 2. Przygotowanie danych

Upewnij się, że w katalogu `Data/` znajdują się niezbędne pliki:

* `krakow_merged.tif` – numeryczny model terenu (DEM)
* `krakow_roads_all_2.graphml` – graf dróg miejskich

## 3. Uruchomienie symulacji

Domyślny scenariusz (scenario 0, 160 kroków symulacji):

```bash
python main.py
```

Można też uruchomić wybrany scenariusz i liczbę kroków:

```bash
python main.py <scenariusz> <liczba_kroków>
```

Przykłady:

* Scenariusz 1 (podwójna liczba ratowników) z 500 krokami:

```bash
python main.py 1 500
```

* Scenariusz 3 (intensywne opady) z domyślną liczbą kroków:

```bash
python main.py 3
```

## 4. Wyniki

* Wyniki symulacji i statystyki zostaną zapisane w katalogu `output/run_<timestamp>/`.

## 5. Scenariusze

| Scenariusz | Opis                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------ |
| 0          | **Domyślny** – standardowa liczba ratowników (6), normalne opady, standardowe decyzje agentów.   |
| 1          | **Podwójna liczba ratowników** – 12 ratowników, pozostałe parametry jak w scenariuszu domyślnym. |
| 2          | **Potrójna liczba ratowników** – 18 ratowników, pozostałe parametry jak w scenariuszu domyślnym. |
| 3          | **Intensywne opady** – podwójne opady (większa wysokość deszczu w każdym bloku czasowym).        |
| 4          | **Zmienione decyzje agentów (mode 1)** – mieszanka strategii: 1 RANDOM, 1 FOLLOWER, 6 DIJKSTRA.  |
| 5          | **Zmienione decyzje agentów (mode 2)** – mieszanka strategii: 2 RANDOM, 6 DIJKSTRA.              |
| 6          | **Zmienione decyzje agentów (mode 3)** – mieszanka strategii: 2 FOLLOWER, 6 DIJKSTRA.            |
| 7          | **Zmienione decyzje agentów (mode 4)** – mieszanka strategii: 1 RANDOM, 3 DIJKSTRA, 1 FOLLOWER.  |
