# We recommend reading the following article:
# https://medium.com/analytics-vidhya/the-art-of-not-getting-blocked-how-i-used-selenium-python-to-scrape-facebook-and-tiktok-fd6b31dbe85f
############### Standard Imports ###############
import datetime
import time
import os
import pickle

############### External Modules Imports ###############
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import urllib.request
from webdriver_manager.chrome import ChromeDriverManager

############### Local Modules Imports ###############
from classes.profiles import facebook_profile
from classes import phone, location, proxy
from scrape_functions import scraper_error, exceptions
import generic

# XPATH const
LOCATION_INFO_XP = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/div[2]/div/div/div[1]/div[2]/div/ul/li/div/div[2]/div/div/div[1]/div/div/ul/li/div/div[2]/div/div/span/span/ul'
PHONE_INFO_XP = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/div[2]/div[3]/div/div[1]/div[2]/div/ul/li/div/div[2]/div/div/div[1]/div/div[1]/ul/li[1]/div/div[2]/div/div/span/ul/li/ul'
NAME_DIV_XP = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/div[1]/div/div[3]/div/div[1]/div/div/h1/span[1]/a'
BIO_DIV_XP = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/div[2]/div/div/div[1]/div[2]/div/ul/li/div/div[2]/div/div/div[1]/div/ul/li/div/div/span'
IMAGE_USER_XP = '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[1]/div/div[1]/div/div[3]/div/div[2]/div[1]/div/div/a/img'
BANNED_LINK_ALERT = '//*[@id="content"]/div/div[2]/a'

# Element name (preferable to XPATH)
SEARCH_TEXTBOX_NAME = 'q'
FB_SEARCH_PEOPLE_LINK_CLASSNAME = '_32mo'
PROFILE_PHOTO_CLASSNAME = '_11kf img'
PHOTO_DIV_LIST_PHOTOS_CLASSNAME = 'uiMediaThumbImg'
FB_HOME_BUTTON_CLASSNAME = '_2md'
BIO_DESCRIPTION_CLASSNAME = '_50f9 _50f3'

# Element IDs (To be preferred to any other form of identification)
LOGIN_BUTTON_ID = 'u_0_b'
LOGIN_MAIL_ID = 'email'
LOGIN_PSW_ID = 'pass'

# URL (preferable to XPATH)
BASE_URL = 'https://www.facebook.com/'
# 'https://www.facebook.com/login/device-based/regular/login/?login_attempt=1&lwv=110'
ERROR_LOGIN_URL = 'https://www.facebook.com/login/device-based/regular/login/'
PROFILE_URL = 'https://www.facebook.com/{}'
PROFILE_PHOTOS_WITH = 'https://www.facebook.com/{}/photos'
PROFILE_PHOTOS_OF = 'https://www.facebook.com/{}/photos_all'
INFO_SECTION = 'https://www.facebook.com/{}/about'
INFO_CONTACT_SECTION = 'https://www.facebook.com/{}?sk=about&section=contact-info'
BIO_SECTION = 'https://www.facebook.com/{}?sk=about&section=bio'
SEARCH_URL = 'https://www.facebook.com/search/people/?q={}&epa=SEARCH_BOX'

# Warning codes
WEBDRIVER_NOT_INITIALIZED = 0
LOGIN_INCORRECT_CREDENTIALS = 1
USER_NOT_LOGGED = 2
TOO_MANY_REQUESTS = 3
NO_PROFILE_PHOTO = 4
UNEXPECTED_URL_VALUE = 5

# Error codes
WEBDRIVER_GENERIC_ERROR = 400
WEBDRIVER_INIT_FAILED = 401
LOGIN_GENERIC_ERROR = 402
LOGIN_CANNOT_LOAD = 403
DOWNLOAD_IMAGE_ERROR = 404
ACCOUNT_BLOCKED = 405

# Costants
SLEEP_TIME_LONG = 3
SLEEP_TIME_MEDIUM = 2
SLEEP_TIME_SHORT = 0.5
REQUEST_LIMIT_MODIFIER = 0.5
SESSION_FILE_NAME = 'session.fb_scraper'

