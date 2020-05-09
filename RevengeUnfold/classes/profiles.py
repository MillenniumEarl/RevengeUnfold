############### Standard Imports ###############
import os
import tempfile
import shutil

############### External Modules Imports ###############
import face_recognition
import photohash

############### Local Modules Imports ###############
from classes import phone
from scrape_functions import tg_functions
import password_manager


class base_profile:
    def __init__(self):
        self.platform = None
        self.user_id = None
        self.username = None
        self.first_name = None
        self.last_name = None
        self.full_name = None
        self.phone = None
        self.locations = []
        self.is_elaborated = False
        self._face_encodings = []
        self._perceptual_hashes = []

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d

    def print_info(self):
        '''
        Stampa informazioni sul profilo
        '''

        # Stampa informazioni generali
        print('Piattaforma: {}'.format(self.platform))
        print('User: {}'.format(self.username))
        print(
            'Generalita\': {} {} ({})'.format(
                self.first_name,
                self.last_name,
                self.full_name))

        # Stampa informazioni sul telefono
        if self.phone is None:
            print('Nessun telefono associato')
        else:
            print('Telefono associato: {} - {}, {}'.format(self.phone.number,
                                                           self.phone.carrier, self.phone.geolocation))

        # Stampa informazioni sull'ultima localitá associata
        if len(self.locations) > 0:
            # Ordina le localitá
            self.locations.sort(key=lambda loc: loc.utc_time, reverse=True)
            print(
                'Ultima localita\' associata: {} in data {} ({}, {})'.format(
                    self.locations[0].name,
                    self.locations[0].time,
                    self.locations[0].latitude,
                    self.locations[0].longitude))

    def compare_profile(self, profile):
        '''
        Compara il profilo con un altro profilo per verificare se appartengono alla stessa persona

        Params:
        @profile: Profilo da comparare

        Return:
        Valore di accuratezza tra i profili, più è alto maggiore la similarità
        '''

        from generic import concat

        # Variabili locali
        match = 0

        # Compara i dati dei profili
        if self.phone is not None and profile.phone is not None:
            if self.phone.number == profile.phone.number:
                match += 1

        # Ottiene il nome completo del profilo corrente
        this_fullname = concat(self.first_name, self.last_name).lower()
        if self.full_name is not None:
            this_fullname = self.full_name.lower()

        # Ottiene il nome completo del profilo comparato
        profile_fullname = concat(
            profile.first_name,
            profile.last_name).lower()
        if profile.full_name is not None:
            profile_fullname = profile.full_name.lower()

        if this_fullname in profile_fullname or profile_fullname in this_fullname:
            match += 1

        # Compara i volti dei profili
        if len(self._face_encodings) > 0:
            for face_encoding in profile._face_encodings:
                results = face_recognition.compare_faces(
                    self._face_encodings, face_encoding)
                match += results.count(True)

        # Compara le immagini tramite hash per identificare quelle similari
        for hash in self._perceptual_hashes:
            for cmp_hash in profile._perceptual_hashes:
                if photohash.hashes_are_similar(hash, cmp_hash):
                    match += 1

        return match

    def _find_faces_profile_photos(self, image_dir):
        '''
        Individua i volti presenti nelle immagini situate nella cartella e li codifica per il riconoscimento visivo

        Params:
        @image_dir: Percorso della directory delle immagini
        '''

        # Ottiene l'elenco di immagini presenti nella cartella
        dir_abs_path = os.path.abspath(image_dir)
        images_list = [os.path.join(dir_abs_path, name) for name in os.listdir(
            dir_abs_path) if os.path.isfile(os.path.join(dir_abs_path, name))]

        for image_path in images_list:
            # Verifica se l'immagine è valida, altrimenti la elimina
            try:
                image = face_recognition.load_image_file(image_path)
            except BaseException:
                os.remove(image_path)
                continue

            # Elabora i volti
            face_encodings = face_recognition.face_encodings(image)
            if len(face_encodings) == 0:
                continue  # Nessun volto individuato
            else:
                self._face_encodings.extend(face_encodings)

    def _elaborate_perceptual_hash_media(self, image_dir):
        '''
        Elabora gli hash per le immagini presenti nella directory specificata

        Params:
        @image_dir: Percorso della directory delle immagini
        '''

        # Ottiene l'elenco di immagini presenti nella cartella
        dir_abs_path = os.path.abspath(image_dir)
        images_list = [os.path.join(dir_abs_path, name) for name in os.listdir(
            dir_abs_path) if os.path.isfile(os.path.join(dir_abs_path, name))]

        # Elabora gli hash delle immagini
        for image_path in images_list:
            hash = photohash.average_hash(image_path)
            if not hash in self._perceptual_hashes:  # Evita di aggiungere doppi
                self._perceptual_hashes.append(hash)


