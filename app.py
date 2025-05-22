"""
Applicazione web Flask per il Risolutore TSP delle Regioni Italiane.

Questa applicazione fornisce un'interfaccia web per:
- Selezionare una regione italiana e filtrare le città per popolazione.
- Scegliere una città di partenza.
- Risolvere il Problema del Commesso Viaggiatore (TSP) per le città selezionate.
- Visualizzare il percorso ottimale su una mappa interattiva (utilizzando Folium).
- Permettere agli utenti di scaricare i risultati.
"""

from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import time
import uuid
import json
from io import BytesIO
import folium # Per la generazione di mappe interattive

# Importa i moduli personalizzati dalla directory src
from src.data_fetcher import NominatimFetcher
from src.distance_matrix import DistanceCalculator
from src.NN_ILS import TSPSolver # Algoritmo di risoluzione TSP

app = Flask(__name__)
# Rende 'enumerate' disponibile nei template Jinja2
app.jinja_env.globals['enumerate'] = enumerate
# Imposta una chiave segreta per la gestione della sessione e altri scopi di sicurezza
app.config['SECRET_KEY'] = uuid.uuid4().hex

# Assicura che la directory 'data' per la memorizzazione dei file di sessione e cache esista
if not os.path.exists('data'):
    os.makedirs('data')

def get_regions():
    """
    Recupera un dizionario delle regioni italiane.

    Returns:
        dict: Un dizionario che mappa i codici delle regioni (minuscoli, con trattini)
              ai loro nomi visualizzati (es. {"lombardia": "Lombardia"}).
    """
    fetcher = NominatimFetcher()
    return {key: value for key, value in fetcher.regions.items()}

@app.route('/')
def index():
    """
    Renderizza la pagina principale dell'applicazione.

    Questa pagina permette agli utenti di selezionare una regione italiana e impostare
    parametri come la popolazione minima delle città.
    """
    regions = get_regions()
    return render_template('index.html', regions=regions)

@app.route('/fetch_cities', methods=['POST'])
def fetch_cities():
    """
    Gestisce l'invio del form dalla pagina principale per recuperare le città di una regione selezionata.

    Recupera le città in base alla regione scelta, alla popolazione minima e all'opzione
    di aggiornare i dati da OpenStreetMap. I dati delle città recuperate vengono
    memorizzati in un file JSON specifico per la sessione.
    """
    region = request.form.get('region', 'basilicata') # Default a 'basilicata' se non fornito
    min_population = int(request.form.get('min_population', 1000)) # Default a 1000
    refresh_data = request.form.get('refresh_data') == 'on' # Verifica se è richiesto l'aggiornamento dei dati

    try:
        fetcher = NominatimFetcher(user_agent="ItalianRegionsTSP-Web/1.0") #
        cities_data = fetcher.fetch_cities(region, refresh=refresh_data, min_population=min_population) #

        if not cities_data:
            return render_template('error.html', error_message=f"Nessuna città trovata per la regione '{region}' con popolazione minima {min_population}.")

        session_id = str(uuid.uuid4()) # Genera un ID univoco per questa sessione
        session_data = {
            'region': region,
            'cities': cities_data,
            'min_population': min_population
        }

        # Memorizza i dati della sessione in un file JSON
        with open(f'data/session_{session_id}.json', 'w', encoding='utf-8') as f:
            json.dump(session_data, f)

        # Ordina le città per la visualizzazione: principalmente per popolazione (decrescente), poi per nome (crescente)
        cities_for_display = sorted(cities_data, key=lambda x: (-x.get('population', 0), x['name']))

        return render_template('select_city.html',
                              cities=cities_for_display,
                              region=region,
                              session_id=session_id,
                              city_count=len(cities_data))
    except Exception as e:
        # Registra l'eccezione qui se necessario, es. app.logger.error(f"Errore nel recupero città: {e}")
        return render_template('error.html', error_message=str(e))

