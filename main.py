"""
Interfaccia a Riga di Comando per il Risolutore TSP delle Regioni Italiane.

Questo script permette agli utenti di risolvere il Problema del Commesso Viaggiatore (TSP)
per le città di una regione italiana specificata tramite la riga di comando.
Recupera i dati delle città da OpenStreetMap, calcola le distanze, risolve il TSP
utilizzando un'euristica Nearest Neighbor seguita da Iterated Local Search (ILS),
e può visualizzare o salvare i risultati, inclusa una visualizzazione su mappa.
"""

import sys
import argparse
import time
import os

# Importa i moduli personalizzati dalla directory src
from src.data_fetcher import NominatimFetcher
from src.distance_matrix import DistanceCalculator
from src.visualization import TSPVisualizer # Per generare visualizzazioni statiche della mappa
from src.NN_ILS import TSPSolver # L'algoritmo principale di risoluzione TSP

def parse_arguments():
    """
    Analizza gli argomenti della riga di comando per il risolutore TSP.

    Returns:
        argparse.Namespace: Un oggetto contenente gli argomenti analizzati dalla riga di comando.
    """
    parser = argparse.ArgumentParser(description='Risolutore del TSP per le regioni italiane') #

    parser.add_argument('--region', type=str, default="basilicata", #
                        help='Nome della regione italiana (default: basilicata). Es., "lombardia", "sicilia".')
    parser.add_argument('--start-city', type=str, default="Potenza", #
                        help='Nome della città di partenza (default: Potenza). Deve essere una città della regione selezionata.')
    parser.add_argument('--min-population', type=int, default=1000, #
                        help='Popolazione minima per includere una città (default: 1000).')
    parser.add_argument('--refresh-data', action='store_true', #
                        help='Forza il recupero di nuovi dati da OpenStreetMap, ignorando i dati in cache.')
    parser.add_argument('--visualize', action='store_true', #
                        help='Mostra il percorso del TSP su una mappa interattiva (finestra matplotlib).')
    parser.add_argument('--save-visualization', type=str, default=None, #
                        help='Salva la visualizzazione del percorso TSP su file (es., "mappa.png"). Il percorso è relativo a static/images/.')
    parser.add_argument('--user-agent', type=str, default="ItalianRegionsTSP-CLI/1.0", #
                        help="User-Agent per l'API Nominatim (default: ItalianRegionsTSP-CLI/1.0). Richiesto dalle policy di OSM.")
    parser.add_argument('--output', type=str, default=None, #
                        help='File di output per i risultati testuali (es., "risultati.txt"). Il percorso è relativo a static/.')
    parser.add_argument('--max-iterations', type=int, default=1000, #
                        help="Numero massimo di iterazioni per l'algoritmo Iterated Local Search (ILS) (default: 1000).")

    return parser.parse_args()

def find_city_index(city_name, cities):
    """
    Trova l'indice di una città specificata all'interno di una lista di oggetti città.

    Gestisce corrispondenze esatte e parziali (chiedendo all'utente se vengono trovate
    corrispondenze parziali multiple). Utilizza la prima città come default se non
    vengono trovate corrispondenze o se l'input dell'utente non è valido.

    Args:
        city_name (str): Il nome della città da trovare.
        cities (list): Una lista di dizionari città, dove ogni dizionario
                       deve contenere una chiave 'name'.

    Returns:
        int: L'indice della città trovata nella lista.
    """
    city_name_lower = city_name.lower()

    # Tenta prima una corrispondenza esatta
    for i, city in enumerate(cities):
        if city['name'].lower() == city_name_lower:
            return i

    # Se non c'è corrispondenza esatta, cerca corrispondenze parziali
    matching_cities = []
    for i, city in enumerate(cities):
        if city_name_lower in city['name'].lower():
            matching_cities.append((i, city['name']))

    if not matching_cities:
        print(f"Attenzione: Città '{city_name}' non trovata. Verrà utilizzata la prima città disponibile: {cities[0]['name']}.")
        return 0 # Default alla prima città se non ci sono corrispondenze

    if len(matching_cities) == 1:
        print(f"Attenzione: Città '{city_name}' non trovata esattamente. Verrà utilizzata '{matching_cities[0][1]}' come corrispondenza più vicina.")
        return matching_cities[0][0]

    # Gestisce corrispondenze parziali multiple chiedendo all'utente
    print(f"Trovate più città che corrispondono a '{city_name}':")
    for i, (_, name) in enumerate(matching_cities):
        print(f"{i+1}. {name}")

    try:
        choice = int(input("Seleziona il numero della città desiderata: ")) - 1
        if 0 <= choice < len(matching_cities):
            return matching_cities[choice][0]
    except ValueError:
        # Gestisce input non intero
        pass
    except IndexError:
        # Gestisce input intero fuori range
        pass

    print(f"Selezione non valida. Verrà utilizzata '{matching_cities[0][1]}' come default.")
    return matching_cities[0][0]