class telegram_profile(base_profile):
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Telegram'
        self._tg_profile = None

    def get_profile_from_tg_profile(self, tg_profile):
        '''
        Dato un profilo Telegram (profilo Telethon) compila i campi del profilo corrente

        Params:
        @tg_profile: Profilo Telegram (Telethon) da cui estrapolare i dati

        Return:
        True se l'operazione va a buon fine
        '''

        self._tg_profile = tg_profile
        if tg_profile.id is not None:
            self.user_id = tg_profile.id
        if tg_profile.username is not None:
            self.username = tg_profile.username
        if tg_profile.first_name is not None:
            self.first_name = tg_profile.first_name
        if tg_profile.last_name is not None:
            self.last_name = tg_profile.last_name
        if tg_profile.phone is not None:
            self.phone = phone.phone(tg_profile.phone)
        return True

    def get_profile_from_userid(self, id, tg_client=None):
        '''
        Ottiene i dati di un profilo Telegram a partire dall'ID di tale profilo

        Params:
        @id: ID dell'utente Telegram
        @tg_client [None]: Client Telegram da usare

        Return:
        False se l'ID non esiste
        True se l'operazione va a buon fine
        '''

        # Cerca il profilo su Telegram
        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                profile = tg_functions.get_profiles(tg_client_internal, id)
        else:
            profile = tg_functions.get_profiles(tg_client, id)
        if profile is None:
            return False  # Se non esiste il profilo corrispondente ai dati indicati ritorna False
        else:
            self.get_profile_from_tg_profile(profile)
        return True

    def get_profile_from_username(self, username, tg_client=None):
        '''
        Ottiene i dati di un profilo Telegram a partire dal suo nome utente

        Params:
        @username: Username dell'utente Telegram
        @tg_client [None]: Client Telegram da usare

        Return:
        False se il nome utente non esiste
        True se l'operazione va a buon fine
        '''

        # Cerca il profilo su Telegram
        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                profile = tg_functions.get_profiles(
                    tg_client_internal, username)
        else:
            profile = tg_functions.get_profiles(tg_client, username)
        if profile is None:
            return False  # Se non esiste il profilo corrispondente ai dati indicati ritorna False
        else:
            self.get_profile_from_tg_profile(profile)
        return True

    def download_profile_photos(self, save_dir, tg_client=None):
        '''
        Salva le immagini profilo dell'utente (se presenti)

        Params:
        @save_dir: Cartella di salvataggio delle immagini
        @tg_client [None]: Client Telegram da usare

        Return:
        False se non è ancora stato associato un utente Telegram
        True se l'operazione va a buon fine
        '''

        if self._tg_profile is None:
            if self.user_id is None:
                return False
            else:
                self.get_profile_from_userid(user_id, tg_client)

        # Crea la cartella se non esiste
        save_dir = os.path.abspath(save_dir)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                tg_functions.download_users_profile_photos(
                    tg_client_internal, self._tg_profile, save_dir)
        else:
            tg_functions.download_users_profile_photos(
                tg_client, self._tg_profile, save_dir)

        return True

    def elaborate_images(self, image_dir=None, tg_client=None):
        '''
        Elabora le immagini associate al profilo per individuare volti e hash delle immagini

        Params:
        @image_dir [None]: Percorso della directory delle immagini (se non specificata ne verrà usata una temporanea)
        @tg_client [None]: Client Telegram da usare

        Return:
        False se non è ancora stato associato un utente Telegram
        True se l'operazione va a buon fine
        '''

        # Variabili locali
        use_temp_dir = False

        # Verifica i parametri
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Crea una cartella temporanea
        else:
            image_dir = os.path.abspath(image_dir)

        # Verifica se ci sono immagini, altrimenti le scarica
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_profile_photos(image_dir, tg_client) == False:
                return False

        # Elabora le immagini alla ricerca di volti
        self._find_faces_profile_photos(image_dir)

        # Elabora le immagini per ricavarne il perceptual hash
        self._elaborate_perceptual_hash_media(image_dir)

        # Elimina la cartella temporanea utilizzata
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True


