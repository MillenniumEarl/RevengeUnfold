from geopy.geocoders import Nominatim


class location:
    def __init__(self):
        self.name = None
        self.time = None
        self.latitude = None
        self.longitude = None
        self.altitude = None

    def from_name(self, name, time_relevation=None):
        '''
        Salva la posizione di un luogo a partire dal suo nome

        Params:
        @name: Nome del luogo da cui ottenere le coordinate
        @time_relevation [None]: Data di rilevazione della posizione
        '''

        # Ottiene le informazioni dato un indirizzo/nome
        geolocator = Nominatim(user_agent='RevengeUnfold')
        reverse_location = geolocator.geocode(name)

        # Salva i dati
        self.name = reverse_location.address
        self.latitude = reverse_location.latitude
        self.longitude = reverse_location.longitude
        self.altitude = reverse_location.altitude
        self.time = time_relevation

    def from_coordinates(self, latitude, longitude, time_relevation=None):
        '''
        Salva la posizione di un luogo tramite coordinate

        Params:
        @latitude: Latitudine della posizione
        @longitude: Longitudine della posizione
        @time_relevation [None]: Data di rilevazione della posizione
        '''

        # Ottiene le informazioni date le coordinate
        geolocator = Nominatim(user_agent='RevengeUnfold')
        reverse_location = geolocator.reverse('{}, {}'.format(latitude, longitude))

        # Salva i dati
        self.name = reverse_location.address
        self.latitude = reverse_location.latitude
        self.longitude = reverse_location.longitude
        self.altitude = reverse_location.altitude
        self.time = time_relevation
