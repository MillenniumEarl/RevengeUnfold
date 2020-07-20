############### Standard Imports ###############
import os
import datetime
import sys
from typing import Type, List

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
MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS = 'Too many requests for the anonymous Instagram client'
MESSAGE_TOO_MANY_REQUESTS_LOGGED = 'Too many. requests for the Instagram client'
MESSAGE_CLIENT_BLOCKED = 'Instagram client has been blocked, please try again in a few hours'
SESSION_FILE_NAME = 'session.ig_session'

# Manage 429 rate limit for anonymous client


def too_many_requests_hook(exctype, value, traceback):
    if exctype == ConnectionException and 'redirected to login' in str(value):
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
    """Class that represents an Instaloader instance and allows Instagram scraping

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
    terminate()
        Close the scraper and release the resources
    login_anonymously()
        It connects to Instagram without the need for credentials
    login(username, password)
        Connect to Instagram using credentials
    find_user_by_username(username)
        Find a user on Instagram using their username
    find_users_by_keywords(*keywords, max_profiles)
        Find a list of users on Instagram using keywords
    find_similar_profiles(ig_profile, max_profiles)
        Find Instagram profiles similar to the one specified
    download_post_images(ig_profile, save_dir, max_posts)
       Download the images present in the posts of an Instagram profile
    download_profile_photo(ig_profile, save_dir)
        Download the profile photo of an Instagram profile
    get_location_history(ig_profile)
       Get the location history of an Instagram profile
    """

    def __init__(self, logger: Type['logging.Logger'] = None):
        """
        Parameters
        ----------
        logger: logging.Logger
           Logger used to save events
           Default None
        """
        self._ig_client: Type[instaloader.Instaloader] = None
        self._logger: Type['logging.Logger'] = logger
        self.is_blocked: bool = False
        self.is_logged: bool = False
        self.is_initialized: bool = False
        self.errors: List[scraper_error.scraper_error] = []

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

        # Writes the message to the log file
        if self._logger is not None:
            if error_code >= 400:
                self._logger.error(message)
            else:
                self._logger.warning(message)

        # Check if the user has been blocked and end the scraping
        if error_code == TOO_MANY_ANON_REQUESTS:
            if self._logger is not None:
                self._logger.warning(
                    'Changing from anonymous client to logged client')
            self.login(
                password_manager.ig_username,
                password_manager.ig_password)
        elif error_code == TOO_MANY_REQUESTS:
            if self._logger is not None:
                self._logger.critical('Too many request, closing client...')
            self.is_blocked = True
            self.terminate()

    def _connect_instagram_client(
            self, username: str, password: str, anonymous: bool = True) -> bool:
        """Create and connect an Instagram client

        If anonymous = True the credentials will not be used (they can be any value)

        Parameters
        ----------
        username: str
            Instagram account username
        password: str
            Instagram account password
        anonymous: bool
            Connection anonymously (without credentials)
            Default True

        Return
        ------
        bool
            True if the connection was successful, False otherwise
        """

        # Create the client
        ig_client = instaloader.Instaloader(quiet=True, download_videos=False,
                                            download_comments=False, compress_json=True, max_connection_attempts=1)

        # Credentials are not specified if an anonymous client is specified
        if anonymous:
            self._ig_client = ig_client

            if self._logger is not None:
                self._logger.info('Successfully connected anonymously')
            return True

        # If there is a session file already configured it loads it
        if os.path.exists(SESSION_FILE_NAME) and not anonymous:
            ig_client.load_session_from_file(username, SESSION_FILE_NAME)
        else:
            try:
                ig_client.login(username, password)
                ig_client.save_session_to_file(SESSION_FILE_NAME)
            except Exception as ex:
                self._manage_error(LOGIN_GENERIC_ERROR, ex)
                return False

        # Test the validity of the connection
        if ig_client.test_login() is None:
            return False

        self._ig_client = ig_client
        if self._logger is not None:
            self._logger.info(
                'Successfully connected to user {}'.format(generic.only_ASCII(username)))
        return True

    def _convert_profile_from_instaloader(
            self, instaloader_profile: Type[instaloader.Profile]) -> profiles.instagram_profile:
        """Convert an Instaloader profile to a classes.profiles.instagram_profile

        Parameters
        ----------
        instaloader_profile: instaloader.Profile
            Instaloader profile to convert

        Return
        ------
        profiles.instagram_profile
            Converted profile
        """

        # Check if the client is blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests(
                MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
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

    def find_similar_profiles(
            self, ig_profile: Type[instaloader.Profile], max_profiles: int = 10) -> List[profiles.instagram_profile]:
        """Find profiles similar to the one specified

        You need to be logged in to use this function

        Parameters
        ----------
        ig_profile: instaloader.Profile
            Instaloader profile from which to find similar users
        max_profiles: int
            Maximum number of profiles to be obtained
            Deafult 10

        Return
        ------
        List
            List of similar profiles (classes.profiles.instagram_profile)
        """

        # You need to be logged in to use this function
        if not self.is_logged:
            self._manage_error(USER_NOT_LOGGED, None)
            return []

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            # Get similar profiles
            ig_profiles = ig_profile.get_similar_accounts()
            ig_profiles = [profile for profile in ig_profiles]

            # Limit the number of profiles
            if len(ig_profiles) > max_profiles:
                ig_profiles = ig_profiles[:max_profiles]

            # Convert the profiles
            converted_profiles = []
            for p in ig_profiles:
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

    def find_user_by_username(
            self, username: str) -> profiles.instagram_profile:
        """Find an Instagram profile by username

        Parameters
        ----------
        username: str
            Username of the user to be found

        Return
        ------
        profiles.instagram_profile
            Profile found (classes.profiles.instagram_profile) or None if not found
        """

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests(
                MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            profile_found = instaloader.Profile.from_username(
                self._ig_client.context, username)

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
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.find_user_by_username(username)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_LOGGED)
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return None
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return None

    def find_users_by_keywords(
            self, *keywords, max_profiles: int = 10) -> List[profiles.instagram_profile]:
        """Search for Instagram profiles based on the keywords used

        Parameters
        ----------
        keyords: tuple
            Keywords to be used in the search
        max_profiles: int
            Maximum number of profiles to be obtained
            Deafult 10

        Return
        ------
        List
            List of profiles (classes.profiles.instagram_profile) identified
        """

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests(
                MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        try:
            # Join the keywords
            keywords = [str(i) for i in keywords if i is not None]
            keyword = ' '.join(keywords).strip()
            if keyword == '':
                return []

            # Search for profiles
            results = instaloader.TopSearchResults(
                self._ig_client.context, keyword)
            ig_profiles = [profile for profile in results.get_profiles()]

            # Limit the number of profiles
            if len(ig_profiles) > max_profiles:
                ig_profiles = ig_profiles[:max_profiles]

            # Convert the profile
            converted_profiles = []
            for p in ig_profiles:
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
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.find_users_by_keywords(keywords, max_profiles)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_LOGGED)
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return []
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return []

    def download_post_images(
            self, ig_profile: Type[instaloader.Profile], save_dir: str, max_posts: int = 20) -> bool:
        """Download the images in the posts of a specified profile

        Parameters
        ----------
        ig_profile: instaloader.Profile
            Instagram profile to retrieve posts from
        save_dir: int
            Directory where to save the downloaded images
        max_posts: int
            Maximum number of images to download
            Deafult 20

        Return
        ------
        bool
            True if the images have been downloaded, False otherwise
        """

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests(
                MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        # Get the list of posts
        try:
            post_list = ig_profile.get_posts()
        except PrivateProfileNotFollowedException as ex:
            self._manage_error(PRIVATE_PROFILE_NOT_FOLLOWED, ex)
            return False
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_post_images(
                    ig_profile, save_dir, max_posts)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_LOGGED)
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(CLIENT_GENERIC_ERROR, ex)
                return None
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return False

        try:
            # Delete videos from posts
            post_list = [post for post in post_list if not post.is_video]

            # Limit the number of posts to download
            if len(post_list) > max_posts:
                post_list = post_list[:max_posts]

            # Download the photos
            post_index = 0
            for post in post_list:
                try:
                    savepath = os.path.join(
                        save_dir, '{}.jpg'.format(post_index))
                    self._ig_client.download_pic(
                        savepath, post.url, post.date_utc)
                    post_index += 1
                except Exception as ex:
                    self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return True
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_post_images(
                    ig_profile, save_dir, max_posts)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_LOGGED)
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None
            else:
                self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
                return None

    def download_profile_photo(
            self, ig_profile: Type[instaloader.Profile], save_dir: str) -> bool:
        """Download the profile photo of the specified Instagram profile

        Download the image and save it in the directory specified with the name 'profile.jpg'

        Parameters
        ----------
        ig_profile: instaloader.Profile
            Instagram profile to retrieve the profile photo
        save_dir: int
            Directory where to save the profile photo

        Return
        ------
        bool
            True if the image has been downloaded, False otherwise
        """

        # Check if the client is blocked
        global _anonymous_client_blocked
        if _anonymous_client_blocked and not self.is_logged:
            ex = exceptions.TooManyRequests(
                MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
            self._manage_error(TOO_MANY_ANON_REQUESTS, ex)

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return False

        # Get the profile photo and save it in the specified folder
        try:
            self._ig_client.download_pic(
                filename=os.path.join(save_dir, 'profile.jpg'),
                url=ig_profile.profile_pic_url,
                mtime=datetime.datetime.now())
            return True
        except ConnectionException as ex:
            if 'redirected to login' in str(ex):
                _anonymous_client_blocked = True
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_ANONYMOUS)
                self._manage_error(TOO_MANY_ANON_REQUESTS, ex)
                return self.download_profile_photo(ig_profile, save_dir)
            elif '429 Too Many Requests' in str(ex) and self.is_logged:
                ex = exceptions.TooManyRequests(
                    MESSAGE_TOO_MANY_REQUESTS_LOGGED)
                self._manage_error(TOO_MANY_REQUESTS, ex)
                return None  # TODO
            else:
                self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
                return None  # TODO
        except Exception as ex:
            self._manage_error(DOWNLOAD_IMAGE_ERROR, ex)
            return False

    def get_location_history(
            self, ig_profile: Type[instaloader.Profile]) -> List[location.location]:
        """Get all post geotags for a specific Instagram profile

        You need to be logged in to use this function
        If no location has been found or errors occur, an empty list is returned

        Parameters
        ----------
        ig_profile: instaloader.Profile
            Instagram profile to retrieve the geotags from

        Return
        ------
        List
            List of locations identified
        """

        # Local variables
        locations_list = []

        # You need to be logged in to use this function
        if not self.is_logged:
            self._manage_error(USER_NOT_LOGGED, None)
            return []

        # Check if the logged client is blocked
        if self.is_blocked:
            ex = exceptions.InstagramClientBlocked(MESSAGE_CLIENT_BLOCKED)
            self._manage_error(CLIENT_BLOCKED, ex)
            return []

        # Get the list of Instagram profile posts
        try:
            post_list = ig_profile.get_posts()
        except PrivateProfileNotFollowedException as ex:
            self._manage_error(PRIVATE_PROFILE_NOT_FOLLOWED, ex)
            return []
        except Exception as ex:
            self._manage_error(CLIENT_GENERIC_ERROR, ex)
            return []

        # Save the geotags of the selected media
        post_with_location = [
            post for post in post_list if post.location is not None]
        for post in post_with_location:
            loc = location.location()

            # Get location from coordinates
            if post.location.lat is not None and post.location.lng is not None:
                loc.from_coordinates(
                    post.location.lat,
                    post.location.lng,
                    post.date_utc)
                locations_list.append(loc)
            elif post.location.name is not None:
                loc.from_name(post.location.name, post.date_utc)
                if loc.is_valid:
                    locations_list.append(loc)

        # Sorts the list from the most recent to the least recent location
        locations_list.sort(key=lambda loc: loc.utc_time, reverse=True)

        if self._logger is not None:
            self._logger.info(
                'Found {} locations for user {}'.format(
                    len(locations_list),
                    generic.only_ASCII(ig_profile.username)))
        return locations_list

    def terminate(self):
        """Terminate the client and reinitialize the variables"""

        if not self.is_initialized:
            return

        self._ig_client.close()
        self.is_initialized = False
        self.is_logged = False
        if self._logger is not None:
            self._logger.info('ig_scraper successfully closed')

    def login_anonymously(self) -> bool:
        """Log in to Instagram anonymously

        Return
        ------
            True if the connection was successful, False otherwise
        """

        # If it is already instantiated, end the object and recreate it
        if self.is_initialized:
            self.terminate()

        if self._connect_instagram_client('', '', anonymous=True):
            self.is_initialized = True
            self.is_logged = False
            if self._logger is not None:
                self._logger.info(
                    'Anonymous Instagram client instanced correctly')
            return True
        else:
            return False

    def login(self, username: str, password: str) -> bool:
        """Log in to Instagram using your credentials

        Parameters
        ----------
        username: str
            Username of the Instagram account to connect to
        username: str
            Password of the Instagram account to connect to

        Return
        ------
        bool
            True if the connection was successful, False otherwise
        """

        # If it is already instantiated, end the object and recreate it
        if self.is_initialized:
            self.terminate()

        if self._connect_instagram_client(username, password, anonymous=False):
            self.is_initialized = True
            self.is_logged = True
            if self._logger is not None:
                self._logger.info(
                    'Instagram client correctly started (user {})'.format(generic.only_ASCII(username)))
            return True
        else:
            return False
