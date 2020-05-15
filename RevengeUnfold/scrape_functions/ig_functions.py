############### Standard Imports ###############
import os
import datetime
import sys

############### External Modules Imports ###############
from instaloader import ProfileNotExistsException, PrivateProfileNotFollowedException
from instaloader.exceptions import ConnectionException
import instaloader

############### Local Modules Imports ###############
from scrape_functions import scraper_error, exceptions
from classes import location, profiles
import generic
import password_manager

# Global variables
_anonymous_client_blocked = False

# Manage 429 rate limit for anonymous client
def too_many_requests_hook(exctype, value, traceback):
    if exctype == ConnectionException and 'redirected to login' in str(ex):
        _anonymous_client_blocked = True
    else:
        sys.__excepthook__(exctype, value, traceback)

sys.excepthook = too_many_requests_hook

# Warning codes
CLIENT_NOT_INITIALIZED = 0
LOGIN_INCORRECT_CREDENTIALS = 1
USER_NOT_LOGGED = 2
CLIENT_BLOCKED = 3

# Error codes
CLIENT_GENERIC_ERROR = 400
PROFILE_NOT_EXISTS = 401
PRIVATE_PROFILE_NOT_FOLLOWED = 402
DOWNLOAD_IMAGE_ERROR = 403
LOGIN_GENERIC_ERROR = 404
TOO_MANY_ANON_REQUESTS = 405
TOO_MANY_REQUESTS = 406

