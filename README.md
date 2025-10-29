# 🌊 Urban Flood Response Simulation

Symulacja wieloagentowa przedstawiająca reakcję miasta Krakowa na powódź z 2010 roku.  
Projekt ma na celu odwzorowanie zarówno **rozprzestrzeniania się wody na obszarze miasta**, jak i **zachowań agentów** reprezentujących mieszkańców, służby ratunkowe oraz centrum dowodzenia.  
Model łączy dane topograficzne, graf dróg miejskich oraz inteligentne zachowania agentów, tworząc spójne środowisko do badania procesów ewakuacji i zarządzania kryzysowego.

---

## 🎯 Cel projektu

W maju 2010 roku Kraków został dotknięty jedną z największych powodzi w historii miasta.  
W projekcie dążymy do stworzenia **symulacji komputerowej** tego typu zjawiska, aby:

- odwzorować proces **rozlewania się wody** w miejskim środowisku,  
- analizować skuteczność **reakcji mieszkańców i służb ratunkowych**,  
- testować różne strategie **ewakuacji i koordynacji działań**,  
- dostarczyć narzędzie edukacyjne i badawcze dla analiz systemów miejskich w sytuacjach kryzysowych.

Model składa się z kilku współpracujących ze sobą modułów, które odpowiadają za różne aspekty powodzi i reagowania na nią.

---

## 📁 Struktura projektu


```
Urban-flood-response-simulation/
│
├── Data/
│   ├── create_graph.py          # Skrypt tworzący graf drogowy miasta z pliku GraphML
│   └── krakow_roads.graphml     # Sieć drogowa Krakowa (wykorzystywana przez agentów)
│
├── Integration/
│   └── (puste)                  # Folder do integracji przepływu wody i ruchu agentów
│
├── agent_model/
│   ├── citizens/                # Podmodel agentów-mieszkańców
│   ├── call_center_agent.py     # Agent centrum zgłoszeń (koordynacja i komunikacja)
│   ├── evac_model.py            # Model ewakuacji i podejmowania decyzji przez obywateli
│   └── rescue_agent.py          # Agent służb ratunkowych reagujących na zagrożenie
│
├── flood-agent/
│   ├── data/                    # (puste) dane wejściowe do symulacji hydrologicznej
│   ├── docs/                    # Dokumentacja PDF i opis matematyczny modelu przepływu
│   ├── model/                   # Kod symulacji przepływu wody w Pythonie
│   └── output/                  # Wyniki symulacji (mapy, wykresy, dane numeryczne)
│
├── .gitignore                   # Plik ignorujący zbędne pliki przy commitach
├── README.md                    # Krótki opis projektu (ten plik)
└── requirements.txt              # Lista wymaganych bibliotek Python
```
## 🧩 Opis modułów

### 🌧️ `flood-agent`
Zawiera model hydrodynamiczny symulujący **przepływ powierzchniowy wody** na uproszczonej siatce terenu.  
Model oblicza różnice wysokości między komórkami (teren + woda), pozwalając wodzie przepływać w dół zgodnie z gradientem wysokości.  
Wynikiem są mapy rozlewania się wody w kolejnych krokach czasowych.

### 🧍 `agent_model`
Odpowiada za modelowanie **zachowań agentów** w środowisku miejskim.  
Zawiera:
- agentów-mieszkańców podejmujących decyzje o ewakuacji,  
- agentów służb ratunkowych koordynujących działania,  
- centrum zgłoszeń (agent komunikacyjny),  
- modele trasowania na podstawie sieci dróg (`krakow_roads.graphml`).

### 🗺️ `Data`
Odpowiada za **przygotowanie grafu drogowego** na podstawie rzeczywistych danych z Krakowa.  
Dzięki temu agenci mogą poruszać się po realistycznej siatce ulic i analizować, jak powódź wpływa na dostępność dróg.

### 🔗 `Integration`
Moduł integrujący przepływ wody z ruchem agentów — w przyszłości będzie łączyć model hydrologiczny z zachowaniami ludzi, aby uzyskać pełną symulację miasta w czasie rzeczywistym.

---

## ⚙️ Uruchomienie projektu

1. Zainstaluj wymagane biblioteki:
   ```bash
   pip install -r requirements.txt
<br>
   TBC