def fetch_cities_data(args):
    """
    Recupera i dati delle città per la regione specificata utilizzando NominatimFetcher.

    Utilizza gli argomenti della riga di comando per determinare la regione,
    la popolazione minima, lo User-Agent e se aggiornare i dati.
    Esce se non vengono trovate città o se si verifica un errore durante il recupero.

    Args:
        args (argparse.Namespace): Argomenti analizzati dalla riga di comando.

    Returns:
        list: Una lista di dizionari città.
    """
    fetcher = NominatimFetcher(user_agent=args.user_agent) #
    try:
        print(f"Recupero delle città per la regione: {args.region.title()} (Pop. min: {args.min_population})")
        cities = fetcher.fetch_cities(args.region, refresh=args.refresh_data,
                                     min_population=args.min_population) #
        if not cities:
            print(f"Errore: Nessuna città trovata per la regione '{args.region.title()}' con i criteri specificati.")
            sys.exit(1)
        return cities
    except Exception as e:
        print(f"Errore critico durante il recupero delle città: {e}")
        print("Controlla la tua connessione internet o la validità della regione specificata.")
        sys.exit(1)

def solve_tsp_problem(cities, start_city_index, max_iterations):
    """
    Risolve il TSP per la lista di città data.

    Args:
        cities (list): Una lista di dizionari città.
        start_city_index (int): L'indice della città di partenza nella lista `cities`.
        max_iterations (int): Numero massimo di iterazioni per l'algoritmo ILS.

    Returns:
        tuple: Una tupla contenente:
            - tuple: (optimal_path_indices, total_distance)
            - TSPSolver: L'istanza del solver utilizzata.
    """
    calculator = DistanceCalculator(cities) #
    distance_matrix = calculator.calculate_distance_matrix() #
    city_names = [city['name'] for city in cities]

    solver = TSPSolver(distance_matrix, city_names) #
    solver_params = {"start_city_index": start_city_index, "max_iterations": max_iterations}
    solution_data, solver_instance = solver.solve(**solver_params), solver # Mantiene l'istanza
    return solution_data, solver_instance

def format_time_duration(seconds):
    """
    Formatta una durata in secondi in una stringa leggibile dall'utente.

    Args:
        seconds (float): La durata in secondi.

    Returns:
        str: Una stringa che rappresenta il tempo formattato (es. "2 minuti e 30.50 secondi").
    """
    if seconds < 60:
        return f"{seconds:.2f} secondi"
    elif seconds < 3600: # Meno di un'ora
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} minuti e {secs:.2f} secondi"
    else: # Un'ora o più
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours} ore, {minutes} minuti e {secs:.2f} secondi"