class instagram_profile(base_profile):
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Instagram'
        self._ig_profile = None
        self.biography = None
        self.is_private = None

    def get_profile_from_ig_profile(self, ig_profile):
        '''
        Dato un profilo Instagram (profilo Instaloader) compila i campi del profilo corrente

        Params:
        @ig_profile: Profilo Instagram (Instaloader) da cui estrapolare i dati

        Return:
        True se l'operazione va a buon fine
        '''

        self._ig_profile = ig_profile
        if ig_profile.userid is not None:
            self.user_id = ig_profile.userid
        if ig_profile.username is not None:
            self.username = ig_profile.username
        if ig_profile.full_name is not None:
            self.full_name = ig_profile.full_name
        if ig_profile.biography is not None:
            self.biography = ig_profile.biography
        if ig_profile.is_private is not None:
            self.is_private = ig_profile.is_private
        return True

    def get_profile_from_username(self, ig_scraper, username):
        '''
        Ottiene i dati di un profilo Instagram a partire dal suo nome utente

        Params:
        @ig_scraper: Istanza di scrape_functions.ig_scraper utilizzata per cercare i dati
        @username: Username dell'utente Instagram

        Return:
        False se il nome utente non esiste
        True se l'operazione va a buon fine
        '''

        # Cerca il profilo su Instagram
        profile = ig_scraper.find_user_by_username(ig_client, username)

        if profile is None:
            return False  # Se non esiste il profilo corrispondente ai dati indicati ritorna False
        else:
            self.get_profile_from_ig_profile(profile)
            return True

    def download_photos(self, ig_scraper, save_dir):
        '''
        Salva le immagini dell'utente (se presenti)

        Params:
        @ig_scraper: Istanza di scrape_functions.ig_scraper utilizzata per cercare i dati
        @save_dir: Cartella di salvataggio delle immagini

        Return:
        False se non è ancora stato associato un utente Instagram
        True se l'operazione va a buon fine
        '''

        if self._ig_profile is None:
            if self.username is None:
                return False
            else:
                self.get_profile_from_username(self.username)

        # Crea la cartella se non esiste
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        ig_scraper.download_profile_photo(self._ig_profile, save_dir)
        ig_scraper.download_post_images(self._ig_profile, save_dir)

        return True

    def elaborate_images(self, ig_scraper, image_dir=None):
        '''
        Elabora le immagini associate al profilo per individuare volti e hash delle immagini

        Params:
        @ig_scraper: Istanza di scrape_functions.ig_scraper utilizzata per cercare i dati
        @image_dir [None]: Percorso della directory delle immagini (se non specificata ne verrà usata una temporanea)

        Return:
        False se non è ancora stato associato un utente Telegram
        True se l'operazione va a buon fine
        '''

        # Variabili locali
        use_temp_dir = False

        # Verifica i parametri
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Crea una cartella temporanea
        else:
            image_dir = os.path.abspath(image_dir)

        # Verifica se ci sono immagini, altrimenti le scarica
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(ig_scraper, image_dir) == False:
                return False

        # Elabora le immagini alla ricerca di volti
        self._find_faces_profile_photos(image_dir)

        # Elabora le immagini per ricavarne il perceptual hash
        self._elaborate_perceptual_hash_media(image_dir)

        # Elimina la cartella temporanea utilizzata
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True

    def get_locations_history(self, ig_scraper):
        '''
        Ottiene tutti i geotag dei post per uno specifico profilo Instagram.
        E' necessario essere loggati per usare questa funzione.

        Params:
        @ig_scraper: Istanza di scrape_functions.ig_scraper utilizzata per cercare i dati

        Return:
        True se l'operazione é eseguita correttamente, False altrimenti
        '''

        if self._ig_profile is None or not ig_scraper.is_logged:
            return False

        # E' richiesta una connessione NON anonima
        location_history = ig_scraper.get_location_history(self._ig_profile)
        self.locations.extend(location_history)

        return True


