import time
import random
import numpy as np # Usato implicitamente per la matrice delle distanze

class TSPSolver:
    """
    Risolve il Problema del Commesso Viaggiatore (TSP) utilizzando una combinazione
    dell'algoritmo Nearest Neighbor (NN) per una soluzione iniziale e
    Iterated Local Search (ILS) per l'ottimizzazione.
    """

    def __init__(self, distance_matrix, city_names):
        """
        Inizializza il risolutore TSP.

        Args:
            distance_matrix (numpy.ndarray): Matrice N x N delle distanze tra le città.
            city_names (list): Lista dei nomi delle città, corrispondente agli indici
                               della matrice delle distanze.
        """
        self.distance_matrix = distance_matrix
        self.city_names = city_names
        self.n_cities = len(city_names)
        if self.n_cities == 0:
            raise ValueError("La lista delle città non può essere vuota.")
        if self.n_cities == 1 and self.distance_matrix.shape != (1,1): # Gestione caso limite città singola
             raise ValueError("Matrice distanze non compatibile con una singola città.")
        elif self.n_cities > 1 and self.distance_matrix.shape != (self.n_cities, self.n_cities):
            raise ValueError("Dimensioni della matrice delle distanze non coerenti con il numero di città.")

        self.best_path_indices = None # Memorizza gli indici delle città nel percorso migliore
        self.best_distance = float('inf') # Memorizza la distanza del percorso migliore

    def solve(self, start_city_index=0, max_iterations=1000):
        """
        Risolve il TSP partendo da una città specifica.

        Args:
            start_city_index (int, optional): Indice della città di partenza. Default a 0.
            max_iterations (int, optional): Numero massimo di iterazioni per l'ILS. Default a 1000.

        Returns:
            tuple: Una tupla contenente:
                - list: Il percorso ottimale (lista di indici di città).
                - float: La distanza totale del percorso ottimale.
        """
        if not (0 <= start_city_index < self.n_cities):
            raise ValueError(f"Indice della città di partenza '{start_city_index}' non valido per {self.n_cities} città.")

        # Caso speciale: se c'è solo una città, il percorso è banale
        if self.n_cities == 1:
            self.best_path_indices = [start_city_index, start_city_index] # Ritorna a se stessa
            self.best_distance = 0.0
            print(f"Risoluzione TSP per una singola città: {self.city_names[start_city_index]}. Distanza: 0.0 km.")
            return self.best_path_indices, self.best_distance

        start_time_solve = time.time()
        print(f"Avvio risoluzione TSP da '{self.city_names[start_city_index]}' con {self.n_cities} città...")

        # Fase 1: Costruzione della soluzione iniziale con Nearest Neighbor
        print("Fase 1: Costruzione del percorso iniziale con Nearest Neighbor...")
        initial_path = self._nearest_neighbor(start_city_index)
        initial_distance = self._calculate_path_length(initial_path)
        print(f"Distanza del percorso iniziale (NN): {initial_distance:.2f} km")

        self.best_path_indices = initial_path
        self.best_distance = initial_distance

        # Fase 2: Ottimizzazione con Iterated Local Search (ILS)
        # ILS è utile se ci sono almeno 3 città per permettere mosse come 2-opt.
        # Per 2 città, NN è già ottimale (A->B->A).
        if self.n_cities > 2 :
            print(f"Fase 2: Ottimizzazione con Iterated Local Search (max {max_iterations} iterazioni)...")
            optimized_path, optimized_distance = self._iterated_local_search(
                initial_path, initial_distance, max_iterations=max_iterations
            )
            self.best_path_indices = optimized_path
            self.best_distance = optimized_distance
        else:
            print("Fase 2: Ottimizzazione ILS saltata (meno di 3 città).")


        elapsed_time = time.time() - start_time_solve
        improvement = initial_distance - self.best_distance
        improvement_percent = (improvement / initial_distance * 100) if initial_distance > 0 else 0

        print(f"Risoluzione TSP completata in {elapsed_time:.2f} secondi.")
        if self.n_cities > 2:
             print(f"Miglioramento rispetto a NN: {improvement:.2f} km ({improvement_percent:.2f}%)")
        print(f"Distanza ottimale finale: {self.best_distance:.2f} km")

        return self.best_path_indices, self.best_distance

    def _nearest_neighbor(self, start_node_idx):
        """
        Implementa l'algoritmo Nearest Neighbor per trovare un percorso TSP iniziale.

        Args:
            start_node_idx (int): L'indice del nodo (città) da cui iniziare.

        Returns:
            list: Un percorso (lista di indici di città) che inizia e finisce
                  al nodo di partenza, visitando ogni altra città una volta.
        """
        unvisited_nodes = set(range(self.n_cities))
        current_node = start_node_idx
        path = [current_node]
        unvisited_nodes.remove(current_node)

        while unvisited_nodes:
            # Trova il nodo non visitato più vicino al nodo corrente
            next_node = min(unvisited_nodes, key=lambda node: self.distance_matrix[current_node][node])
            path.append(next_node)
            unvisited_nodes.remove(next_node)
            current_node = next_node

        # Completa il ciclo tornando al nodo di partenza
        path.append(start_node_idx)
        return path

    def _iterated_local_search(self, initial_tour_indices, initial_distance, max_iterations):
        """
        Implementa l'algoritmo Iterated Local Search (ILS) per ottimizzare un percorso TSP.

        Args:
            initial_tour_indices (list): Il percorso iniziale (lista di indici di città),
                                         che include il ritorno alla partenza.
            initial_distance (float): La distanza del percorso iniziale.
            max_iterations (int): Numero massimo di iterazioni dell'ILS.

        Returns:
            tuple: Una tupla contenente (percorso_migliore_finale, distanza_migliore_finale).
        """
        current_tour = initial_tour_indices[:-1] # Lavora con il percorso senza il ritorno finale duplicato
        current_dist = initial_distance

        best_overall_tour = initial_tour_indices # Memorizza il percorso completo (con ritorno)
        best_overall_dist = initial_distance

        iterations_without_global_improvement = 0
        MAX_STAGNATION = 200 # Numero di iterazioni senza miglioramento globale prima di fermarsi

        for i in range(max_iterations):
            # Ricerca Locale (es. 2-opt)
            improved_in_local_search, new_tour_segment, new_dist_segment = self._local_search_2opt(current_tour, current_dist)

            if new_dist_segment < current_dist:
                current_tour = new_tour_segment
                current_dist = new_dist_segment

                if current_dist < best_overall_dist:
                    best_overall_dist = current_dist
                    best_overall_tour = current_tour + [current_tour[0]] # Aggiunge ritorno per coerenza
                    iterations_without_global_improvement = 0
                    print(f"Iterazione ILS {i+1}: Nuovo miglior percorso globale trovato, distanza: {best_overall_dist:.2f} km")
                else:
                    iterations_without_global_improvement += 1
            else:
                iterations_without_global_improvement += 1

            # Perturbazione se la ricerca locale non migliora o per esplorare
            # Applica la perturbazione se non c'è stato miglioramento o periodicamente
            if not improved_in_local_search or (i % 50 == 0 and i > 0) : #  Condizione di perturbazione
                if iterations_without_global_improvement > 20 : # Perturba se stagnante
                    # print(f"Iterazione ILS {i+1}: Perturbazione del percorso...")
                    current_tour = self._perturb_tour_double_bridge(current_tour)
                    current_dist = self._calculate_path_length(current_tour + [current_tour[0]])


            if iterations_without_global_improvement >= MAX_STAGNATION:
                print(f"Iterazione ILS {i+1}: Arresto anticipato per stagnazione dopo {MAX_STAGNATION} iterazioni senza miglioramento globale.")
                break
        
        if not best_overall_tour: # Assicura che ci sia sempre un percorso di ritorno
             return initial_tour_indices, initial_distance
        return best_overall_tour, best_overall_dist


    def _local_search_2opt(self, tour_indices, current_distance):
        """
        Esegue una ricerca locale utilizzando la mossa 2-opt per migliorare il percorso.
        Il percorso in input (`tour_indices`) non include il ritorno alla città di partenza.

        Args:
            tour_indices (list): Il percorso attuale (lista di indici di città, senza ritorno alla partenza).
            current_distance (float): La distanza del percorso attuale (calcolata includendo il ritorno).

        Returns:
            tuple: (migliorato_bool, percorso_risultante, distanza_risultante)
                   Il percorso e la distanza risultanti sono relativi al percorso che include il ritorno.
        """
        n = len(tour_indices)
        best_tour_segment = list(tour_indices) # Copia del segmento di percorso (senza ritorno)
        best_segment_distance = current_distance # Distanza completa del tour (con ritorno)
        improved = False

        for i in range(n - 1): # da 0 a n-2
            for j in range(i + 2, n): # da i+2 a n-1
                # Escludere il caso in cui j sia l'ultimo nodo e i sia il primo,
                # che chiuderebbe il cerchio in modo non standard per 2-opt su un segmento.
                if i == 0 and j == n - 1: continue

                # Costruisci il nuovo segmento invertendo la parte tra tour_indices[i+1] e tour_indices[j]
                new_segment = list(tour_indices) # Crea una copia per la modifica
                segment_to_reverse = new_segment[i+1 : j+1]
                segment_to_reverse.reverse()
                new_segment[i+1 : j+1] = segment_to_reverse

                # Calcola la distanza del nuovo tour completo (aggiungendo il ritorno alla partenza)
                new_total_distance = self._calculate_path_length(new_segment + [new_segment[0]])

                if new_total_distance < best_segment_distance:
                    best_segment_distance = new_total_distance
                    best_tour_segment = new_segment
                    improved = True
                    # In una strategia "first improvement", si potrebbe uscire qui.
                    # Qui adottiamo una strategia "best improvement" all'interno di questa chiamata 2-opt.

        return improved, best_tour_segment, best_segment_distance


    def _perturb_tour_double_bridge(self, tour_indices):
        """
        Applica una perturbazione "double-bridge" (una mossa 4-opt) al percorso.
        Questa mossa aiuta ad uscire dai minimi locali.
        Il percorso in input (`tour_indices`) non include il ritorno alla città di partenza.

        Args:
            tour_indices (list): Il percorso attuale (lista di indici di città, senza ritorno).

        Returns:
            list: Il nuovo percorso perturbato (lista di indici di città, senza ritorno).
        """
        n = len(tour_indices)
        if n < 4: # La mossa double-bridge richiede almeno 4 città nel segmento
            return list(tour_indices)

        # Scegli 4 punti di taglio casuali, distinti e ordinati
        # i < j < k < l
        # Gli archi da rompere sono (p_i, p_{i+1}), (p_j, p_{j+1}), (p_k, p_{k+1}), (p_l, p_{l+1})
        # In questo caso, consideriamo indici di *nodi* per suddividere il percorso.
        # Seleziona 4 indici casuali per i nodi che definiranno i segmenti.
        # Assicurati che gli indici siano distinti e che ci sia spazio tra loro.
        idx = sorted(random.sample(range(n), 4))

        i, j, k, l = idx[0], idx[1], idx[2], idx[3]

        # Ricostruisci il percorso scambiando i segmenti intermedi
        # Segmento 1: da inizio a tour_indices[i]
        # Segmento 2: da tour_indices[i+1] a tour_indices[j]
        # Segmento 3: da tour_indices[j+1] a tour_indices[k]
        # Segmento 4: da tour_indices[k+1] a tour_indices[l]
        # Segmento 5: da tour_indices[l+1] a fine
        # La mossa double-bridge standard ricombina come: seg1 -> seg4 -> seg3 -> seg2 -> seg5 (adattato)
        # A B C D -> A D C B (2-opt)
        # tour = P_0 ... P_i | P_{i+1} ... P_j | P_{j+1} ... P_k | P_{k+1} ... P_l | P_{l+1} ... P_{n-1}
        # new_tour = P_0 ... P_i + P_{k+1} ... P_l + P_{j+1} ... P_k + P_{i+1} ... P_j + P_{l+1} ... P_{n-1}

        s1 = tour_indices[0 : i+1]
        s2 = tour_indices[i+1 : j+1]
        s3 = tour_indices[j+1 : k+1]
        s4 = tour_indices[k+1 : l+1]
        s5 = tour_indices[l+1 : n]
        
        # Una possibile ricombinazione double-bridge:
        perturbed_tour = s1 + s4 + s3 + s2 + s5
        
        # Verifica la validità del percorso perturbato (lunghezza e unicità dei nodi)
        if len(perturbed_tour) == n and len(set(perturbed_tour)) == n:
            return perturbed_tour
        else: # Se la perturbazione fallisce (raro con indici corretti), ritorna l'originale
            return list(tour_indices)


    def _calculate_path_length(self, path_indices):
        """
        Calcola la lunghezza totale di un dato percorso.

        Args:
            path_indices (list): Una lista di indici di città che rappresenta il percorso.
                                 Deve includere il ritorno al nodo di partenza se si
                                 vuole la lunghezza totale del tour.

        Returns:
            float: La lunghezza totale del percorso.
        """
        total_distance = 0.0
        if not path_indices or len(path_indices) < 2:
            return 0.0 # Nessuna distanza se il percorso è vuoto o ha un solo nodo

        for i in range(len(path_indices) - 1):
            from_node = path_indices[i]
            to_node = path_indices[i+1]
            total_distance += self.distance_matrix[from_node][to_node]
        return total_distance

    def get_path_with_names(self):
        """
        Restituisce il miglior percorso trovato, utilizzando i nomi delle città.

        Returns:
            list: Una lista di nomi di città che rappresenta il percorso ottimale,
                  o una lista vuota se `solve()` non è stato ancora chiamato
                  o se non è stato trovato nessun percorso.
        """
        if self.best_path_indices is None:
            return []
        return [self.city_names[idx] for idx in self.best_path_indices]

    def get_path_details(self):
        """
        Restituisce i dettagli di ogni segmento del miglior percorso trovato.

        Returns:
            list: Una lista di tuple, dove ogni tupla contiene:
                  (nome_citta_partenza_segmento, nome_citta_arrivo_segmento, distanza_segmento).
                  Restituisce una lista vuota se nessun percorso è stato trovato.
        """
        if self.best_path_indices is None or len(self.best_path_indices) < 2:
            return []

        details = []
        for i in range(len(self.best_path_indices) - 1):
            from_idx = self.best_path_indices[i]
            to_idx = self.best_path_indices[i+1]
            distance = self.distance_matrix[from_idx][to_idx]
            details.append((
                self.city_names[from_idx],
                self.city_names[to_idx],
                distance
            ))
        return details