class ig_scraper:
    '''
    Classe che rappresenta un'istanza Instaloader e permette lo scraping di Instagram
    '''

    def __init__(self, logger=None):
        self._ig_client = None
        self._logger = logger
        self.is_blocked = False
        self.is_logged = False
        self.is_initialized = False
        self.errors = []

    def _manage_error(self, error_code, ex):
        '''
        Gestisce gli errori e la loro scrittura su logger
        '''
        self.errors.append(scraper_error.scraper_error(error_code, ex, datetime.datetime.now()))
        if ex is not None: message = 'CODE: {} - {}'.format(error_code, str(ex))
        else: message = 'CODE: {}'.format(error_code)

        if self._logger is not None:
            if error_code >= 400: self._logger.error(message)
            else: self._logger.warning(message)

        if error_code == TOO_MANY_ANON_REQUESTS:
            if self._logger is not None: self._logger.warning('Changing from anonymous client to logged client')
            self.login(password_manager.ig_username, password_manager.ig_password)
        elif error_code == TOO_MANY_REQUESTS:
            if self._logger is not None: self._logger.critical('Too many request, closing client...')
            self.is_blocked = True
            self.terminate()

    def _connect_instagram_client(self, username, password, anonymous=True):
        '''
        Crea e connette un client Instagram.
        Se anonymous = True le credenziali non verrano usate (possono essere qualunque valore)

        Params:
        @username: Nome utente del proprio account Instagram
        @password: Password del proprio account Instagram
        @anonymous [True]: Connessione in maniera anonima (senza credenziali)

        Return:
        True se la connessione é avvenuta correttamente, False altrimenti
        '''

        # Crea il client
        ig_client = instaloader.Instaloader(quiet=True, download_videos=False,
                                            download_comments=False, compress_json=True, max_connection_attempts=1)
        # File di salvataggio della sessione
        ig_session_file = 'instagram_session.session'

        # Se è stato specificato un client anonimo non vengono specificate le
        # credenziali
        if anonymous:
            self._ig_client = ig_client

            if self._logger is not None:
                self._logger.info('Successfully connected anonymously')
            return True

        # Se esiste un file di sessione già configurato lo carica
        if os.path.exists(ig_session_file) and not anonymous:
            ig_client.load_session_from_file(username, ig_session_file)
        else:
            try:
                ig_client.login(username, password)
                ig_client.save_session_to_file(ig_session_file)
            except Exception as ex:
                self._manage_error(LOGIN_GENERIC_ERROR, ex)
                return False

        if ig_client.test_login() is None:
            return False

        self._ig_client = ig_client
        if self._logger is not None:
            self._logger.info(
                'Successfully connected to user {}'.format(generic.only_ASCII(username)))
        return True

    def _convert_profile_from_instaloader(self, instaloader_profile):
        '''
        Convert an Instaloader profile to a classes.profiles.instagram_profiles

        Params:
        @instaloader_profile: Instaloader profile to convert

        Return
        The converted classes.profiles.instagram_profile object
        '''

        # Check if the client is blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Copy the data
        ig_profile = profiles.instagram_profile()

        ig_profile._ig_profile = instaloader_profile
        if instaloader_profile.userid is not None:
            ig_profile.user_id = instaloader_profile.userid
        if instaloader_profile.username is not None:
            ig_profile.username = instaloader_profile.username
        if instaloader_profile.full_name is not None:
            ig_profile.full_name = instaloader_profile.full_name
        if instaloader_profile.is_private is not None:
            ig_profile.is_private = instaloader_profile.is_private
        if instaloader_profile.biography is not None:
            ig_profile.biography = instaloader_profile.biography

        return ig_profile

    def find_similar_profiles(self, ig_profile, max_profiles = 10):
        '''
        Trova profili simili a quello specificato.
        E' necessario essere loggati per usare questa funzione.

        Params:
        @ig_profile: Profilo Instaloader da cui trovare utenti simili
        @max_profiles: Numero massimo di profili da ottenere

        Return:
        Lista di profili (classes.profiles.ig_profile) simili
        '''

        # E' necessario essere loggati per usare questa funzione
        if not self.is_logged:
            self._manage_error(USER_NOT_LOGGED, None)
            return []

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            # Ottiene i profili simili
            profiles = ig_profile.get_similar_accounts()
            profiles = [profile for profile in profiles]

            # Limita il numero di profili
            if len(profiles) > max_profiles:
                profiles = profiles[:max_profiles]

            # Convert the profile
            converted_profiles = []
            for p in profiles:
                ig_profile = self._convert_profile_from_instaloader(p)
                converted_profiles.append(ig_profile)

            if self._logger is not None:
                self._logger.info(
                    'Found {} profiles similar to {}'.format(
                        len(converted_profiles), ig_profile.username))

            return converted_profiles
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return []

    def find_user_by_username(self, username):
        '''
        Trova un profilo Instagram a partire dal nome utente

        Params:
        @username: Nome utente dell'utente da trovare

        Return:
        Profilo individuato (classes.profiles.ig_profile) o None se non viene trovato
        '''

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            profile_found = instaloader.Profile.from_username(self._ig_client.context, username)

            # Convert the profile
            ig_profile = self._convert_profile_from_instaloader(profile_found)

            if self._logger is not None:
                self._logger.info('User {} found'.format(username))

            return ig_profile
        except ProfileNotExistsException as ex:
            self._manage_error(PROFILE_NOT_EXISTS, ex)
            return None
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.find_user_by_username(username)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests('Too many requests for the Instagram client')
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return None
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return None

    def find_user_by_keywords(self, *keywords, max_profiles = 10):
        '''
        Cerca dei profili Instagram in base alle parole chiave usate

        Params:
        @keyords: Nome utente dell'utente da trovare
        @max_profiles: Numero massimo di profili da ottenere

        Return:
        Lista di profili (classes.profiles.ig_profile) individuati
        '''

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            # Unisce le keywords
            keywords = [str(i) for i in keywords if i is not None]
            keyword = ' '.join(keywords).strip()
            if keyword == '':
                return []

            # Ricerca i profili
            results = instaloader.TopSearchResults(self._ig_client.context, keyword)
            profiles = [profile for profile in results.get_profiles()]

            # Limita il numero di profili
            if len(profiles) > max_profiles:
                profiles = profiles[:max_profiles]

            # Convert the profile
            converted_profiles = []
            for p in profiles:
                ig_profile = self._convert_profile_from_instaloader(p)
                converted_profiles.append(ig_profile)

            if self._logger is not None:
                self._logger.info(
                    'Found {} profiles with keywords {}'.format(
                        len(converted_profiles), generic.only_ASCII(keyword)))
            return converted_profiles
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.find_user_by_keywords(keywords, max_profiles)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests('Too many requests for the Instagram client')
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return []
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return []

    def download_post_images(self, ig_profile, save_dir, max_posts=20):
        '''
        Scarica le immagini pesenti nei post di un profilo specificato

        Params:
        @ig_profile: Profilo Instagram (Instaloader) di cui recuperare i post
        @save_dir: Directory dove salvare le immagini scaricate
        @max_posts [20]: Numero massimo di immagini da scaricare

        Return:
        True se le immagini sono state scaricate, False altrimenti
        '''

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        # Ottiene l'elenco dei post
        try: post_list = ig_profile.get_posts()
        except PrivateProfileNotFollowedException as ex:
            self._manage_error(PRIVATE_PROFILE_NOT_FOLLOWED, ex)
            return False
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_post_images(ig_profile, save_dir, max_posts)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests('Too many requests for the Instagram client')
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return None
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return False

        try:
            # Elimina i video dai post
            post_list = [post for post in post_list if not post.is_video]

            # Limita il numero di post da scaricare
            if len(post_list) > max_posts:
                post_list = post_list[:max_posts]

            # Scarica le foto
            post_index = 0
            for post in post_list:
                try:
                    savepath = os.path.join(save_dir, '{}.jpg'.format(post_index))
                    self._ig_client.download_pic(savepath, post.url, post.date_utc)
                    post_index += 1
                except Exception as ex:
                    self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return True
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_post_images(ig_profile, save_dir, max_posts)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests('Too many requests for the Instagram client')
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
                return None

    def download_profile_photo(self, ig_profile, save_dir):
        '''
        Scarica la foto profilo del profilo specificato

        Params:
        @ig_profile: Profilo Instagram (Instaloader) di cui recuperare la foto profilo
        @save_dir: Directory dove salvare la foto profilp

        Return:
        True se la foto profilo é stata scaricata, False altrimenti
        '''

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        # Ottiene la foto profilo e la salva nella cartella specificata
        try:
            self._ig_client.download_pic(
                filename=os.path.join(
                    save_dir,
                    'profile.jpg'),
                url=ig_profile.profile_pic_url,
                mtime=datetime.datetime.now())
            return True
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests('Too many requests for the anonymous Instagram client')
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_profile_photo(ig_profile, save_dir)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests('Too many requests for the Instagram client')
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
                return None
        except Exception as ex:
            self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return False

    def get_location_history(self, ig_profile):
        '''
        Ottiene tutti i geotag dei post per uno specifico profilo Instagram.
        E' necessario essere loggati per usare questa funzione.

        Params:
        @ig_profile: Profilo Instagram (Instaloader) di cui recuperare i geotag

        Return:
        Lista di localitá (classes.location) individuate
        '''

        # Variabili locali
        locations_list = []

        # E' necessario essere loggati per usare questa funzione
        if not self.is_logged:
            self._manage_error(USER_NOT_LOGGED, None)
            return []

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked('Instagram client has been blocked, please try again in a few hours')
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        # Ottiene l'elenco dei post del profilo Instagram
        try:
            post_list = ig_profile.get_posts()
        except PrivateProfileNotFollowedException as ex:
            self._manage_error(PRIVATE_PROFILE_NOT_FOLLOWED, ex)
            return []
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return []

        # Salva i geotag dei media selezionati
        post_with_location = [
            post for post in post_list if post.location is not None]
        for post in post_with_location:
            loc = location.location()
            # Ottiene la locazione dalle coordinate
            if post.location.lat is not None and post.location.lng is not None:
                loc.from_coordinates(
                    post.location.lat, post.location.lng, post.date_utc)
                locations_list.append(loc)
            elif post.location.name is not None:
                loc.from_name(post.location.name, post.date_utc)
                if loc.is_valid: locations_list.append(loc)

        # Ordina la lista dalla locazione più recente a quella meno recente
        locations_list.sort(key=lambda loc: loc.utc_time, reverse=True)

        if self._logger is not None:
            self._logger.info(
                'Found {} locations for user {}'.format(
                    len(locations_list),
                    generic.only_ASCII(ig_profile.username)))
        return locations_list

    def terminate(self):
        '''
        Termina il client e resetta le variabili
        '''

        if not self.is_initialized:
            return

        self._ig_client.close()
        self.is_initialized = False
        self.is_logged = False
        if self._logger is not None:
            self._logger.info('ig_scraper successfully closed')

    def login_anonymously(self):
        '''
        Esegue il login a Instagram in maniera anonima

        Return:
        True se la connessione é avvenuta con successo, False altrimenti
        '''

        # Se é giá istanziato termina l'oggetto e lo ricrea
        if self.is_initialized:
            self.terminate()

        if self._connect_instagram_client('', '', anonymous=True):
            self.is_initialized = True
            self.is_logged = False
            if self._logger is not None: self._logger.info('Anonymous Instagram client instanced correctly')
            return True
        else: return False

    def login(self, username, password):
        '''
        Esegue il login a Instagram usando le credenziali

        Params:
        @username: Nome utente dell'account Instagram a cui connettersi
        @password: Password dell'account Instagram a cui connettersi

        Return:
        True se la connessione é avvenuta con successo, False altrimenti
        '''

        # Se è già istanziato termina l'oggetto e lo ricrea
        if self.is_initialized:
            self.terminate()

        if self._connect_instagram_client(username, password, anonymous=False):
            self.is_initialized = True
            self.is_logged = True
            if self._logger is not None:
                self._logger.info(
                    'Instagram client correctly started (user {})'.format(generic.only_ASCII(username)))
            return True
        else: return False
