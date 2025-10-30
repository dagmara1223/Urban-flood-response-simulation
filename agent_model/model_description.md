## Model agentowy

### 1. Mieszkańcy (*CitizenAgent*)

Stan agenta ( C_i ) opisuje:

`S_i(t) ∈ {SAFE, UNSAFE, CRITICALLY_UNSAFE, RESCUED}`

Każdy obywatel wybiera ścieżkę do bezpiecznego punktu ( P_s ):

* **Tryb Dijkstra** – minimalizacja odległości:

  ```math
  \min_{p \in \mathrm{Paths}(i,P_s)} \sum_{(u,v)\in p} L_{uv}
  ```
* **Tryb losowy** – wybór losowego sąsiada,
* **Tryb follower** – podążanie za najbliższym agentem.

---

### 2. Ratownicy (*RescueAgent*)

Stan agenta ratowniczego ( R_j ):

```math
R_j(t) \in \{\mathtt{AVAILABLE},\ \mathtt{ON\_MISSION},\ \mathtt{CARRYING}\}
```

Parametry:

| Symbol     | Znaczenie               | Wartość przykładowa |
| ---------- | ----------------------- | ------------------- |
| ( v_d )    | prędkość jazdy (m/s)    | 8 ± 1               |
| ( cap )    | pojemność (liczba osób) | 2                   |
| ( s_{ij} ) | status drogi            | safe / unsafe       |

**Reguły ruchu i decyzji:**

1. Jeśli ( R_j ) jest `AVAILABLE` i w zasięgu są obywatele o stanie `CRITICALLY_UNSAFE` → CallCenter przydziela cel ( C_i ).
2. Ścieżka do celu wyznaczana jest po podgrafie:
   ```math
   G_{\mathrm{safe}} = \{ (u,v) \in E : s_{uv} = \mathrm{safe} \}
   ```

   lub pełnym grafie ( G ), jeśli nie istnieje bezpieczna ścieżka.
3. Po dotarciu do celu:

   ```math
   C_i.state \leftarrow \mathtt{RESCUED}, \quad R_j.state \leftarrow \mathtt{CARRYING}
   ```

   i wyznaczana jest ścieżka do najbliższego bezpiecznego węzła ( P_s ).
4. W ( P_s ): obywatele otrzymują stan `SAFE`, ( R_j ) staje się znów `AVAILABLE`.

---

### 3. Centrum koordynacji (*CallCenterAgent*)

Działa jak funkcja alokacji:

```math
A: \{C_i\} \times \{R_j\} \to \{(R_j, C_i)\}
```

Algorytm:

1. Wykryj obywateli ( C_i ) o stanie `CRITICALLY_UNSAFE`.
2. Dla każdego wybierz najbliższego dostępnego ratownika:

   ```math
   R_j^* = \arg\min_{R_j \in \mathrm{available}} d_G(R_j, C_i)
   ```
3. Przypisz cel, jeśli żaden ratownik nie jest już w drodze.

---

## 5. Interakcja modeli

Na koniec każdej iteracji:

1. Model hydrologiczny aktualizuje głębokości ( h(x,y,t) ).
2. Wartości są przypisywane do grafu ( G ) jako ( d_{ij}(t) ).
3. Ratownicy i obywatele reagują na te zmiany:

   * Obywatele mogą zmienić stan z `SAFE` → `UNSAFE` → `CRITICALLY_UNSAFE`,
   * Ratownicy omijają niebezpieczne drogi,
   * CallCenter przydziela zadania dynamicznie.

---

## 6. Parametry i skalowanie czasowe

| Parametr              | Opis                         | Wartość domyślna |
| --------------------- | ---------------------------- | ---------------- |
| ( k )                 | współczynnik przepływu wody  | 0.12             |
| ( d_{ij}(t) ) | granica nieprzejezdności (m) | 0.5              |
| ( Delta t )          | krok czasowy (s)             | 1                |
| ( v_c )               | prędkość obywatela (m/s)     | 1.5 ± 0.3        |
| ( v_r )               | prędkość ratownika (m/s)     | 8.0 ± 1.0        |

---

## 7. Wyniki i wizualizacja

Model wizualizuje w czasie rzeczywistym:

* sieć dróg (czarne – przejezdne, czerwone – zalane),
* położenie agentów (niebiescy – mieszkańcy, purpurowi – ratownicy),
* nakłada na tło raster głębokości wody (kolor niebieski).
