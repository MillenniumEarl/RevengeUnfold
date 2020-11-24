# We recommend reading the following article:
# https://medium.com/analytics-vidhya/the-art-of-not-getting-blocked-how-i-used-selenium-python-to-scrape-facebook-and-tiktok-fd6b31dbe85f
############### Standard Imports ###############
import datetime
import time
import os
import pickle
from typing import Type, List

############### External Modules Imports ###############
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
from classes import phone, location
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

# Global constants
SLEEP_TIME_LONG = 3
SLEEP_TIME_MEDIUM = 2
SLEEP_TIME_SHORT = 0.5
REQUEST_LIMIT_MODIFIER = 0.5
SESSION_FILE_NAME = 'session.fb_scraper'
MESSAGE_NEED_LOGIN = 'In order to use this function the user need to be logged to Facebook'
MESSAGE_ACCOUNT_BLOCKED = 'The account has been blocked, you may have to wait for a day to use your account. The client will now be closed'


class fb_scraper:
    """
    Class that represents a Selenium instance of WebDriver and allows the scraping of a Facebook profile

    Attributes
    ----------
    is_blocked: bool
        Specifies whether the client has been blocked from accessing Facebook
    is_logged: bool
        Specifies whether the client has authenticated to Facebook
    is_initialized: bool
        Specifies whether the client is initialized
    errors: list
        List of errors occurred

    Methods
    -------
    init_scraper()
        Initialize the scraper
    terminate()
        Close the scraper and release the resources
    fb_login(fb_mail, fb_password)
        Log in to Facebook
    find_user_by_username(self, username, skip_verification)
        Find a Facebook profile based on your username
    find_user_by_keywords(self, *keywords, max_users)
        Find a Facebook profile from a list of keywords
    download_profile_photo(self, fb_profile, save_path)
        Download the profile picture of a Facebook profile
    download_profile_images(self, fb_profile, save_dir, max_photo)
        Download photos of a Facebook profile
    """

    def __init__(self, logger: Type['logging.Logger'] = None):
        """
        Parameters
        ----------
        logger: logging.Logger
           Logger used to save events
           Default None
        """
        self._driver: webdriver = None
        self._requests: int = 0
        self._instantiation_time: datetime.datetime = datetime.datetime.now()
        self._timeout: float = 5
        self._req_per_second: float = 0.056  # 200 per hour
        self._logger: Type['logging.Logger'] = logger
        self.is_blocked: bool = False
        self.is_logged: bool = False
        self.is_initialized: bool = False
        self.errors: List[scraper_error.scraper_error] = []

    def _is_blocked(self) -> bool:
        """Check if the account has been blocked (too many requests)"""

        # Create an object to wait
        wait = WebDriverWait(self._driver, self._timeout)

        try:
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, BANNED_LINK_ALERT)))
            self.is_blocked = True
            return True
        except TimeoutException as ex:
            self.is_blocked = False
            return False
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

    def _manage_error(self, error_code: int, ex: Exception):
        """It manages errors and their writing on logger

        Save errors on self.errors and, if a logger has been specified,
        write an error message

        Parameters
        ----------
        error_code: int
            Identification code of the error to be written on the logger
        ex: Exception
            Exception to write on the logger
        """

        # Save the error in the list
        self.errors.append(
            scraper_error.scraper_error(
                error_code, ex, datetime.datetime.now()))
        if ex is not None:
            message = 'CODE: {} - {}'.format(error_code, str(ex))
        else:
            message = 'CODE: {}'.format(error_code)

        # Check if the user has been blocked and end the scraping
        if error_code == ACCOUNT_BLOCKED:
            if self._logger is not None:
                self._logger.critical(message)
            self.terminate()
            return

        # Writes the message to the log file
        if self._logger is not None:
            if error_code >= 400:
                self._logger.error(message)
            else:
                self._logger.warning(message)

    def _request_manager(self):
        """Manages requests to Facebook

        Deals with limiting the number of requests to avoid being blocked by Facebook.
        It must be called each time a request is made to a Facebook URL.
        """

        # Increase the number of requests made
        self._requests += 1

        # Calculates the average of requests made since the object was
        # instanced
        delta = datetime.datetime.now() - self._instantiation_time
        avg_req_per_sec = self._requests / delta.total_seconds()
        if self._logger is not None:
            self._logger.debug(
                'Current requests per second: {:.2f} rq/sec'.format(avg_req_per_sec))

        # Save request data for the session
        pickle.dump({'requests': self._requests,
                     'instantiation_time': self._instantiation_time},
                    open(os.path.abspath(SESSION_FILE_NAME),
                         'wb'),
                    protocol=pickle.HIGHEST_PROTOCOL)

        # Check if the limit has been exceeded and if necessary wait
        if avg_req_per_sec > self._req_per_second:
            # Reduces the number of requests per second to a value lower than
            # the maximum allowed
            wait_delta_sec = self._requests / \
                (self._req_per_second * REQUEST_LIMIT_MODIFIER)

            # Gets the number of seconds to wait
            resume_time = datetime.datetime.now() + datetime.timedelta(seconds=wait_delta_sec)
            ex = exceptions.TooManyRequests('Too many requests, need to wait {:.2f} seconds, until {} ({} requests in {} seconds)'.format(
                wait_delta_sec,
                resume_time.strftime('%d/%m/%y %H:%M:%S'),
                self._requests,
                delta.total_seconds()))
            self._manage_error(TOO_MANY_REQUESTS, ex)

            # Waits for the calculated time
            time.sleep(wait_delta_sec)

    def _check_scraper_usable(self):
        """Check if the scraper can be used

        Check that the scraper is logged in and not blocked by Facebook

        Return
        ------
        bool
            True if the scraper is usable, False otherwise
        """

        # Check if the profile is locked
        if self.is_blocked:
            return False

        # You must be logged in to download the images
        if not self.is_logged:
            ex = exceptions.UserNotLogged(MESSAGE_NEED_LOGIN)
            self._manage_error(USER_NOT_LOGGED, ex)
            return False

        return True

    @staticmethod
    def _wait_for_correct_current_url(
            driver: webdriver, desired_url: str, timeout: int = 10) -> bool:
        """Waits for a Web Driver to load a specific URL

        Parameters
        ----------
        driver: webdriver
            WebDriver to be used to wait for the page
        desired_url: str
            URL to wait
        timeout: int
            Maximum number of seconds to wait for verification
            Default 10

                Return
        ------
        bool
            True if the URL of the WebDriver is the same of desired_url, False otherwise
        """

        wait = WebDriverWait(driver, timeout)
        try:
            wait.until(lambda driver: driver.current_url == desired_url)
            return True
        except TimeoutException:
            return False

    def _image_download(self, url: str, save_path: str) -> bool:
        """Download an image from the profile

        Parameters
        ----------
        url: str
            URL of the image to download
        save_path: str
            Image saving path

                Return
        ------
                bool
                        True if the image was downloaded, False otherwise
        """
        try:
            if url.lower().startswith('http'):  # Download only HTTP URLs
                urllib.request.urlretrieve(url, os.path.abspath(save_path))
                return True
            else:
                ex = exceptions.UnexpectedURLValue(
                    'URL {} is not valid'.format(url))
                self._manage_error(UNEXPECTED_URL_VALUE, ex)
                return False
        except Exception as ex:
            self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return False

    def _get_photos_URL(self, username: str) -> list:
        """Gets the URLs of all the images in the user's profile

        Parameters
        ----------
        username: str
            User name of the profile from which to download the images

                Return
        ------
        list
                        List of URLs
        """

        # Local variables
        url_images = []
        images_link_list = []

        # Navigate to the 'Photos with user' profile screen
        self._driver.get(PROFILE_PHOTOS_WITH.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Scrolls down the page
        self._driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        # Waits for the page to load images
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Gets all DIVs containing images
        images_link_list.extend([img.get_attribute('style') for img in self._driver.find_elements(
            By.CLASS_NAME, PHOTO_DIV_LIST_PHOTOS_CLASSNAME)])

        # Navigate to the 'User Photos' profile screen
        self._driver.get(PROFILE_PHOTOS_OF.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Scrolls down the page
        self._driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        # Waits for the page to load images
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Gets all DIVs containing images
        images_link_list.extend([img.get_attribute('style') for img in self._driver.find_elements(
            By.CLASS_NAME, PHOTO_DIV_LIST_PHOTOS_CLASSNAME)])

        # URL is stored in the 'style' tag
        # style="background-image:url(IMAGE_URL);"
        for src in images_link_list:
            first = src.index('"')
            last = src.rfind('"')
            url = src[first + 1:last]
            url_images.append(url)

        return url_images

    def _find_user_page(self, username: str) -> bool:
        """Search a user's home page to verify that it exists

        Parameters
        ----------
        username: str
            Username of the profile to check for

                Return
        ------
        bool
                        True if the profile exists, False otherwise
        """

        # Check if the scraper can continue execution
        if not self._check_scraper_usable():
            return False

        # Search for the profile by URL
        self._driver.get(PROFILE_URL.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Wait to see if the error page is found
        wait = WebDriverWait(self._driver, self._timeout)
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, IMAGE_USER_XP)))
            return True
        except TimeoutException:
            return False  # No user found
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

    def init_scraper(self):
        """Initialize the Facebook scraper

        Initialize a ChromeDriver associated with the object.
        The WebDriver is automatically downloaded.

        Customized proxies and User Agents cannot be used because
        they would make Facebook's anti-spam algorithm suspicious
        """

        # If it is already instantiated, end the object and recreate it
        if self.is_initialized:
            self.terminate()

        # Set options for the Web Driver
        options = Options()
        prefs = {'disk-cache-size': 4096}
        options.add_experimental_option('prefs', prefs)
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('--mute-audio')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # Instantiate the driver for automated navigation
        try:
            self._driver = webdriver.Chrome(
                executable_path=ChromeDriverManager().install(),
                options=options)

            # Not to let Facebook see that it is an automated browser
            self._driver.maximize_window()

            # Check if a session file already exists and possibly upload it
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

    def fb_login(self, fb_mail: str, fb_password: str) -> bool:
        """Log in to Facebook. The Web Driver must be initialized.

        Parameters
        ----------
        fb_mail: str
            Facebook account email
        fb_password: str
            Facebook account password

                Return
        ------
        bool
                        True if successfully logged in, False otherwise (or if the Web Driver has not been initialized)
        """

        # If the driver is not initialized it exits
        if not self.is_initialized:
            ex = exceptions.WebDriverNotInitialized(
                'The WebDriver is not initialized, please call the init_scraper() function')
            self._manage_error(WEBDRIVER_NOT_INITIALIZED, ex)
            return False

        # Navigate to the login page
        self._driver.get(BASE_URL)
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Search for items to log in
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

        # Enter the data
        email_field.send_keys(fb_mail)
        password_field.send_keys(fb_password)

        # Log in (ENTER button)
        login_button.send_keys(Keys.ENTER)

        # Waits for the element to be visible. If it is, the login is correct
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
            if self.wait_for_correct_current_url(
                    self._driver, ERROR_LOGIN_URL) is True:
                self._manage_error(LOGIN_INCORRECT_CREDENTIALS, ex)
            else:
                self._manage_error(LOGIN_GENERIC_ERROR, ex)
            return False

    def terminate(self):
        """Closes the scraping session

        End the session by closing the Web Driver and resetting the properties of the scraper.
        You need to call init_scraper() again.
        """

        if not self.is_initialized:
            return
        self._driver.quit()
        self.is_initialized = False
        self.is_logged = False
        if self._logger is not None:
            self._logger.info('fb_scraper correctly closed')

    def find_user_by_username(
            self, username: str, skip_verification: bool = False) -> Type['classes.profiles.facebook_profile']:
        """Search for a Facebook profile from your username

        You must be logged in

        Parameters
        ----------
        username: str
            Profile username
        fb_password: bool
            Indicates whether to skip checking the existence of the profile
            Default False

                Return
        ------
        facebook_profile
            Facebook profile (profiles.facebook profile) or None if the profile does not exist (or you are not logged in)
        """

        # Check if the scraper can continue execution
        if not self._check_scraper_usable():
            return None

        # Search for the user
        if not skip_verification:
            if not self._find_user_page(username):
                return None

        # Existing user, we extrapolate the data...
        fb_user = facebook_profile()
        fb_user.username = username

        # Browse the contact information
        self._driver.get(INFO_CONTACT_SECTION.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Make sure your account hasn't been locked out
        if self._is_blocked():
            ex = exceptions.FacebookAccountBlocked(MESSAGE_ACCOUNT_BLOCKED)
            self._manage_error(ACCOUNT_BLOCKED, ex)
            return None

        wait = WebDriverWait(self._driver, self._timeout)
        # Gets the full name
        try:
            fullname_div = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, NAME_DIV_XP)))
            fb_user.full_name = fullname_div.text.strip()
        except TimeoutException:
            pass

        # Get phone and home
        try:
            phone_number_div = wait.until(
                EC.presence_of_element_located((By.XPATH, PHONE_INFO_XP)))
            fb_user.phone = phone.phone(phone_number_div.text)
        except TimeoutException:
            pass

        try:
            location_div = wait.until(
                EC.presence_of_element_located((By.XPATH, LOCATION_INFO_XP)))
            loc = location.location().from_name(location_div.text)
            if loc.is_valid:
                fb_user.location = loc
        except TimeoutException:
            pass

        # Browse and search the biography
        self._driver.get(BIO_SECTION.format(username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        try:
            bio_div = wait.until(
                EC.presence_of_element_located((By.XPATH, BIO_DIV_XP)))
            fb_user.biography = bio_div.text.strip()
        except TimeoutException:
            pass

        # Return the created profile
        return fb_user

    def find_user_by_keywords(
            self, *keywords, max_users: int = 5) -> List[Type['classes.profiles.facebook_profile']]:
        """Search for Facebook profiles compatible with the specified keywords

        You must be logged in

        Parameters
        ----------
        keywords: tuple
            Keywords to be used for research
        max_users: int
            Maximum number of users to search
            Default 5

                Return
        ------
        List
            List of Facebook profiles (profiles.facebook_profile)
        """

        # Local variables
        usernames = []
        fb_profiles = []
        links = []

        # Check if the scraper can continue execution
        if not self._check_scraper_usable():
            return []

        # Compose the URL to be used for the search
        keys = [str(s).strip() for s in keywords if s is not None]
        search_string = '%20'.join(keys)  # %20 is space
        if search_string == '':
            return []
        self._driver.get(SEARCH_URL.format(search_string))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Search for links from identified users
        links = self._driver.find_elements(
            By.CLASS_NAME, FB_SEARCH_PEOPLE_LINK_CLASSNAME)

        # Get user links
        links = [link.get_attribute('href')for link in links]

        # Get users' usernames
        for link in links:
            username = link.replace(BASE_URL, '')
            index_question_mark = username.find('?')

            # Value not found, possible change in Facebook URL structure
            if index_question_mark == -1:
                continue
            username = username[:index_question_mark]

            # Possible standard user? However it should be ignored
            if 'profile.php' in usernames:
                usernames.remove('profile.php')

            # Add your username
            usernames.append(username)

        # Limit the maximum number of profiles to search
        if len(usernames) > max_users:
            usernames = usernames[:max_users]

        # Get profile data
        for username in usernames:
            # Exit the cycle if the profile is locked
            # The check is carried out in find_user_by_username
            if self.is_blocked:
                break

            # We skip the verification because we already know that the
            # profiles exist
            p = self.find_user_by_username(username, skip_verification=True)
            if p is not None:
                fb_profiles.append(p)
            time.sleep(SLEEP_TIME_LONG)

        if self._logger is not None:
            self._logger.info(
                'Found {} profiles with the keywords: {}'.format(
                    len(fb_profiles), generic.only_ASCII(','.join(keys))))
        return fb_profiles

    def download_profile_photo(
            self, fb_profile: Type['classes.profiles.facebook_profile'], save_path: str) -> bool:
        """Download the profile picture of the specified user

        You must be logged in

        Parameters
        ----------
        fb_profile: facebook_profile
            Facebook profile to download the image from
        save_path: str
            Image saving path

                Return
        ------
        bool
            True if the image was downloaded, False otherwise
        """

        # Check if the scraper can continue execution
        if not self._check_scraper_usable():
            return False

        # Browse the user's profile
        self._driver.get(PROFILE_URL.format(fb_profile.username))
        time.sleep(SLEEP_TIME_MEDIUM)
        self._request_manager()

        # Get the profile picture
        try:
            wait = WebDriverWait(self._driver, self._timeout)
            profile_image = wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, PROFILE_PHOTO_CLASSNAME)))
        except TimeoutException:
            self._logger.debug(
                'User {} does not have a profile photo'.format(
                    fb_profile.username))
            return False
        except Exception as ex:
            self._manage_error(WEBDRIVER_GENERIC_ERROR, ex)
            return False

        # Gets the URL of the image
        url = profile_image.get_attribute('src')

        # Download the image
        return self._image_download(url, save_path)

    def download_profile_images(
            self, fb_profile: Type['classes.profiles.facebook_profile'], save_dir: str, max_photo: int = 30) -> bool:
        """Download the Facebook profile pictures

        You must be logged in

        Parameters
        ----------
        fb_profile: facebook_profile
            Facebook profile to download the images from
        save_dir: str
            Image saving directory
        max_photo: int
            Maximum number of photos to download
            Default 30

                Return
        ------
        bool
            True if the images have been downloaded, False otherwise
        """

        # Local variables
        url_images = []

        # Check if the scraper can continue execution
        if not self._check_scraper_usable():
            return False

        # Create the folder if needed
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Get links to images
        url_images = self._get_photos_URL(fb_profile.username)

        # Limit the number of photos to download
        if len(url_images) > max_photo:
            url_images = url_images[:max_photo]

        # Download images with the format 'username_index.jpg'
        index = 0
        for url in url_images:
            abs_dir = os.path.abspath(save_dir)
            save_path = os.path.join(
                abs_dir, '{}_{}.jpg'.format(fb_profile.username, index))
            self._image_download(url, save_path)
            time.sleep(SLEEP_TIME_SHORT)
            index += 1

        return True
