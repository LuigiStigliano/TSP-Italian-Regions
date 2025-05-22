import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import argparse # Usato per ottenere opzionalmente il nome della regione
import os

class TSPVisualizer:
    """
    Visualizza il percorso TSP trovato su una mappa statica utilizzando Matplotlib e NetworkX.

    Questa classe si occupa di creare un grafo delle città, disegnare i nodi
    (con dimensioni proporzionali alla popolazione), tracciare il percorso TSP
    e opzionalmente salvare l'immagine o mostrarla a schermo.
    """

    def __init__(self, cities, path_indices=None):
        """
        Inizializza il visualizzatore.

        Args:
            cities (list): Lista di dizionari città. Ogni città deve avere
                           'name', 'lat', 'lon' e opzionalmente 'population'.
            path_indices (list, optional): Lista di indici di città che rappresenta il percorso TSP.
                                     Default a None.
        """
        self.cities = cities
        self.path_indices = path_indices # Lista di indici del percorso
        self.fig = None # Figura Matplotlib
        self.ax = None  # Assi Matplotlib
        self.region_name = self._get_region_name_from_args() # Nome della regione per il titolo

    def _get_region_name_from_args(self):
        """
        Tenta di ottenere il nome della regione dagli argomenti della riga di comando.
        Questo è un metodo di supporto per avere un titolo di default sensato se
        l'informazione della regione non è passata esplicitamente.

        Returns:
            str: Il nome della regione o un valore di default.
        """
        # Questo è un modo per rendere il visualizzatore leggermente più consapevole
        # del contesto CLI senza accoppiarlo strettamente.
        # In un'applicazione web, questo nome verrebbe passato diversamente.
        parser = argparse.ArgumentParser(add_help=False) # add_help=False per evitare conflitti se usato altrove
        parser.add_argument('--region', type=str, default="N/A") # Default se non specificato
        # parse_known_args ignora argomenti non riconosciuti, utile se TSPVisualizer è parte di uno script più grande
        args, _ = parser.parse_known_args()
        return args.region

    def _create_graph_from_cities(self):
        """
        Crea un grafo NetworkX a partire dalla lista delle città.
        I nodi rappresentano le città e gli archi (se `path_indices` è fornito)
        rappresentano i segmenti del percorso TSP.

        Returns:
            networkx.Graph: Il grafo creato.
        """
        G = nx.Graph() # Grafo non orientato

        # Aggiunge le città come nodi del grafo
        for i, city_data in enumerate(self.cities):
            G.add_node(i, # L'ID del nodo è l'indice della città nella lista originale
                       pos=(city_data['lon'], city_data['lat']), # Posizione per il plotting (longitudine, latitudine)
                       name=city_data['name'],
                       population=city_data.get('population', 0)) # Popolazione, default a 0 se non presente

        # Se un percorso è stato fornito, aggiunge gli archi che lo rappresentano
        if self.path_indices and len(self.path_indices) > 1:
            for i in range(len(self.path_indices) - 1):
                u_node = self.path_indices[i]
                v_node = self.path_indices[i+1]
                G.add_edge(u_node, v_node)
        return G

    def _get_map_boundaries(self, node_positions):
        """
        Determina i limiti geografici (latitudine e longitudine min/max)
        per la visualizzazione della mappa, basati sulle posizioni dei nodi.

        Args:
            node_positions (dict): Dizionario {node_id: (lon, lat)} delle posizioni dei nodi.

        Returns:
            dict: Un dizionario con 'min_lon', 'max_lon', 'min_lat', 'max_lat'.
        """
        if not node_positions:
            # Valori di default se non ci sono nodi (caso improbabile ma gestito)
            return {'min_lon': -10, 'max_lon': 10, 'min_lat': 35, 'max_lat': 50}

        longitudes = [pos[0] for pos in node_positions.values()]
        latitudes = [pos[1] for pos in node_positions.values()]

        # Aggiunge un margine per evitare che i nodi siano esattamente sui bordi
        margin_lon = (max(longitudes) - min(longitudes)) * 0.10 # Margine del 10% della larghezza
        margin_lat = (max(latitudes) - min(latitudes)) * 0.10 # Margine del 10% dell'altezza
        
        # Se i margini sono zero (es. una sola città), imposta un margine fisso
        if margin_lon == 0: margin_lon = 0.1
        if margin_lat == 0: margin_lat = 0.1


        return {
            'min_lon': min(longitudes) - margin_lon,
            'max_lon': max(longitudes) + margin_lon,
            'min_lat': min(latitudes) - margin_lat,
            'max_lat': max(latitudes) + margin_lat
        }

    def _draw_city_nodes(self, graph, positions, ax):
        """
        Disegna i nodi (città) sul grafo.
        La dimensione di ogni nodo è proporzionale alla sua popolazione.

        Args:
            graph (networkx.Graph): Il grafo contenente i nodi.
            positions (dict): Dizionario delle posizioni dei nodi.
            ax (matplotlib.axes.Axes): Gli assi su cui disegnare.

        Returns:
            tuple: (popolazione_minima_usata, popolazione_massima_usata) per la legenda.
        """
        populations = np.array([graph.nodes[node_id].get('population', 1000) for node_id in graph.nodes()])
        # Evita divisione per zero se tutte le popolazioni sono uguali o se c'è solo una città
        min_pop = populations.min()
        max_pop = populations.max()

        if max_pop == min_pop: # Se tutte le popolazioni sono uguali (o c'è una sola città)
            node_sizes_scaled = [100] * len(populations) # Usa una dimensione fissa
        else:
            # Normalizza le dimensioni dei nodi in un range visibile (es. da 50 a 1500)
            node_sizes_scaled = 50 + 1450 * (populations - min_pop) / (max_pop - min_pop)

        nx.draw_networkx_nodes(graph, positions, ax=ax,
                               node_size=node_sizes_scaled,
                               node_color='skyblue',
                               edgecolors='black', # Bordo dei nodi
                               alpha=0.8)

        # Disegna le etichette (nomi delle città)
        node_labels = {node_id: graph.nodes[node_id]['name'] for node_id in graph.nodes}
        nx.draw_networkx_labels(graph, positions, ax=ax,
                                labels=node_labels,
                                font_size=8, # Dimensione font ridotta per leggibilità
                                font_weight='bold')
        return min_pop, max_pop

    def _draw_tsp_path(self, graph, positions, ax):
        """
        Disegna gli archi che rappresentano il percorso TSP, se fornito.
        Gli archi possono essere colorati o numerati per indicare la sequenza.

        Args:
            graph (networkx.Graph): Il grafo (dovrebbe contenere gli archi del percorso).
            positions (dict): Dizionario delle posizioni dei nodi.
            ax (matplotlib.axes.Axes): Gli assi su cui disegnare.
        """
        if not self.path_indices or len(self.path_indices) < 2:
            return # Niente da disegnare se non c'è percorso

        # Estrae gli archi dal percorso per disegnarli
        path_edges = []
        for i in range(len(self.path_indices) - 1):
            path_edges.append((self.path_indices[i], self.path_indices[i+1]))

        nx.draw_networkx_edges(graph, positions, ax=ax,
                               edgelist=path_edges, # Disegna solo gli archi del percorso
                               width=2.0,          # Spessore degli archi
                               edge_color='green', # Colore degli archi del percorso
                               arrows=True,        # Aggiunge frecce per indicare la direzione
                               arrowstyle='-|>',
                               arrowsize=15)

        # Opzionale: etichette per numerare i segmenti del percorso
        edge_labels_dict = {}
        for i, edge in enumerate(path_edges):
            edge_labels_dict[edge] = str(i + 1) # Numero progressivo del segmento

        nx.draw_networkx_edge_labels(graph, positions, ax=ax,
                                     edge_labels=edge_labels_dict,
                                     font_size=7,
                                     font_color='darkgreen')

    def _add_map_legend(self, min_pop, max_pop, ax):
        """
        Aggiunge una legenda alla mappa per indicare la scala delle dimensioni dei nodi
        in base alla popolazione.

        Args:
            min_pop (float): Popolazione minima usata per la scala dei nodi.
            max_pop (float): Popolazione massima usata per la scala dei nodi.
            ax (matplotlib.axes.Axes): Gli assi su cui aggiungere la legenda.
        """
        # Crea degli handle fittizi per la legenda (scatter plot vuoti)
        # Le dimensioni 's' qui sono indicative per la legenda.
        legend_handles = [
            plt.scatter([], [], s=50, label=f'Pop. Min: ~{min_pop:,.0f}', color='skyblue', edgecolors='black'),
            plt.scatter([], [], s=200, label='Pop. Media', color='skyblue', edgecolors='black'),
            plt.scatter([], [], s=500, label=f'Pop. Max: ~{max_pop:,.0f}', color='skyblue', edgecolors='black')
        ]
        ax.legend(handles=legend_handles, title='Dimensione Città (Popolazione)', loc='best', fontsize='small')


    def plot_path(self, title=None, save_path=None, figsize=(14, 10)): # Aumentata dimensione figura
        """
        Crea e visualizza (o salva) la mappa del percorso TSP.

        Args:
            title (str, optional): Titolo per il grafico. Se None, ne viene generato uno di default.
            save_path (str, optional): Percorso del file dove salvare l'immagine (es. "mappa.png").
                                       Se None, l'immagine non viene salvata.
            figsize (tuple, optional): Dimensioni della figura Matplotlib.

        Returns:
            tuple: (matplotlib.figure.Figure, matplotlib.axes.Axes) La figura e gli assi creati.
        """
        if title is None:
            title = f"Percorso TSP - Regione: {self.region_name.title()}"
            if self.path_indices and self.cities:
                 title += f" ({len(self.path_indices)-1} città)"


        graph = self._create_graph_from_cities()
        node_positions = nx.get_node_attributes(graph, 'pos') # {node_id: (lon, lat)}

        self.fig, self.ax = plt.subplots(figsize=figsize)

        map_bounds = self._get_map_boundaries(node_positions)
        self.ax.set_xlim(map_bounds['min_lon'], map_bounds['max_lon'])
        self.ax.set_ylim(map_bounds['min_lat'], map_bounds['max_lat'])

        # Disegna i nodi (città)
        min_pop, max_pop = self._draw_city_nodes(graph, node_positions, self.ax)

        # Disegna il percorso TSP
        self._draw_tsp_path(graph, node_positions, self.ax)

        # Aggiunge la legenda per la dimensione dei nodi
        if min_pop is not None and max_pop is not None : # Solo se ci sono dati di popolazione
             self._add_map_legend(min_pop, max_pop, self.ax)

        self.ax.set_title(title, fontsize=16)
        self.ax.set_xlabel("Longitudine", fontsize=12)
        self.ax.set_ylabel("Latitudine", fontsize=12)
        self.ax.grid(True, linestyle='--', alpha=0.6) # Griglia per migliore leggibilità

        # Aggiunge informazioni testuali sul percorso in fondo alla figura
        if self.path_indices and len(self.path_indices) > 1 and self.cities:
            start_city_name_info = self.cities[self.path_indices[0]]['name']
            num_visited_cities = len(self.path_indices) - 1
            # (Opzionale) Calcola la distanza totale se necessario per il testo qui,
            # ma generalmente questa informazione proviene dal solver.
            # total_distance_info = ...
            fig_text = f"Partenza: {start_city_name_info}. Città visitate: {num_visited_cities}."
            self.fig.text(0.5, 0.01, fig_text, ha='center', fontsize=10, style='italic')


        plt.tight_layout(rect=[0, 0.03, 1, 0.97]) # Aggiusta layout per fare spazio al titolo e figtext

        if save_path:
            try:
                # Assicura che la directory esista
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Visualizzazione salvata in: {save_path}")
            except Exception as e:
                print(f"Errore durante il salvataggio della visualizzazione in '{save_path}': {e}")

        return self.fig, self.ax

    def show(self):
        """Mostra la visualizzazione a schermo."""
        if self.fig:
            plt.show()
        else:
            print("Nessuna figura da mostrare. Chiamare prima plot_path().")

    def create_interactive_html_visualization(self, output_file=None): # Rinominata per chiarezza
        """
        Crea una visualizzazione HTML statica contenente l'immagine del percorso TSP.
        Questo è un metodo legacy se non si usa Folium.
        NOTA: Il progetto principale ora usa Folium per le mappe interattive nell'app web.
              Questa funzione genera un PNG e lo embedda in HTML.

        Args:
            output_file (str, optional): Nome del file HTML di output.
                                         Se None, ne viene generato uno di default.
        """
        if output_file is None:
            output_file = f"tsp_visualization_{self.region_name.lower().replace(' ', '_')}.html"

        # Definisce il nome del file immagine basato sul nome del file HTML
        image_file_name = os.path.splitext(output_file)[0] + ".png"
        # Crea un percorso completo per l'immagine, ad esempio in una sottocartella 'static'
        # Questo dipende da dove si vuole che l'HTML cerchi l'immagine.
        # Per semplicità, assumiamo che l'immagine sia nella stessa directory dell'HTML o un percorso relativo.
        image_path_for_html = os.path.basename(image_file_name) # Riferimento relativo per l'HTML

        # Genera e salva l'immagine PNG
        self.plot_path(save_path=image_file_name) # Salva l'immagine

        region_title_display = self.region_name.title()
        html_content = f"""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <title>Visualizzazione TSP - {region_title_display}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; text-align: center; }}
                img {{ max-width: 100%; height: auto; border: 1px solid #ccc; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <h1>Visualizzazione del Percorso TSP per la Regione: {region_title_display}</h1>
            <img src="{image_path_for_html}" alt="Mappa del Percorso TSP">
            <p>Questa mappa mostra il percorso ottimale calcolato tra le città selezionate.</p>
        </body>
        </html>
        """

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Visualizzazione HTML salvata in: {output_file}")
            print(f"Assicurarsi che l'immagine '{image_path_for_html}' sia accessibile dall'HTML.")
        except Exception as e:
            print(f"Errore durante il salvataggio della visualizzazione HTML '{output_file}': {e}")