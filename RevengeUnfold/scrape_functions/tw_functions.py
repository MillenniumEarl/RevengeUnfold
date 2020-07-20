############### Standard Imports ###############
import datetime
import os

############### External Modules Imports ###############
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from twitter_scraper import Profile as TwProfile
import urllib.request
from webdriver_manager.chrome import ChromeDriverManager

############### Local Modules Imports ###############
from classes.profiles import twitter_profile
from classes import location, proxy
from scrape_functions import scraper_error, exceptions
import generic

# Valori XPATH
RESULTS_USERNAMES_XPATH = "//a[@href and @role='link']//span[contains(text(), '@')]"
PROFILE_PHOTO_XPATH = '//img'
LAST_PHOTOS_XPATH = "//img[contains(@src, 'media')]"

# Costanti URL
SEARCH_PEOPLE_URL = 'https://twitter.com/search?q={}&src=typed_query&f=user'
PROFILE_PHOTO_URL = 'https://twitter.com/{}/photo'
PROFILE_URL = 'https://twitter.com/{}'

# Codici di warning
WEBDRIVER_NOT_INITIALIZED = 0
TOO_MANY_REQUESTS = 3
NO_PROFILE_PHOTO = 4
UNEXPECTED_URL_VALUE = 5

# Codici di errore
WEBDRIVER_GENERIC_ERROR = 400
WEBDRIVER_INIT_FAILED = 401
DOWNLOAD_IMAGE_ERROR = 404
ACCOUNT_BANNED = 405

