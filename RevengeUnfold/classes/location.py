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
        location = geolocator.geocode(name)

        # Salva i dati
        self.name = location.address
        self.latitude = location.latitude
        self.longitude = location.longitude
        self.altitude = location.altitude
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
        location = geolocator.reverse('{}, {}'.format(latitude, longitude))

        # Salva i dati
        self.name = location.address
        self.latitude = location.latitude
        self.longitude = location.longitude
        self.altitude = location.altitude
        self.time = time_relevation