def display_tsp_results(region, start_city_name, optimal_path_indices, total_distance,
                        execution_time, path_with_names, path_details):
    """
    Stampa i risultati della soluzione TSP sulla console in modo formattato.

    Args:
        region (str): Il nome della regione italiana.
        start_city_name (str): Il nome della città di partenza.
        optimal_path_indices (list): Lista degli indici delle città che rappresentano il percorso ottimale.
        total_distance (float): La distanza totale del percorso ottimale in km.
        execution_time (float): Il tempo impiegato per risolvere il TSP in secondi.
        path_with_names (list): Lista dei nomi delle città nel percorso ottimale.
        path_details (list): Lista di tuple, ognuna delle quali dettaglia un segmento del percorso
                             (citta_partenza, citta_arrivo, distanza).
    """
    print("\n" + "="*60)
    print(f"  RISULTATO DEL TSP PER LE CITTÀ DELLA REGIONE {region.upper()}")
    print("="*60)
    print(f"  Algoritmo utilizzato: Nearest Neighbor + Iterated Local Search (ILS)")
    print(f"  Città di partenza: {start_city_name}")
    print(f"  Numero di città visitate (esclusa partenza ripetuta): {len(optimal_path_indices) - 1}")
    print(f"  Distanza totale percorsa: {total_distance:.2f} km")
    print(f"  Tempo di esecuzione del solver: {format_time_duration(execution_time)}")
    print("\n  Percorso ottimale:")
    print(f"    {' -> '.join(path_with_names)}")

    print("\n  Dettagli del percorso (tratte):")
    for i, (from_city, to_city, distance) in enumerate(path_details, 1):
        print(f"    {i:2d}. Da {from_city:<20} a {to_city:<20}: {distance:>7.2f} km")
    print("="*60)

def prepare_results_for_output_file(region, start_city_name, optimal_path_indices,
                                    total_distance, execution_time, path_with_names, path_details):
    """
    Prepara una lista di stringhe contenenti i risultati del TSP, formattati per il salvataggio su file di testo.

    Args:
        region (str): Il nome della regione italiana.
        start_city_name (str): Il nome della città di partenza.
        optimal_path_indices (list): Lista degli indici delle città nel percorso ottimale.
        total_distance (float): La distanza totale del percorso ottimale in km.
        execution_time (float): Il tempo impiegato per risolvere il TSP in secondi.
        path_with_names (list): Lista dei nomi delle città nel percorso ottimale.
        path_details (list): Lista di tuple, ognuna delle quali dettaglia un segmento del percorso.

    Returns:
        list: Una lista di stringhe, dove ogni stringa è una riga per il file di output.
    """
    results_data = [
        f"RISULTATO DEL TSP PER LE CITTÀ DELLA REGIONE {region.upper()}",
        "="*50,
        "Algoritmo utilizzato: Nearest Neighbor + Iterated Local Search (ILS)",
        f"Città di partenza: {start_city_name}",
        f"Numero di città visitate (esclusa partenza ripetuta): {len(optimal_path_indices) - 1}",
        f"Distanza totale percorsa: {total_distance:.2f} km",
        f"Tempo di esecuzione del solver: {format_time_duration(execution_time)}",
        "\nPercorso ottimale:",
        " -> ".join(path_with_names),
        "\nDettagli del percorso (tratte):"
    ]

    for i, (from_city, to_city, distance) in enumerate(path_details, 1):
        results_data.append(f"{i}. Da {from_city} a {to_city}: {distance:.2f} km")

    return results_data

def save_results_to_file(output_file_path, results_data_lines):
    """
    Salva i risultati TSP formattati in un file di testo specificato.

    Assicura che la directory per il file di output esista prima di scrivere.

    Args:
        output_file_path (str): Il percorso completo del file di testo di output.
        results_data_lines (list): Una lista di stringhe da scrivere nel file.
    """
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True) #
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for line in results_data_lines:
                f.write(line + "\n")
        print(f"\nRisultati salvati con successo in: {output_file_path}")
    except IOError as e:
        print(f"Errore durante il salvataggio dei risultati su file '{output_file_path}': {e}")

