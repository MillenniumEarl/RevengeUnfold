############### External Modules Imports ###############
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

class phone:
    """
    Class representing a phone number. Through the constructor it can obtain the data of a telephone number.

    Attributes
    ----------
    number : str
        Telephone number
    carrier : str
        Original telephone operator name of the number
    geolocation : str
        Country to which the number belongs
    timezone : str
        Timezone of the country where the phone is used
    """

    def __init__(self, phone_number:str):
        """
        Parameters
        ----------
        phone_number : str
            Telephone number for which to obtain information
        """
        self.number = None
        self.carrier = None
        self.geolocation = None
        self.timezone = None

        # If not present, add the + for the international prefix (avoid exceptions)
        if not '+' in phone_number:
            # Remove any + not at first character
            phone_number = '+{}'.format(phone_number.replace('+', ''))

        # It obtains information on the number considering it as international
        parsed_phone = phonenumbers.parse('{}'.format(phone_number), None)

        # Check if the number is correct and valid
        if not phonenumbers.is_possible_number(parsed_phone):
            return None
        if not phonenumbers.is_valid_number(parsed_phone):
            return None

        # The number is valid, formatted with international format
        # (+00 11 2222 3333)
        self.number = phonenumbers.format_number(
            parsed_phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

        # Geolocate the number
        self.geolocation = geocoder.description_for_number(parsed_phone, 'it')

        # Identify the operator
        self.carrier = carrier.name_for_number(parsed_phone, 'it')

        # Identifies the time zone to which the number belongs
        self.timezone = timezone.time_zones_for_number(parsed_phone)
