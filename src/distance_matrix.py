import numpy as np
from math import radians, sin, cos, sqrt, atan2

class DistanceCalculator:
    """
    Calcola la matrice delle distanze tra un insieme di città utilizzando
    la formula di Haversine per determinare la distanza geodetica
    (in linea d'aria) tra coordinate geografiche.
    """

    def __init__(self, cities):
        """
        Inizializza il calcolatore con una lista di città.

        Args:
            cities (list): Una lista di dizionari, dove ogni dizionario
                           rappresenta una città e deve contenere almeno
                           le chiavi 'name', 'lat' (latitudine) e 'lon' (longitudine).
        """
        self.cities = cities
        self.city_names = [city['name'] for city in cities]
        self.n_cities = len(cities)

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calcola la distanza in linea d'aria tra due punti geografici
        specificati da latitudine e longitudine, utilizzando la formula di Haversine.

        Args:
            lat1 (float): Latitudine del primo punto in gradi.
            lon1 (float): Longitudine del primo punto in gradi.
            lat2 (float): Latitudine del secondo punto in gradi.
            lon2 (float): Longitudine del secondo punto in gradi.

        Returns:
            float: La distanza tra i due punti in chilometri.
        """
        # Raggio medio della Terra in chilometri
        R = 6371.0

        # Converte le coordinate da gradi decimali a radianti
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)

        # Differenze di latitudine e longitudine
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Formula di Haversine
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c  # Distanza in chilometri
        return distance

    def calculate_distance_matrix(self):
        """
        Calcola e restituisce una matrice N x N delle distanze tra tutte le coppie di città,
        dove N è il numero di città.

        La matrice è simmetrica (distanza[i, j] == distanza[j, i]) e la diagonale
        principale è zero (distanza[i, i] == 0).

        Returns:
            numpy.ndarray: Una matrice NumPy 2D contenente le distanze
                           tra ogni coppia di città in chilometri.
        """
        # Inizializza una matrice N x N con zeri
        distance_matrix = np.zeros((self.n_cities, self.n_cities))

        # Popola la matrice calcolando la distanza tra ogni coppia di città
        for i in range(self.n_cities):
            for j in range(i + 1, self.n_cities): # Calcola solo per la parte superiore della matrice
                city1 = self.cities[i]
                city2 = self.cities[j]

                dist = self._haversine_distance(
                    city1['lat'], city1['lon'],
                    city2['lat'], city2['lon']
                )

                # La matrice è simmetrica
                distance_matrix[i, j] = dist
                distance_matrix[j, i] = dist

        return distance_matrix

    def get_closest_cities(self, city_index, n=5):
        """
        Trova le 'n' città più vicine a una data città, basandosi sulla matrice delle distanze.
        Questo metodo è più un esempio d'uso e non è direttamente utilizzato nel flusso principale del TSP solver.

        Args:
            city_index (int): L'indice della città di riferimento nella lista `self.cities`.
            n (int, optional): Il numero di città più vicine da restituire. Default a 5.

        Returns:
            list: Una lista di tuple, dove ogni tupla contiene:
                  (indice_citta_vicina, nome_citta_vicina, distanza_dalla_citta_riferimento).
                  La lista è ordinata per distanza crescente.
        """
        if not (0 <= city_index < self.n_cities):
            raise IndexError("Indice della città non valido.")

        # Calcola la matrice delle distanze se non già fatto (o se si vuole ricalcolarla)
        # In un'applicazione reale, si potrebbe volerla memorizzare nella classe.
        distance_matrix = self.calculate_distance_matrix()

        # Estrae le distanze dalla città di riferimento
        distances_from_city = distance_matrix[city_index]

        # Ottiene gli indici delle città ordinati per distanza
        # Esclude la città stessa (che avrà distanza 0)
        sorted_indices = np.argsort(distances_from_city)

        closest_cities_info = []
        for i in sorted_indices:
            if i == city_index: # Salta la città stessa
                continue
            if len(closest_cities_info) < n:
                closest_cities_info.append(
                    (i, self.city_names[i], distances_from_city[i])
                )
            else:
                break # Abbiamo trovato le n città più vicine

        return closest_cities_info