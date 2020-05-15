############### External Modules Imports ###############
from geopy.geocoders import Nominatim

class location:
    """
    Class used to represents a place 
    
    Attributes
    ----------
    name : str
        Name of the place
    time : datetime
        Location detection date
    latitude : float
        Latitude of the place
    longitude : float
        Longitude of the place
    altitude : float
        Altitude of the place
    is_valid : bool
        If True the place is an existing place

    Methods
    -------
    from_coordinates(latitude, longitude, time_detection=None)
        Get the info about a place from it's coordinates
    from_name(name, time_detection=None)
        Get the info about a place from it's name
    """
    def __init__(self):
        self.name = None
        self.time = None
        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.is_valid = False

    def __eq__(self, other): 
        if not isinstance(other, location):
            # Don't attempt to compare against unrelated types
            return False
        if not self.is_valid and not other.is_valid: return False

        return self.latitude == other.latitude and self.longitude == other.longitude

    def from_coordinates(self, latitude: str, longitude: str, time_detection=None):
        """Save the location of a place based on its coordinates

        Parameters
        ----------
        latitude : str
            Location latitude
        longitude : str
            Location longitude
        time_detection : datetime, optional
            Position detection date
        """

        # Gets the information given the coordinates
        geolocator = Nominatim(user_agent='RevengeUnfold')
        reverse_location = geolocator.reverse('{}, {}'.format(latitude, longitude))

        # Save the data
        if reverse_location is not None:
            self.name = reverse_location.address
            self.latitude = reverse_location.latitude
            self.longitude = reverse_location.longitude
            self.altitude = reverse_location.altitude
            self.time = time_detection
            self.is_valid = True
        else: self.is_valid = False

    def from_name(self, name: str, time_detection=None):
        """Save the location of a place based on its name

        Parameters
        ----------
        name : str
            Name of the place from which to obtain the coordinates
        time_detection : datetime, optional
            Position detection date
        """

        # Gets the information given an address/name
        geolocator = Nominatim(user_agent='RevengeUnfold')
        reverse_location = geolocator.geocode(name)

        # Save the data
        if reverse_location is not None:
            self.name = reverse_location.address
            self.latitude = reverse_location.latitude
            self.longitude = reverse_location.longitude
            self.altitude = reverse_location.altitude
            self.time = time_detection
            self.is_valid = True
        else: self.is_valid = False