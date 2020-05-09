class scraper_error:
    '''
    Classe wrapper per le eccezioni che avvengono nella classe fb_scraper

    Proprietà:
    @error_code: Codice di errore interno alla classe (Int)
    @ex: Eccezione avvenuta (Exception)
    @ex_time: Timestamp dell'eccezione (Datetime)
    '''

    def __init__(self, error_code, ex, ex_time):
        self.error_code = error_code
        self.exception = ex
        self.time = ex_time