def manage_visualization(cities, optimal_path_indices, start_city_name, total_distance,
                         should_visualize, save_visualization_path):
    """
    Gestisce la creazione e la visualizzazione/salvataggio della visualizzazione del percorso TSP.

    Args:
        cities (list): Lista dei dizionari città.
        optimal_path_indices (list): Lista degli indici delle città per il percorso ottimale.
        start_city_name (str): Nome della città di partenza.
        total_distance (float): Distanza totale del percorso.
        should_visualize (bool): Se True, visualizza la mappa.
        save_visualization_path (str or None): Percorso per salvare l'immagine della mappa, o None.
    """
    print("\nGenerazione della visualizzazione della mappa...")
    visualizer = TSPVisualizer(cities, optimal_path_indices) #

    title = (f"Percorso TSP per {start_city_name} ({len(optimal_path_indices)-1} città) - "
             f"Distanza: {total_distance:.2f} km")

    # Assicura che la directory esista se si salva la visualizzazione
    if save_visualization_path:
        try:
            os.makedirs(os.path.dirname(save_visualization_path), exist_ok=True) #
        except OSError as e:
            print(f"Errore nella creazione della cartella per la visualizzazione '{save_visualization_path}': {e}")
            save_visualization_path = None # Impedisce il tentativo di salvataggio se la creazione della directory fallisce

    visualizer.plot_path(title=title, save_path=save_visualization_path) #

    if should_visualize:
        print("Visualizzazione del percorso (chiudere la finestra per continuare)...")
        visualizer.show() #
    elif save_visualization_path:
        print(f"Visualizzazione salvata in: {save_visualization_path}")


def main():
    """
    Funzione principale per eseguire l'applicazione CLI del risolutore TSP.

    Analizza gli argomenti, recupera i dati, risolve il TSP, visualizza i risultati
    e gestisce la visualizzazione e l'output su file in base ai flag utente.
    """
    args = parse_arguments() #
    overall_start_time = time.time() # Cronometra l'intero processo, incluso il recupero dati

    # Assicura che le directory necessarie esistano (data per la cache, static per gli output)
    if not os.path.exists('data'): #
        os.makedirs('data') #
    if not os.path.exists('static'): # Per --output
        os.makedirs('static') #
    if not os.path.exists('static/images'): # Per --save-visualization
        os.makedirs('static/images', exist_ok=True) #

    # 1. Recupera i dati delle città
    cities = fetch_cities_data(args)
    print(f"Recuperate {len(cities)} città per la regione {args.region.title()}.")

    # 2. Determina la città di partenza
    start_city_index = find_city_index(args.start_city, cities) #
    start_city_name = cities[start_city_index]['name']
    print(f"\nCittà di partenza selezionata: {start_city_name}")

    # 3. Risolve il TSP
    print("\nAvvio della risoluzione del TSP...")
    tsp_solve_start_time = time.time()
    (optimal_path_indices, total_distance), solver_instance = solve_tsp_problem(
        cities, start_city_index, args.max_iterations
    )
    tsp_execution_time = time.time() - tsp_solve_start_time

    # 4. Prepara e visualizza i risultati
    path_with_names = solver_instance.get_path_with_names() #
    path_details = solver_instance.get_path_details() #
    display_tsp_results(args.region, start_city_name, optimal_path_indices, total_distance,
                        tsp_execution_time, path_with_names, path_details) #

    # 5. Salva i risultati su file di testo se richiesto
    if args.output:
        output_file_path = os.path.join('static', args.output) # Salva nella directory 'static'
        results_to_save = prepare_results_for_output_file(
            args.region, start_city_name, optimal_path_indices, total_distance,
            tsp_execution_time, path_with_names, path_details
        ) #
        save_results_to_file(output_file_path, results_to_save) #

    # 6. Gestisce la visualizzazione (mostra o salva la mappa)
    if args.visualize or args.save_visualization:
        save_viz_path = None
        if args.save_visualization:
            # Salva nella directory 'static/images'
            save_viz_path = os.path.join('static', 'images', args.save_visualization) #

        manage_visualization(cities, optimal_path_indices, start_city_name, total_distance,
                           args.visualize, save_viz_path) #

    overall_execution_time = time.time() - overall_start_time
    print(f"\nProcesso completato in {format_time_duration(overall_execution_time)} (tempo totale).")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
        sys.exit(0)
    except Exception as e:
        # Cattura errori generici per problemi imprevisti nel flusso principale
        print(f"\nSi è verificato un errore imprevisto durante l'esecuzione: {e}")
        # Per debugging, potresti voler stampare il traceback completo:
        # import traceback
        # traceback.print_exc()
        sys.exit(1)