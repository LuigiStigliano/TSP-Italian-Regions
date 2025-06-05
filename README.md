# Italian Regions TSP Solver

Questo repository contiene una soluzione al **Problema del Commesso Viaggiatore (TSP)** applicata a tutte le **regioni italiane**, permettendo di selezionare una regione e una città di partenza arbitraria.

---

## Introduzione al Problema del Commesso Viaggiatore

Il Traveling Salesman Problem (TSP) è un classico problema di ottimizzazione combinatoria:

> Dato un insieme di città e le distanze tra ogni coppia di esse, trovare il percorso più breve che visiti ciascuna città esattamente una volta e ritorni alla città di partenza.

È un problema **NP-difficile**, quindi per istanze medio-grandi si utilizzano algoritmi euristici o metaeuristici.

### Applicazioni del TSP

- Logistica e pianificazione di consegne
- Progettazione elettronica (PCB)
- Sequenziamento genetico
- Automazione industriale

---

## Caratteristiche del Progetto

- Import automatico delle città da OpenStreetMap tramite Overpass API
- Calcolo automatico della matrice delle distanze (Haversine)
- Risoluzione del TSP con Nearest Neighbor + Iterated Local Search (ILS)
- Possibilità di selezionare regione, città di partenza, e soglie sulla popolazione
- Visualizzazione del percorso su mappa
- Supporto caching per minimizzare richieste all'API
- **Interfaccia web** per un utilizzo interattivo e intuitivo

---

## ⚠️ Problemi Noti

- **Regioni non funzionanti**: Attualmente, le seguenti regioni potrebbero non restituire risultati o non funzionare come previsto a causa di discrepanze nella nomenclatura o nella struttura dei dati su OpenStreetMap:
    - Sardegna
    - Valle d'Aosta

---

## Installazione

1. Clonare il repository:
   ```
   git clone https://github.com/LuigiStigliano/TSP-Italian-Regions.git
   cd TSP-Italian-Regions
   ```

2. Creare e attivare un ambiente virtuale:
   ```
   # Su Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Su macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Installare le dipendenze:
   ```
   pip install -r requirements.txt
   ```
---

## Utilizzo

Il progetto può essere utilizzato in due modalità differenti:

### 1. Interfaccia a riga di comando

Esegui il programma:

```bash
python main.py
```

#### Parametri disponibili

| Argomento                 | Default                   | Descrizione                                                         |
|--------------------------|---------------------------|---------------------------------------------------------------------|
| `--region`               | `"basilicata"`            | Regione italiana di interesse                                       |
| `--start-city`           | `"Potenza"`               | Città di partenza                                                   |
| `--min-population`       | `1000`                    | Popolazione minima per filtrare le città                           |
| `--refresh-data`         | `False`                   | Forza il recupero dati da OpenStreetMap                             |
| `--visualize`            | `False`                   | Mostra il percorso su una mappa                                     |
| `--max-iterations`       | `1000`                    | Iterazioni per l'Iterated Local Search                              |
| `--user-agent`           | `"ItalianRegionsTSP/1.0"` | User-Agent per l'API (obbligatorio)                                 |
| `--output`               | `None`                    | Salva i risultati in un file `.txt`                                 |
| `--save-visualization`   | `None`                    | Salva la visualizzazione su file `.png`                             |

#### Esempio completo

```bash
python main.py --region lombardia --start-city Milano --min-population 20000 --refresh-data --visualize --max-iterations 2000 --user-agent "ItalianRegionsTSP/1.0" --output risultati.txt --save-visualization mappa.png
```

### 2. Interfaccia Web

L'applicazione web offre un'interfaccia grafica intuitiva per risolvere il problema TSP.

#### Avvio dell'applicazione web

```bash
python app.py
```

Dopo l'avvio, l'applicazione sarà accessibile all'indirizzo [http://localhost:5000](http://localhost:5000) dal tuo browser.

#### Funzionalità dell'interfaccia web

- **Selezione regione**: seleziona facilmente la regione italiana di interesse
- **Filtraggio città**: imposta la popolazione minima per filtrare le città
- **Aggiornamento dati**: opzione per forzare l'aggiornamento dei dati da OpenStreetMap
- **Selezione città di partenza**: visualizza e scegli tra le città disponibili
- **Configurazione algoritmo**: imposta il numero massimo di iterazioni
- **Visualizzazione risultati**: visualizza il percorso ottimale su una mappa interattiva
- **Esportazione**: scarica i risultati in formato testo

---

## Dettagli degli Algoritmi

### Algoritmo Nearest Neighbor

Costruisce una soluzione iniziale scegliendo sempre la città più vicina tra quelle non ancora visitate.

- **Pro**: veloce (O(n²)), semplice
- **Contro**: non garantisce soluzioni ottime

### Algoritmo Iterated Local Search (ILS)

Migliora iterativamente il percorso:

1. **2-opt**: scambia segmenti per ridurre la lunghezza del tour
2. **Double-bridge move (4-opt)**: perturbazione per uscire da minimi locali
3. **Criteri di accettazione**: si accettano solo soluzioni migliorative
4. **Terminazione**: massimo numero di iterazioni o stagnazione

---

## Classe TSPSolver

```python
# Esempio
solver = TSPSolver(distance_matrix, city_names)
path, dist = solver.solve(start_city_index=0)
print(solver.get_path_with_names())
```

### Metodi principali:
- `solve()`: esegue NN + ILS
- `get_path_with_names()`: restituisce i nomi delle città nel percorso
- `get_path_details()`: informazioni sulle singole tratte

---

## Visualizzazione

Il percorso può essere visualizzato su una mappa salvata in `.png`. I dati geografici sono proiettati correttamente e il percorso viene tracciato tra le città.

- **Interfaccia a riga di comando**: visualizzazione statica con opzione di salvataggio
- **Interfaccia web**: visualizzazione integrata nella pagina dei risultati

---

## Note su OpenStreetMap

- L'API Overpass è usata per estrarre città e coordinate
- I dati sono **cacheati** nella cartella `data/`
- Il filtro `--min-population` ha effetto solo con `--refresh-data`
- Rispettiamo i [termini d'uso](https://operations.osmfoundation.org/policies/nominatim/), incluso:
  - User-Agent obbligatorio
  - Limite 1 richiesta/sec
