import os
import json
import requests

class NominatimFetcher:
    """
    Recupera dati geografici relativi alle città italiane utilizzando l'API Nominatim
    di OpenStreetMap e l'API Overpass.

    Questa classe gestisce il recupero delle città per una data regione italiana,
    filtrandole opzionalmente per popolazione minima e utilizzando un sistema
    di cache per ridurre il numero di richieste alle API esterne.
    """
    def __init__(self, user_agent="ItalianRegionsTSP/1.0"):
        """
        Inizializza il fetcher con un User-Agent specifico.

        Args:
            user_agent (str): Lo User-Agent da utilizzare per le richieste HTTP.
                              È importante per rispettare le policy di OSM.
        """
        self.user_agent = user_agent
        self.base_url = "https://nominatim.openstreetmap.org/search" # URL base per Nominatim (non usato direttamente per le città qui)

        # Mappatura dei codici regione ai nomi completi delle regioni italiane
        self.regions = {
            "abruzzo": "Abruzzo",
            "basilicata": "Basilicata",
            "calabria": "Calabria",
            "campania": "Campania",
            "emilia-romagna": "Emilia-Romagna",
            "friuli-venezia-giulia": "Friuli-Venezia Giulia",
            "lazio": "Lazio",
            "liguria": "Liguria",
            "lombardia": "Lombardia",
            "marche": "Marche",
            "molise": "Molise",
            "piemonte": "Piemonte",
            "puglia": "Puglia",
            "sardegna": "Sardegna",
            "sicilia": "Sicilia",
            "toscana": "Toscana",
            "trentino-alto-adige": "Trentino-Alto Adige/Südtirol",
            "umbria": "Umbria",
            "valle-d-aosta": "Valle d'Aosta/Vallée d'Aoste",
            "veneto": "Veneto"
        }

    def fetch_cities(self, region: str, refresh=False, min_population=0):
        """
        Recupera le città di una regione specifica, utilizzando la cache se disponibile.

        Args:
            region (str): Il codice della regione italiana (es. "lombardia").
            refresh (bool, optional): Se True, forza il recupero dei dati dall'API
                                      ignorando la cache. Default a False.
            min_population (int, optional): La popolazione minima che una città deve avere
                                            per essere inclusa nei risultati. Default a 0.

        Returns:
            list: Una lista di dizionari, ognuno rappresentante una città con
                  nome, latitudine, longitudine e popolazione.

        Raises:
            ValueError: Se il codice della regione fornito non è valido.
            requests.exceptions.RequestException: Se si verifica un errore durante
                                                  la richiesta all'API Overpass.
        """
        region_code = region.lower()
        if region_code not in self.regions:
            raise ValueError(f"Regione non valida. Regioni disponibili: {', '.join(self.regions.keys())}")

        region_name_display = self.regions[region_code]
        # Definisce il percorso del file di cache per la regione specificata
        data_file = f"data/{region_code}_cities.json"

        # Utilizza i dati dalla cache se il file esiste e non è richiesto un aggiornamento
        if not refresh and os.path.exists(data_file):
            print(f"Caricamento città per '{region_name_display}' dalla cache...")
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        print(f"Recupero delle città per la regione '{region_name_display}' da Overpass API (pop. min: {min_population})...")
        cities = self._fetch_from_overpass(region_name_display, min_population)

        # Salva i dati recuperati nella cache per usi futuri
        if cities: # Salva solo se sono state trovate città
            self._save_to_cache(data_file, cities)
            print(f"Trovate e salvate in cache {len(cities)} città per la regione '{region_name_display}'.")
        else:
            print(f"Nessuna città trovata per la regione '{region_name_display}' con popolazione minima {min_population}.")


        return cities

    def _fetch_from_overpass(self, region_name, min_population):
        """
        Esegue la query effettiva all'API Overpass per recuperare i dati delle città.

        Args:
            region_name (str): Il nome completo della regione italiana (es. "Lombardia").
            min_population (int): La popolazione minima per filtrare le città.

        Returns:
            list: Una lista di dizionari città.
        """
        overpass_url = "https://overpass-api.de/api/interpreter"
        # Query Overpass per trovare nodi (città, paesi, villaggi) all'interno dell'area amministrativa della regione
        query = f"""
        [out:json][timeout:30];
        area["name"="{region_name}"]["boundary"="administrative"]["admin_level"="4"]->.reg;
        (
          node["place"~"city|town|village"](area.reg);
        );
        out body;
        """
        # Nota: la query Overpass non supporta direttamente il filtraggio per 'population' nel server-side in questo modo.
        # Il filtraggio per popolazione viene fatto client-side dopo aver ricevuto i dati.

        response = requests.post(overpass_url, data={"data": query},
                               headers={"User-Agent": self.user_agent})
        response.raise_for_status() # Solleva un'eccezione per errori HTTP (4xx o 5xx)
        data = response.json()

        cities_found = []
        seen_city_names = set() # Per evitare duplicati basati sul nome

        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            # Converte la popolazione in float, gestendo l'assenza del tag o valori non numerici
            try:
                population_str = tags.get("population", "0")
                population = float(population_str) if population_str else 0.0
            except ValueError:
                population = 0.0 # Default a 0 se la conversione fallisce

            if name and (name not in seen_city_names) and population >= min_population:
                seen_city_names.add(name)
                cities_found.append({
                    "name": name,
                    "lat": float(element["lat"]),
                    "lon": float(element["lon"]),
                    "population": population
                })

        return cities_found

    def _save_to_cache(self, data_file_path, cities_data):
        """
        Salva i dati delle città in un file JSON di cache.

        Args:
            data_file_path (str): Il percorso completo del file di cache.
            cities_data (list): La lista di dizionari città da salvare.
        """
        # Assicura che la directory 'data' esista
        os.makedirs(os.path.dirname(data_file_path), exist_ok=True)

        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(cities_data, f, indent=2, ensure_ascii=False)