class facebook_profile(base_profile):
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Facebook'
        self.biography = None

    def get_profile_from_username(self, fb_scraper, username):
        '''
        Ottiene i dati di un profilo Facebook a partire dal suo nome utente.
        Sovrascrive i dati precedentemente salvati nel profilo chiamante.

        Params:
        @fb_scraper: Istanza di scrape_functions.fb_scraper utilizzata per cercare i dati
        @username: Username dell'utente Facebook

        Return:
        False se il nome utente non esiste o non si è connessi a Facebook
        True se l'operazione va a buon fine
        '''

        if not fb_scraper.is_logged:
            return False

        # Cerca il profilo su Facebook
        profile = fb_scraper.find_user_by_username(username)

        if profile is None:
            return False  # Se non esiste il profilo corrispondente ai dati indicati ritorna False
        else:
            self = profile
            return True

    def download_photos(self, fb_scraper, save_dir):
        '''
        Salva le immagini dell'utente (se presenti)

        Params:
        @fb_scraper: Istanza di scrape_functions.fb_scraper utilizzata per cercare i dati
        @save_dir: Cartella di salvataggio delle immagini

        Return:
        False se non è presente il nome utente del profilo (username) o non è stato effettuato il login a Facebook
        True se l'operazione va a buon fine
        '''

        if self.username is None:
            return False
        if not fb_scraper.is_logged:
            return False

        # Crea la cartella se non esiste
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        fb_scraper.download_profile_images(self, save_dir)
        fb_scraper.download_profile_photo(
            self, os.path.join(save_dir, 'profile.jpg'))

        return True

    def elaborate_images(self, fb_scraper, image_dir=None):
        '''
        Elabora le immagini associate al profilo per individuare volti e hash delle immagini

        Params:
        @fb_scraper: Istanza di scrape_functions.fb_scraper utilizzata per cercare i dati
        @image_dir [None]: Percorso della directory delle immagini (se non specificata ne verrà usata una temporanea)

        Return:
        False se non è ancora stato associato un utente Telegram
        True se l'operazione va a buon fine
        '''

        # Variabili locali
        use_temp_dir = False

        # Verifica i parametri
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Crea una cartella temporanea
        else:
            image_dir = os.path.abspath(image_dir)

        # Verifica se ci sono immagini, altrimenti le scarica
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(fb_scraper, image_dir) == False:
                return False

        # Elabora le immagini alla ricerca di volti
        self._find_faces_profile_photos(image_dir)

        # Elabora le immagini per ricavarne il perceptual hash
        self._elaborate_perceptual_hash_media(image_dir)

        # Elimina la cartella temporanea utilizzata
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True


class twitter_profile(base_profile):
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Twitter'
        self.biography = None

    def get_profile_from_username(self, tw_scraper, username):
        '''
        Ottiene i dati di un profilo Twitter a partire dal suo nome utente.
        Sovrascrive i dati precedentemente salvati nel profilo chiamante.

        Params:
        @tw_scraper: Istanza di scrape_functions.tw_scraper utilizzata per cercare i dati
        @username: Username dell'utente Twitter

        Return:
        False se il nome utente non esiste o tw_scraper non è inizializzato
        True se l'operazione va a buon fine
        '''

        if not tw_scraper.is_initialized:
            return False

        # Cerca il profilo su Twtter
        profile = tw_scraper.find_user_by_username(username)

        if profile is None:
            return False  # Se non esiste il profilo corrispondente ai dati indicati ritorna False
        else:
            self = profile
            return True

    def download_photos(self, tw_scraper, save_dir):
        '''
        Salva le immagini dell'utente (se presenti)

        Params:
        @tw_scraper: Istanza di scrape_functions.tw_scraper utilizzata per cercare i dati
        @save_dir: Cartella di salvataggio delle immagini

        Return:
        False se non è presente il nome utente del profilo (username)  o tw_scraper non è inizializzato
        True se l'operazione va a buon fine
        '''

        if self.username is None:
            return False
        if not tw_scraper.is_initialized:
            return False

        # Crea la cartella se non esiste
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        tw_scraper.download_profile_images(self, save_dir)
        tw_scraper.download_profile_photo(
            self, os.path.join(save_dir, '{}_profile.jpg'.format(self.username)))

        return True

    def elaborate_images(self, tw_scraper, image_dir=None):
        '''
        Elabora le immagini associate al profilo per individuare volti e hash delle immagini

        Params:
        @tw_scraper: Istanza di scrape_functions.tw_scraper utilizzata per cercare i dati
        @image_dir [None]: Percorso della directory delle immagini (se non specificata ne verrà usata una temporanea)

        Return:
        False se non è ancora stato associato un utente Telegram
        True se l'operazione va a buon fine
        '''

        # Variabili locali
        use_temp_dir = False

        # Verifica i parametri
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Crea una cartella temporanea
        else:
            image_dir = os.path.abspath(image_dir)

        # Verifica se ci sono immagini, altrimenti le scarica
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(tw_scraper, image_dir) == False:
                return False

        # Elabora le immagini alla ricerca di volti
        self._find_faces_profile_photos(image_dir)

        # Elabora le immagini per ricavarne il perceptual hash
        self._elaborate_perceptual_hash_media(image_dir)

        # Elimina la cartella temporanea utilizzata
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True