class tw_scraper:
    def __init__(self, logger = None):
        self._driver = None
        self._timeout = 5
        self._logger = logger
        self.is_initialized = False
        self.errors = []

    def _manage_error(self, error_code, ex):
        """
        Gestisce gli errori e la loro scrittura su logger
        """

        self.errors.append(
            scraper_error.scraper_error(
                error_code, ex, datetime.datetime.now()))
        if ex is not None:
            message = 'CODE: {} - {}'.format(error_code, str(ex))
        else:
            message = 'CODE: {}'.format(error_code)

        if self._logger is not None:
            if error_code >= 400:
                self._logger.error(message)
            else:
                self._logger.warning(message)

    def _image_download(self, url, save_path):
        """
        Scarica un immagine.

        Params:
        @url: URL dell'immagine da scaricare
        @save_path: Percorso di salvataggio dell'immagine

        Return:
        True se l'immagine è stata scaricata, False altrimenti
        """
        try:
            if url.lower().startswith('http'): # Download only HTTP URLs
                urllib.request.urlretrieve(url, os.path.abspath(save_path))
                return True
            else:
                ex = exceptions.UnexpectedURLValue('URL {} is not valid'.format(url))
                self._manage_error(UNEXPECTED_URL_VALUE, ex)
                return False
        except Exception as ex:
            self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return False

    def init(self, use_proxy=True, proxy_s=None):
        """
        Inizializza un ChromeDriver associato all'oggetto.
        Il WebDriver viene automaticamente scaricato.

        Params:
        @use_proxy [True]: Usa un proxy italiano (automatico)
        @proxy_s [None]: Proxy custom nel formato IP:Porta
        """

        # Se é giá istanziato termina l'oggetto e lo ricrea
        if self.is_initialized:
            self.terminate()

        # Ottiene un proxy nel paese selezionato
        if use_proxy and proxy_s is None:
            proxy_obj = proxy.proxy()
            proxy_s = proxy_obj.get()
            if proxy_s is not None:
                if self._logger is not None:
                    self._logger.info('Selected proxy: {}'.format(proxy_s))
            else:
                if self._logger is not None:
                    self._logger.info('No proxy available')

        # Imposta le opzioni per il WebDriver->Non salvare la cache, Twitter dà problemi
        options = Options()
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('--mute-audio')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        if proxy_s is not None and use_proxy:
            options.add_argument('--proxy-server={}'.format(proxy_s))

        # Istanzia il driver per la navigazione automatizzata
        try:
            self._driver = webdriver.Chrome(
                executable_path=ChromeDriverManager().install(),
                options=options)

            # Per non far vedere a Twitter che è un browser automatizzato
            self._driver.maximize_window()

            self.is_initialized = True
            if self._logger is not None:
                self._logger.info('tw_scraper successfully initialized')
            return True
        except Exception as ex:
            self._manage_error(WEBDRIVER_INIT_FAILED, ex)
            return False

    def terminate(self):
        """
        Chiude il WebDriver
        """

        if not self.is_initialized:
            return

        self._driver.quit()
        self.is_initialized = False
        if self._logger is not None:
            self._logger.info('tw_scraper correctly closed')

    def find_user_by_username(self, username):
        """
        Cerca un profilo Twitter a partire dal nome utente.

        Params:
        @username: Nome utente del profilo

        Return:
        Profilo Twitter (profiles.twitter_profile) o None se il profilo non esiste (o il WebDriver non è inizializzato)
        """

        try:
            # Get the data from Twitter
            profile = TwProfile(username)

            # Convert the data to profiles.twitter_profile
            tw_user = twitter_profile()
            tw_user.username = profile.username
            tw_user.full_name = profile.name

            if tw_user.biography != '':
                tw_user.biography = profile.biography

            tw_loc = profile.location
            if tw_loc != '':
                loc = location.location().from_name(tw_loc)
                if loc.is_valid: tw_user.locations.append(loc)
        except ValueError:
            # Profile not exists
            return None
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return None

        # Ritorna il profilo createo
        return tw_user

    def find_user_by_keywords(self, *keywords, max_users=10):
        """
        Cerca dei profili Twitter compatibili con le parole chiave specificate.

        Params:
        @keywords: Parole chiave da utilizzare per la ricerca
        @max_users [5]: Massimo numero di utenti da ricercare

        Return:
        Lista di profili Twitter (profiles.twitter_profile)
        """

        # Variabili locali
        usernames = []
        tw_profiles = []

        if not self.is_initialized:
            ex = exceptions.WebDriverNotInitialized('The WebDriver is not initialized, please call the init() function')
            self._manage_error(WEBDRIVER_NOT_INITIALIZED, ex)
            return None

        # Compone l'URL da utilizzare per la ricerca
        keys = [str(s).strip() for s in keywords if s is not None]
        search_string = ' '.join(keys)
        if search_string == '':
            return []
        self._driver.get(SEARCH_PEOPLE_URL.format(search_string))

        # Ricerca gli username degli utenti individuati
        usernames_elms = self._driver.find_elements(By.XPATH, RESULTS_USERNAMES_XPATH)

        # Ottiene i link degli utenti
        usernames = [elm.text for elm in usernames_elms]

        # Limita il massimo numero di profili da cercare
        if len(usernames) > max_users:
            usernames = usernames[:max_users]

        # Ottiene i dati dei profili
        for username in usernames:
            p = self.find_user_by_username(username)
            tw_profiles.append(p)

        if self._logger is not None:
            self._logger.info(
                'Found {} profiles with the keywords: {}'.format(
                    len(tw_profiles), generic.only_ASCII(','.join(keys))))
        return tw_profiles

    def download_profile_photo(self, tw_profile, save_path):
        """
        Scarica l'immagine profilo dell'utente specificato.

        Params:
        @tw_profile: Profilo Twitter (profiles.twitter_profile) di cui scaricare l'immagine profilo
        @save_path: Percorso di salvataggio dell'immagine

        Return:
        True se l'immagine è stata scaricata, False altrimenti
        """

        if not self.is_initialized:
            ex = exceptions.WebDriverNotInitialized('The WebDriver is not initialized, please call the init() function')
            self._manage_error(WEBDRIVER_NOT_INITIALIZED, ex)
            return False

        # Naviga sull'immagine profilo
        self._driver.get(PROFILE_PHOTO_URL.format(tw_profile.username))

        # Ottiene l'immagine profilo
        try:
            wait = WebDriverWait(self._driver, self._timeout)
            profile_image = wait.until(
                EC.presence_of_element_located((By.XPATH, PROFILE_PHOTO_XPATH)))
        except TimeoutException:
            ex = exceptions.NoProfilePhoto('The user does not have a profile photo')
            self._manage_error(NO_PROFILE_PHOTO, ex)
            return False
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

        # Ottiene l'URL dell'immagine
        url = profile_image.get_attribute('src')

        # Scarica l'immagine
        return self._image_download(url, save_path)

    def download_profile_images(self, tw_profile, save_dir, max_photo=30):
        """
        Scarica le immagini del profilo utente.

        Params:
        @tw_profile: Profilo Twitter (profiles.twitter_profile) di cui scaricare le immagini
        @save_dir: Directory di salvataggio delle immagini
        @max_photo [30]: Massimo numero di foto da scaricare
        """

        # Variabili locali
        url_images = []

        if not self.is_initialized:
            ex = exceptions.WebDriverNotInitialized('The WebDriver is not initialized, please call the init() function')
            self._manage_error(WEBDRIVER_NOT_INITIALIZED, ex)
            return False

        # Naviga sull'immagine profilo
        self._driver.get(PROFILE_URL.format(tw_profile.username))

        # Crea la cartella se serve
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Ottiene i link alle immagini
        url_images_elms = self._driver.find_elements(By.XPATH, LAST_PHOTOS_XPATH)
        url_images = [elm.get_attribute('src') for elm in url_images_elms]

        # Limita il numero di foto da scaricare
        if len(url_images) > max_photo:
            url_images = url_images[:max_photo]

        # Scarica le immagini con il formato 'nomeutente_index.jpg'
        index = 0
        for url in url_images:
            abs_dir = os.path.abspath(save_dir)
            save_path = os.path.join(
                abs_dir, '{}_{}.jpg'.format(tw_profile.username, index))
            self._image_download(url, save_path)
            index += 1

        return True