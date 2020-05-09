import phonenumbers
from phonenumbers import geocoder, carrier, timezone


class phone:
    '''
    Classe rappresentante un numero di telefono. Tramite costruttore può ottenere i dati di un numero telefonico.

    Proprietà:
    @number: Numero di telefono (Stringa)
    @carrier: Nome operatore telefonico originale del numero (Stringa)
    @geolocation: Paese di appartenenza del numero (Stringa)
    @timezone: Timezone in cui è utilizzato il telefono (Stringa)
    '''

    def __init__(self, phone_number):
        self.number = None
        self.carrier = None
        self.geolocation = None
        self.timezone = None

        # Se non è presente aggiunge il + per il prefisso internazionale (evita
        # eccezioni)
        if not '+' in phone_number:
            # Rimuove eventuali + non al primo carattere
            phone_number = '+{}'.format(phone_number.replace('+', ''))

        # Ottiene informazioni sul numero considerandolo come internazionale
        parsed_phone = phonenumbers.parse('{}'.format(phone_number), None)

        # Verifica se il numero è corretto e valido
        if not phonenumbers.is_possible_number(parsed_phone):
            return None
        if not phonenumbers.is_valid_number(parsed_phone):
            return None

        # Il numero è valido, lo formatto con metodo internazionale
        # (+00 11 2222 3333)
        self.number = phonenumbers.format_number(
            parsed_phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

        # Geolocalizza il numero
        self.geolocation = geocoder.description_for_number(parsed_phone, 'it')

        # Identifica l'operatore
        self.carrier = carrier.name_for_number(parsed_phone, 'it')

        # Identifica la zona oraria a cui appartiene il numero
        self.timezone = timezone.time_zones_for_number(parsed_phone)