class fb_scraper:
    '''
    Classe che rappresenta un'istanza di WebDriver e permette lo scraping di un profilo Facebook
    '''

    def __init__(self, logger=None):
        self._driver = None
        self._requests = 0
        self._instantiation_time = datetime.datetime.now()
        self._timeout = 5
        self._req_per_second = 0.056  # 200 all'ora
        self._logger = logger
        self.is_blocked = False
        self.is_logged = False
        self.is_initialized = False
        self.errors = []

    def _is_blocked(self):
        '''
        Verifica se l'account è stato bloccato (troppe richieste)
        '''

        # Crea un oggetto per l'attesa
        wait = WebDriverWait(self._driver, self._timeout)

        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, BANNED_LINK_ALERT)))
            self.is_blocked = True
            return True
        except TimeoutException as ex:
            self.is_blocked = False
            return False
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

    def _manage_error(self, error_code, ex):
        '''
        Gestisce gli errori e la loro scrittura su logger
        '''

        self.errors.append(
            scraper_error.scraper_error(
                error_code, ex, datetime.datetime.now()))
        if ex is not None:
            message = 'CODE: {} - {}'.format(error_code, str(ex))
        else:
            message = 'CODE: {}'.format(error_code)

        # Verifica se l'utente è stato bannato
        if error_code == ACCOUNT_BLOCKED:
            if self._logger is not None: self._logger.critical(message)
            self.terminate()
            return

        if self._logger is not None:
            if error_code >= 400:
                self._logger.error(message)
            else:
                self._logger.warning(message)

    def _request_manager(self):
        '''
        Questa funzione si occupa di limitare il numero di richieste per evitare di farsi bloccare da Facebook.
        Deve essere chiamata ogni volta che si effettua una richiesta ad un URL di Facebook.
        '''

        # Incrementa il numero di richieste effettuate
        self._requests += 1

        # Calcola la media di richieste effettuate dall'instanziamento
        # dell'oggetto
        delta = datetime.datetime.now() - self._instantiation_time
        avg_req_per_sec = self._requests / delta.seconds
        if self._logger is not None:
            self._logger.debug(
                'Current requests per second: {:.2f} rq/sec'.format(avg_req_per_sec))

        # Salva i dati sulle richieste per la sessione
        pickle.dump({'requests': self._requests,
                     'instantiation_time': self._instantiation_time},
                    open(os.path.abspath(SESSION_FILE_NAME),
                         'wb'),
                    protocol=pickle.HIGHEST_PROTOCOL)

        # Verifica se è stato superato il limite ed eventualmente attende
        if avg_req_per_sec > self._req_per_second:
            # Abbassa il numero di richieste al secondo ad un valore più basso
            # del massimo consentito
            wait_delta_sec = self._requests / \
                (self._req_per_second * REQUEST_LIMIT_MODIFIER)

            # Ottiene il numero di secondi da attendere
            resume_time = datetime.datetime.now() + datetime.timedelta(seconds=wait_delta_sec)
            ex = exceptions.TooManyRequests('Too many requests, need to wait {:.2f} seconds, until {} ({} requests in {} seconds)'.format(
                wait_delta_sec,
                resume_time.strftime('%d/%m/%y %H:%M:%S'),
                self._requests,
                delta.seconds))
            self._manage_error(TOO_MANY_REQUESTS, ex)

            # Attende per il tempo calcolato
            time.sleep(wait_delta_sec)

    def _image_download(self, url, save_path):
        '''
        Scarica un immagine.

        Params:
        @url: URL dell'immagine da scaricare
        @save_path: Percorso di salvataggio dell'immagine

        Return:
        True se l'immagine è stata scaricata, False altrimenti
        '''
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

    def _get_photos_link(self, username):
        '''
        Ottiene i link delle immagini dell'utente

        Params:
        @username: Nome utente del profilo da cui scaricare le immagini

        Returns:
        Lista di link
        '''

        # Variabili locali
        url_images = []
        images_link_list = []

        # Naviga sulla schermata del profilo 'Foto con utente'
        self._driver.get(PROFILE_PHOTOS_WITH.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Scende nella pagina
        self._driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        # Attende che la pagina carichi le immagini
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Ottiene tutti i DIV contenenti immagini
        images_link_list.extend([img.get_attribute('style') for img in self._driver.find_elements(
            By.CLASS_NAME, PHOTO_DIV_LIST_PHOTOS_CLASSNAME)])

        # Naviga sulla schermata del profilo 'Foto di utente'
        self._driver.get(PROFILE_PHOTOS_OF.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Scende nella pagina
        self._driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        # Attende che la pagina carichi le immagini
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Ottiene tutti i DIV contenenti immagini
        images_link_list.extend([img.get_attribute('style') for img in self._driver.find_elements(
            By.CLASS_NAME, PHOTO_DIV_LIST_PHOTOS_CLASSNAME)])

        # Selezionare 'style' e prendere l'url:
        # style="background-image:url(URL_IMMAGINE);"
        for src in images_link_list:
            #src = img.get_attribute('style')
            first = src.index('"')
            last = src.rfind('"')
            url = src[first + 1:last]
            url_images.append(url)

        return url_images

    def _find_user_page(self, username):
        '''
        Cerca la pagina principale di un utente per verificare che un utente esiste.

        Params:
        @username: Nome utente del profilo

        Return:
        True se il profilo esiste, False altrimenti
        '''

        # Bisogna essere loggati per cercare gli utenti
        if not self.is_logged:
            ex = exceptions.UserNotLogged('In order to use this function the user need to be logged to Facebook')
            self._manage_error(USER_NOT_LOGGED, ex)
            return False

        # Cerca il profilo tramite URL
        self._driver.get(PROFILE_URL.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Aspetta per vedere se viene trovata la pagina di errore
        wait = WebDriverWait(self._driver, self._timeout)
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, IMAGE_USER_XP)))
            return True
        except TimeoutException:
            return False  # Nessun utente trovato
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

    def init_scraper(self, use_proxy=True, proxy_s=None):
        '''
        Inizializza un ChromeDriver associato all'oggetto.
        Il WebDriver viene automaticamente scaricato.

        Params:
        @use_proxy [True]: Usa un proxy italiano (automatico)
        @proxy_s [None]: Proxy custom nel formato IP:Porta
        '''

        # Se é giá istanziato termina l'oggetto e lo ricrea
        if self.is_initialized:
            self.terminate()

        # Crea uno UserAgent casuale (per rendere meno unico il browser)
        software_names = [SoftwareName.CHROME.value]
        operating_systems = [
            OperatingSystem.WINDOWS.value,
            OperatingSystem.LINUX.value]

        user_agent_rotator = UserAgent(software_names=software_names,
                                       operating_systems=operating_systems,
                                       limit=100)

        user_agent = user_agent_rotator.get_random_user_agent()

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

        # Imposta le opzioni per il WebDriver
        options = Options()
        prefs = {'disk-cache-size': 4096}
        options.add_experimental_option('prefs', prefs)
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('--mute-audio')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('user-agent={}'.format(user_agent))
        if proxy_s is not None and use_proxy:
            options.add_argument('--proxy-server={}'.format(proxy_s))

        # Istanzia il driver per la navigazione automatizzata
        try:
            self._driver = webdriver.Chrome(
                executable_path=ChromeDriverManager().install(),
                options=options)

            # Per non far vedere a Facebook che è un browser automatizzato
            self._driver.maximize_window()

            # Controlla se esiste già un file di sessione ed eventualmente lo
            # carica
            if os.path.exists(os.path.abspath(SESSION_FILE_NAME)):
                session = pickle.load(
                    open(os.path.abspath(SESSION_FILE_NAME), 'rb'))
                self._requests = session['requests']
                self._instantiation_time = session['instantiation_time']

            self.is_initialized = True
            if self._logger is not None:
                self._logger.info('fb_scraper successfully initialized')
            return True
        except Exception as ex:
            self._manage_error(WEBDRIVER_INIT_FAILED, ex)
            return False

    def fb_login(self, fb_mail, fb_password):
        '''
        Esegue il login a Facebook. Il WebDriver dev'essere inizializzato.

        Params:
        @fb_mail: Email dell'account Facebook
        @fb_password: Password dell'account Facebook

        Return:
        True se è stato effettuato correttamente il login, False altrimenti (o se il WebDriver non è stato inizializzato)
        '''

        # Se il driver non è inizializzato esce
        if not self.is_initialized:
            ex = exceptions.WebDriverNotInitialized('The WebDriver is not initialized, please call the init_scraper() function')
            self._manage_error(WEBDRIVER_NOT_INITIALIZED, ex)
            return False

        # Naviga sulla pagina di login
        self._driver.get(BASE_URL)
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Cerca gli elementi per fare il login
        wait = WebDriverWait(self._driver, self._timeout)

        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.ID, LOGIN_BUTTON_ID)))
            email_field = wait.until(
                EC.presence_of_element_located((By.ID, LOGIN_MAIL_ID)))
            password_field = wait.until(
                EC.presence_of_element_located((By.ID, LOGIN_PSW_ID)))
        except TimeoutException as ex:
            self._manage_error(LOGIN_CANNOT_LOAD, ex)
            return False

        # Inserisce i dati
        email_field.send_keys(fb_mail)
        password_field.send_keys(fb_password)

        # Effettua il login (pulsante INVIO)
        login_button.send_keys(Keys.ENTER)

        # Attende che l'elemento sia visibile. Se lo è il login è corretto
        try:
            wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, FB_HOME_BUTTON_CLASSNAME)))
            self.is_logged = True
            if self._logger is not None:
                self._logger.info(
                    'Login successfully with user {}'.format(fb_mail))
            self._request_manager()
            return True
        except TimeoutException as ex:
            if _wait_for_correct_current_url(
                    self._driver, ERROR_LOGIN_URL) is True:
                self._manage_error(LOGIN_INCORRECT_CREDENTIALS, ex)
            else:
                self._manage_error(LOGIN_GENERIC_ERROR, ex)
            return False

    def terminate(self):
        '''
        Chiude il WebDriver
        '''

        if not self.is_initialized:
            return
        self._driver.quit()
        self.is_initialized = False
        self.is_logged = False
        if self._logger is not None:
            self._logger.info('fb_scraper correctly closed')

    def find_user_by_username(self, username, skip_verification=False):
        '''
        Cerca un profilo Facebook a partire dal nome utente.
        E' necessario aver effettuato il login.

        Params:
        @username: Nome utente del profilo
        @skip_verification [False]: Indica se saltare il controllo dell'esistenza del profilo

        Return:
        Profilo Facebook (profiles.facebook_profile) o None se il profilo non esiste (o non si è loggati).
        '''

        # Controlla se il profilo è bloccato
        if self.is_blocked:
            return None

        # Bisogna essere loggati per cercare gli utenti
        if not self.is_logged:
            ex = exceptions.UserNotLogged('In order to use this function the user need to be logged to Facebook')
            self._manage_error(USER_NOT_LOGGED, ex)
            return None

        # Variabili locali
        wait = WebDriverWait(self._driver, self._timeout)

        # Cerca l'utente
        if not skip_verification:
            if not self._find_user_page(username):
                return None

        # Utente esistente, estrapoliamo i dati..
        fb_user = facebook_profile()
        fb_user.username = username

        # Naviga nelle informazioni di contatto
        self._driver.get(INFO_CONTACT_SECTION.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Verifica che l'account non sia stato bloccato
        if self._is_blocked():
            ex = exceptions.FacebookAccountBlocked('The account has been blocked, you may have to wait for a day to use your account. The client will now be closed')
            self._manage_error(ACCOUNT_BLOCKED, ex)
            return None

        # Ottiene il nome completo
        try:
            fullname_div = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, NAME_DIV_XP)))
            fb_user.full_name = fullname_div.text.strip()
        except TimeoutException:
            pass

        # Ottieni telefono e abitazione
        try:
            phone_number_div = wait.until(
                EC.presence_of_element_located((By.XPATH, PHONE_INFO_XP)))
            fb_user.phone = phone.phone(phone_number_div.text)
        except TimeoutException:
            pass

        try:
            location_div = wait.until(
                EC.presence_of_element_located((By.XPATH, LOCATION_INFO_XP)))
            fb_user.location = location.location().from_name(location_div.text)
        except TimeoutException:
            pass

        # Naviga e cerca la biografia
        self._driver.get(BIO_SECTION.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        try:
            bio_div = wait.until(
                EC.presence_of_element_located((By.XPATH, BIO_DIV_XP)))
            fb_user.biography = bio_div.text.strip()
        except TimeoutException:
            pass

        # Ritorna il profilo createo
        return fb_user

    def find_user_by_keywords(self, *keywords, max_users=5):
        '''
        Cerca dei profili Facebook compatibili con le parole chiave specificate.
        E' necessario aver effettuato il login.

        Params:
        @keywords: Parole chiave da utilizzare per la ricerca
        @max_users [5]: Massimo numero di utenti da ricercare

        Return:
        Lista di profili Facebook (profiles.facebook_profile)
        '''

        # Variabili locali
        usernames = []
        fb_profiles = []
        links = []

        # Controlla se il profilo è bloccato
        if self.is_blocked:
            return []

        # Bisogna essere loggati per cercare gli utenti
        if not self.is_logged:
            ex = exceptions.UserNotLogged('In order to use this function the user need to be logged to Facebook')
            self._manage_error(USER_NOT_LOGGED, ex)
            return []

        # Compone l'URL da utilizzare per la ricerca
        keys = [str(s).strip() for s in keywords if s is not None]
        search_string = '%20'.join(keys)
        if search_string == '':
            return []
        self._driver.get(SEARCH_URL.format(search_string))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Ricerca i link degli utenti individuati
        links = self._driver.find_elements(
            By.CLASS_NAME, FB_SEARCH_PEOPLE_LINK_CLASSNAME)

        # Ottiene i link degli utenti
        links = [link.get_attribute('href')for link in links]

        # Ottiene gli username degli utenti
        for link in links:
            username = link.replace(BASE_URL, '')
            index_question_mark = username.find('?')

            # Valore non trovato, possibile cambiamento nelle URL di Facebook
            if index_question_mark == -1:
                continue
            else:
                username = username[:index_question_mark]

            # Un qualche utente standard?
            if 'profile.php' in usernames:
                usernames.remove('profile.php')

            # Aggiunge il nome utente
            usernames.append(username)

        # Limita il massimo numero di profili da cercare
        if len(usernames) > max_users:
            usernames = usernames[:max_users]

        # Ottiene i dati dei profili
        for username in usernames:
            # Esce dal ciclo se il profilo è bloccato
            if self.is_blocked: break

            # Saltiamo la verifica perchè sappiamo già che i profili esistono
            p = self.find_user_by_username(username, skip_verification=True)
            if p is not None: fb_profiles.append(p)
            time.sleep(SLEEP_TIME_LONG)

        if self._logger is not None:
            self._logger.info(
                'Found {} profiles with the keywords: {}'.format(
                    len(fb_profiles), generic.only_ASCII(','.join(keys))))
        return fb_profiles

    def download_profile_photo(self, fb_profile, save_path):
        '''
        Scarica l'immagine profilo dell'utente specificato.
        E' necessario aver effettuato il login.

        Params:
        @fb_profile: Profilo Facebook (profiles.facebook_profile) di cui scaricare l'immagine profilo
        @save_path: Percorso di salvataggio dell'immagine

        Return:
        True se l'immagine è stata scaricata, False altrimenti
        '''

        # Controlla se il profilo è bloccato
        if self.is_blocked:
            return False

        # Bisogna essere loggati per scaricare le immagini
        if not self.is_logged:
            ex = exceptions.UserNotLogged('In order to use this function the user need to be logged to Facebook')
            self._manage_error(USER_NOT_LOGGED, ex)
            return False

        # Naviga sul profilo dell'utente
        self._driver.get(PROFILE_URL.format(fb_profile.username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Ottiene l'immagine profilo
        try:
            wait = WebDriverWait(self._driver, self._timeout)
            profile_image = wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, PROFILE_PHOTO_CLASSNAME)))
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

    def download_profile_images(self, fb_profile, save_dir, max_photo=30):
        '''
        Scarica le immagini del profilo utente.
        E' necessario aver effettuato il login.

        Params:
        @fb_profile: Profilo Facebook (profiles.facebook_profile) di cui scaricare le immagini
        @save_dir: Directory di salvataggio delle immagini
        @max_photo [30]: Massimo numero di foto da scaricare
        '''

        # Variabili locali
        url_images = []

        # Controlla se il profilo è bloccato
        if self.is_blocked:
            return False

        # Bisogna essere loggati per scaricare le immagini
        if not self.is_logged:
            ex = exceptions.UserNotLogged('In order to use this function the user need to be logged to Facebook')
            self._manage_error(USER_NOT_LOGGED, ex)
            return False

        # Crea la cartella se serve
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Ottiene i link alle immagini
        url_images = self._get_photos_link(fb_profile.username)

        # Limita il numero di foto da scaricare
        if len(url_images) > max_photo:
            url_images = url_images[:max_photo]

        # Scarica le immagini con il formato 'nomeutente_index.jpg'
        index = 0
        for url in url_images:
            abs_dir = os.path.abspath(save_dir)
            save_path = os.path.join(
                abs_dir, '{}_{}.jpg'.format(fb_profile.username, index))
            self._image_download(url, save_path)
            time.sleep(SLEEP_TIME_SHORT)
            index += 1

        return True

#######################################################################


def _wait_for_correct_current_url(driver, desired_url, timeout=10):
    '''
    Attende che una pagina carichi una URL specifica
    '''

    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(lambda driver: driver.current_url == desired_url)
        return True
    except TimeoutException:
        return False