@app.route('/solve_tsp', methods=['POST'])
def solve_tsp():
    """
    Gestisce la richiesta di risoluzione del TSP.

    Carica i dati delle città dal file di sessione, calcola la matrice delle distanze,
    esegue il risolutore TSP e quindi visualizza i risultati, inclusa una mappa interattiva.
    """
    session_id = request.form.get('session_id')
    start_city_name = request.form.get('start_city')
    max_iterations = int(request.form.get('max_iterations', 1000)) # Iterazioni ILS di default

    try:
        # Carica i dati della sessione
        with open(f'data/session_{session_id}.json', 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        cities = session_data['cities']
        region = session_data['region']

        # Trova l'indice della città di partenza
        start_city_index = 0
        for i, city_obj in enumerate(cities):
            if city_obj['name'] == start_city_name:
                start_city_index = i
                break

        start_time = time.time() # Avvia il cronometraggio del processo di risoluzione TSP

        # Calcola le distanze e risolve il TSP
        calculator = DistanceCalculator(cities) #
        distance_matrix = calculator.calculate_distance_matrix() #
        city_names = [city_obj['name'] for city_obj in cities]

        solver = TSPSolver(distance_matrix, city_names) #
        (optimal_path_indices, total_distance), solver_instance = solver.solve(
            start_city_index=start_city_index,
            max_iterations=max_iterations
        ), solver # Mantiene l'istanza del solver per accedere ai suoi metodi

        execution_time = time.time() - start_time # Calcola il tempo di esecuzione totale

        path_with_names = solver_instance.get_path_with_names() #
        path_details = solver_instance.get_path_details() #

        # --- Integrazione Mappa Folium ---
        # Centra la mappa sulla città di partenza
        map_center = [cities[start_city_index]['lat'], cities[start_city_index]['lon']]
        m = folium.Map(location=map_center, zoom_start=8)

        # Aggiunge marcatori per tutte le città
        for i, city_obj in enumerate(cities):
            popup_html = f"<b>{city_obj['name']}</b><br>Pop: {city_obj.get('population', 'N/A')}"
            folium.Marker(
                location=[city_obj['lat'], city_obj['lon']],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=city_obj['name'],
                # Città di partenza in rosso, le altre in blu
                icon=folium.Icon(color="red" if i == start_city_index else "blue", icon="info-sign")
            ).add_to(m)

        # Aggiunge PolyLine per il percorso TSP
        path_coordinates = []
        for city_idx in optimal_path_indices:
            city_obj = cities[city_idx]
            path_coordinates.append((city_obj['lat'], city_obj['lon']))
        folium.PolyLine(path_coordinates, color="green", weight=2.5, opacity=1).add_to(m)

        # Opzionale: Aggiunge marcatori numerati per la sequenza del percorso (può risultare affollato)
        for i, city_idx in enumerate(optimal_path_indices[:-1]): # Esclude il ritorno alla partenza per la numerazione
             city_obj = cities[city_idx]
             folium.Marker(
                 location=[city_obj['lat'], city_obj['lon']],
                 icon=folium.DivIcon( # HTML personalizzato per marcatori numerati
                    html=f"""<div style="font-family: sans-serif; color: black; background-color: rgba(255,255,255,0.7); border-radius: 50%; width: 20px; height: 20px; text-align: center; line-height: 20px; font-weight: bold;">{i+1}</div>"""
                 )
             ).add_to(m)

        map_html = m._repr_html_() # Ottiene la rappresentazione HTML della mappa Folium
        # --- Fine Integrazione Mappa Folium ---

        # Aggiorna i dati della sessione con i risultati
        session_data.update({
            'start_city': start_city_name,
            'optimal_path': optimal_path_indices,
            'total_distance': total_distance,
            'execution_time': execution_time,
            'path_with_names': path_with_names,
            'path_details': path_details,
        })

        with open(f'data/session_{session_id}.json', 'w', encoding='utf-8') as f:
            json.dump(session_data, f)

        formatted_time = format_time(execution_time) #

        return render_template('results.html',
                              region=region,
                              start_city=start_city_name,
                              city_count=len(optimal_path_indices) - 1, # Numero di città uniche visitate
                              total_distance=total_distance,
                              execution_time=formatted_time,
                              path_with_names=path_with_names,
                              path_details=path_details,
                              map_html=map_html, # Passa l'HTML della mappa al template
                              session_id=session_id)
    except Exception as e:
        # Registra l'eccezione qui se necessario
        # import traceback; traceback.print_exc() # Per debugging dettagliato
        return render_template('error.html', error_message=str(e))

@app.route('/download_results/<session_id>')
def download_results(session_id):
    """
    Permette all'utente di scaricare i risultati del TSP come file di testo.

    Args:
        session_id (str): L'identificatore univoco per la sessione dell'utente,
                          utilizzato per recuperare i risultati.
    """
    try:
        # Carica i dati della sessione
        with open(f'data/session_{session_id}.json', 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Prepara il contenuto per il file di testo
        results = []
        results.append(f"RISULTATO DEL TSP PER LE CITTÀ DELLA {session_data['region'].upper()}")
        results.append("=" * 50)
        results.append("Algoritmo utilizzato: Nearest Neighbor + Iterated Local Search")
        results.append(f"Città di partenza: {session_data['start_city']}")
        results.append(f"Numero di città visitate: {len(session_data['optimal_path']) - 1}")
        results.append(f"Distanza totale percorsa: {session_data['total_distance']:.2f} km")
        results.append(f"Tempo di esecuzione: {format_time(session_data['execution_time'])}") #
        results.append("\nPercorso ottimale:")
        results.append(" -> ".join(session_data['path_with_names']))
        results.append("\nDettagli del percorso:")

        for i, (from_city, to_city, distance) in enumerate(session_data['path_details'], 1):
            results.append(f"{i}. {from_city} -> {to_city}: {distance:.2f} km")

        content = "\n".join(results)

        # Crea un buffer BytesIO per contenere il contenuto testuale
        buffer = BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0) # Resetta la posizione del buffer all'inizio

        return send_file(buffer,
                       as_attachment=True, # Attiva il comportamento di download
                       download_name=f"tsp_{session_data['region']}_{session_data['start_city']}.txt",
                       mimetype="text/plain")
    except Exception as e:
        return render_template('error.html', error_message=str(e))

def format_time(seconds):
    """
    Formatta una durata in secondi in una stringa leggibile dall'utente.

    Args:
        seconds (float): La durata in secondi.

    Returns:
        str: Una stringa che rappresenta il tempo formattato (es. "2 minuti e 30.50 secondi").
    """
    if seconds < 60:
        return f"{seconds:.2f} secondi"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} minuti e {secs:.2f} secondi"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours} ore, {minutes} minuti e {secs:.2f} secondi"

if __name__ == '__main__':
    # Esegue il server di sviluppo Flask
    # La modalità Debug dovrebbe essere False in un ambiente di produzione
    app.run(debug=True)