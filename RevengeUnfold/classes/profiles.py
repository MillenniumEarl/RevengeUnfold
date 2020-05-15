############### Standard Imports ###############
import os
import tempfile
import shutil

############### External Modules Imports ###############
import face_recognition
import photohash

############### Local Modules Imports ###############
from classes import phone
from generic import concat
import password_manager
from scrape_functions import tg_functions


class base_profile:
    """
    Base class representing a generic social profile.
    This class should not be used.

    Attributes
    ----------
    platform : str
        Name of the platform from which the data stored in the profile comes
    user_id : int
        Unique ID of the account on the platform
    username : str
        Account username
    first_name : str
        Name of the user associated with the account
    last_name : str
        Surname of the user associated with the account
    full_name : str
        Full name (first and last name) of the user associated with the account. Used in some platforms that do not divide name and surname
    phone : classes.phone
        Data on the phone (classes.phone) associated with the account
    locations : list
        List of locations associated with the account
    is_elaborated : bool
        Value indicating whether the profile has been processed and is ready for comparison with other profiles
    """
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
        """Print profile information"""

        # Print generic information
        print('Platform: {}'.format(self.platform))
        print('User: {}'.format(self.username))
        print(
            'Identity: {} {} ({})'.format(
                self.first_name,
                self.last_name,
                self.full_name))

        # Print phone info
        if self.phone is None:
            print('No phone associated')
        else:
            print('Associated phone: {} - {}, {}'.format(self.phone.number,
                                                           self.phone.carrier, self.phone.geolocation))

        # Print information on the last visited location
        if len(self.locations) > 0:
            # Sort the locations
            self.locations.sort(key=lambda loc: loc.time, reverse=True)
            print(
                'Last visited location: {} on {} ({}, {})'.format(
                    self.locations[0].name,
                    self.locations[0].time,
                    self.locations[0].latitude,
                    self.locations[0].longitude))

    def compare_profile(self, profile:base_profile):
        """Compare the profile with another profile to see if they belong to the same person

        Compare the profile with the one passed as a parameter and compare the general information, 
        the phone data, the locations visited, the correspondence of faces in the photos associated 
        with the profiles and the similarities of the images through perceptual hashes

        Parameters
        ----------
        profile : base_profile
            Profile derived from base_profile to be compared to the current profile

        Return
        ------
        int
            Accuracy value between profiles, the higher the greater the similarity
        """

        # Local variables
        match = 0

        # Compare profile data
        if self.username is not None and profile.username is not None:
            if self.username == profile.username:
                match += 1

        if self.phone is not None and profile.phone is not None:
            if self.phone.number == profile.phone.number:
                match += 1

        # Gets the normalized full name of the current profile
        this_fullname = self.full_name.lower() if self.full_name is not None else concat(self.first_name, self.last_name).lower()

        # Gets the normalized full name of the compared profile
        profile_fullname = profile.full_name.lower() if profile.full_name is not None else concat(profile.first_name, profile.last_name).lower()

        if this_fullname in profile_fullname or profile_fullname in this_fullname:
            match += 1

        # Compare the places visited
        for loc in self.locations:
            for cmp_loc in profile.locations:
                if loc == cmp_loc:
                    match += 1

        # Compare the faces in the images associated with the profiles
        if len(self._face_encodings) > 0:
            for face_encoding in profile._face_encodings:
                results = face_recognition.compare_faces(
                    self._face_encodings, face_encoding)
                match += results.count(True)

        # Compare hash images to identify similar ones
        for cmp_hash in self._perceptual_hashes:
            for new_hash in profile._perceptual_hashes:
                if photohash.hashes_are_similar(cmp_hash, new_hash):
                    match += 1

        return match

    def _find_faces_profile_photos(self, image_dir:str):
        """Identify the faces in the images located in the folder passed by parameter and encode them for face recognition

        Parameters
        ----------
        image_dir: str
            Path to the image directory
        """

        # Gets the list of images in the folder
        dir_abs_path = os.path.abspath(image_dir)
        images_list = [os.path.join(dir_abs_path, name) for name in os.listdir(
            dir_abs_path) if os.path.isfile(os.path.join(dir_abs_path, name))]

        for image_path in images_list:
            # Check if the image is valid, otherwise delete it
            try:
                image = face_recognition.load_image_file(image_path)
            except BaseException:
                os.remove(image_path)
                continue

            # Process faces
            face_encodings = face_recognition.face_encodings(image)
            if len(face_encodings) == 0:
                continue  # No faces identified
            else:
                self._face_encodings.extend(face_encodings)

    def _elaborate_perceptual_hash_media(self, image_dir:str):
        """Processes the perceptual hashes for the images in the folder passed by parameter

        Parameters
        ----------
        image_dir: str
            Path to the image directory
        """

        # Ottiene l'elenco di immagini presenti nella cartella
        dir_abs_path = os.path.abspath(image_dir)
        images_list = [os.path.join(dir_abs_path, name) for name in os.listdir(
            dir_abs_path) if os.path.isfile(os.path.join(dir_abs_path, name))]

        # Process hashes of images
        for image_path in images_list:
            image_hash = photohash.average_hash(image_path)
            if not image_hash in self._perceptual_hashes:  # Avoid adding doubles
                self._perceptual_hashes.append(image_hash)


class telegram_profile(base_profile):
    """
    Class representing a Telegram account. 
    Derived from base_profile.

    Attributes
    ----------
    platform: str
        Name of the platform: Telegram
    """
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Telegram'
        self._tg_profile = None

    def get_profile_from_tg_profile(self, tg_profile:tg_functions.TelegramClient):
        """Given a Telegram profile fill in the fields of the current profile

        Parameters
        ----------
        tg_profile: tg_functions.TelegramClient (telethon.sync.TelegramClient)
            Telegram client (Telethon) from which to extrapolate the data

        Return
        ------
        bool
            True if the operation is successful, False otherwise
        """

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

    def get_profile_from_userid(self, userid:int, tg_client:tg_functions.TelegramClient=None):
        """Gets the data of a Telegram profile starting from the ID of that profile

        Parameters
        ----------
        userid: int
            ID of the Telegram user
        tg_client: tg_functions.TelegramClient (telethon.sync.TelegramClient), optional
            Telegram client (Telethon) from which to extrapolate the data. If not specified, a new one is instantiated

        Return
        ------
        bool
            False if the ID does not exist
            True if the operation is successful
        """

        # Search for the profile on Telegram
        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                profile = tg_functions.get_profiles(tg_client_internal, id)
        else:
            profile = tg_functions.get_profiles(tg_client, userid)
        if profile is None:
            return False  # If the profile corresponding to the indicated data does not exist, return False
        else:
            return self.get_profile_from_tg_profile(profile)

    def get_profile_from_username(self, username:str, tg_client:tg_functions.TelegramClient=None):
        """Gets the data of a Telegram profile starting from the username of that profile

        Parameters
        ----------
        username: str
            Username (@user) of the Telegram user
        tg_client: tg_functions.TelegramClient (telethon.sync.TelegramClient), optional
            Telegram client (Telethon) from which to extrapolate the data. If not specified, a new one is instantiated

        Return
        ------
        bool
            False if the username does not exist
            True if the operation is successful
        """

        # Search for the profile on Telegram
        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                profile = tg_functions.get_profiles(tg_client_internal, username)
        else: profile = tg_functions.get_profiles(tg_client, username)
        if profile is None: return False  # If the profile corresponding to the indicated data does not exist, return False
        
        return self.get_profile_from_tg_profile(profile)

    def download_profile_photos(self, save_dir:str, tg_client:tg_functions.TelegramClient=None):
        """Save user profile images (if any)
        
        Parameters
        ----------
        save_dir: str
            Image saving folder
        tg_client: tg_functions.TelegramClient (telethon.sync.TelegramClient), optional
            Telegram client (Telethon) from which to extrapolate the data. If not specified, a new one is instantiated
        
        Return
        ------
        bool
            False if the current profile has no user id associated
            True if the operation is successful
        """

        if self._tg_profile is None:
            if self.user_id is None: return False
            self.get_profile_from_userid(self.user_id, tg_client)

        # Create the folder if it doesn't exist
        save_dir = os.path.abspath(save_dir)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if tg_client is None:
            with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client_internal:
                tg_functions.download_users_profile_photos(tg_client_internal, self._tg_profile, save_dir)
        else:
            tg_functions.download_users_profile_photos(tg_client, self._tg_profile, save_dir)

        return True

    def elaborate_images(self, image_dir:str=None, tg_client:tg_functions.TelegramClient=None):
        """Download and process the images associated with the profile to identify faces and hashes of the images

        Parameters
        ----------
        image_dir: str, optional
            Path to the image directory (if not specified, a temporary one will be used)
            Default None
        tg_client: tg_functions.TelegramClient (telethon.sync.TelegramClient), optional
            Telegram client (Telethon) from which to extrapolate the data. If not specified, a new one is instantiated

        Return
        ------
        bool
            False if the user has no profile pictures
            True if the operation is successful
        """

        # Local variables
        use_temp_dir = False

        # Check the parameters
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Create a temporary folder
        else:
            image_dir = os.path.abspath(image_dir)

        # Check if there are images and download them, otherwise end the function
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_profile_photos(image_dir, tg_client) is False:
                return False

        # Process images in search of faces
        self._find_faces_profile_photos(image_dir)

        # Process images to obtain perceptual hashes
        self._elaborate_perceptual_hash_media(image_dir)

        # Delete the temporary folder used
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True


class instagram_profile(base_profile):
    """
    Class representing an Istagram account. 
    Derived from base_profile.

    Attributes
    ----------
    platform: str
        Name of the platform: Instagram
    biography: str
        User biography
    is_private: bool
        True if the Instagram account is private
    """
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Instagram'
        self._ig_profile = None
        self.biography = None
        self.is_private = None

    def get_profile_from_username(self, ig_scraper, username:str):
        """Gets the data of a Instagram profile starting from the username of that profile

        Overwrites data previously saved in the calling profile.

        Parameters
        ----------
        ig_scraper: scrape_functions.ig_functions.ig_scraper
            Instagram scraper used to get profile data
        username: str
            Username of the Instagram user

        Return
        ------
        bool
            False if the username does not exist
            True if the operation is successful
        """

        # Look for the profile on Instagram
        profile = ig_scraper.find_user_by_username(username)

        if profile is None:
            return False  # If the profile corresponding to the indicated data does not exist, False returns
        else:
            self.__dict__.update(profile.__dict__)
            return True

    def download_photos(self, ig_scraper, save_dir:str):
        """Save user post' images (if any)
        
        Parameters
        ----------
        ig_scraper: scrape_functions.ig_functions.ig_scraper
            Instagram scraper used to get profile data
        save_dir: str
            Image saving folder
        
        Return
        ------
        bool
            False if the current profile has no Instagram username associated
            True if the operation is successful
        """

        if self._ig_profile is None:
            if self.username is None: return False
            self.get_profile_from_username(ig_scraper, self.username)

        # Create the folder if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        ig_scraper.download_profile_photo(self._ig_profile, save_dir)
        ig_scraper.download_post_images(self._ig_profile, save_dir)

        return True

    def elaborate_images(self, ig_scraper, image_dir:str=None):
        """Download and process the images associated with the profile to identify faces and hashes of the images

        Parameters
        ----------
        ig_scraper: scrape_functions.ig_functions.ig_scraper
            Instagram scraper used to get profile data
        image_dir: str, optional
            Path to the image directory (if not specified, a temporary one will be used)
            Default None

        Return
        ------
        bool
            False if the user has no profile pictures
            True if the operation is successful
        """

        # Local variables
        use_temp_dir = False

        # Check the parameters
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Create a temporary folder
        else:
            image_dir = os.path.abspath(image_dir)

        # Check if there are images and download them, otherwise end the function
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(ig_scraper, image_dir) is False:
                return False

        # Process images in search of faces
        self._find_faces_profile_photos(image_dir)

        # Process images to obtain perceptual hashes
        self._elaborate_perceptual_hash_media(image_dir)

        # Delete the temporary folder used
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True

    def get_locations_history(self, ig_scraper):
        """Gets the places visited by the user

        Get all post geotags for a specific Instagram profile and from those all the places visited by the user.
        You need to be logged in Instagram to use this function.

        Parameters
        ----------
        ig_scraper: scrape_functions.ig_functions.ig_scraper
            Logged Instagram scraper used to get profile data

        Return
        ------
        bool
            True if the operation is successful, False otherwise
        """

        # A *non* anonymous connection is required
        if self._ig_profile is None or not ig_scraper.is_logged:
            return False

        location_history = ig_scraper.get_location_history(self._ig_profile)
        self.locations.extend(location_history)

        return True


class facebook_profile(base_profile):
    """
    Class representing a Facebook account. 
    Derived from base_profile.

    Attributes
    ----------
    platform: str
        Name of the platform: Facebook
    biography: str
        User biography
    """
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Facebook'
        self.biography = None

    def get_profile_from_username(self, fb_scraper, username:str):
        """Gets the data of a Facebook profile starting from the username of that profile

        Overwrites data previously saved in the calling profile.

        Parameters
        ----------
        fb_scraper: scrape_functions.fb_functions.fb_scraper
            Facebook scraper used to get profile data
        username: str
            Username of the Facebook user

        Return
        ------
        bool
            False if the username does not exist
            True if the operation is successful
        """

        if not fb_scraper.is_logged:
            return False

        # Search for the profile on Facebook
        profile = fb_scraper.find_user_by_username(username)

        # The profile does not exist
        if profile is None: return False
        
        # Update profile
        self.__dict__.update(profile.__dict__)
        return True

    def download_photos(self, fb_scraper, save_dir:str):
        """Save user post' images (if any)
        
        Parameters
        ----------
        fb_scraper: scrape_functions.fb_functions.fb_scraper
            Facebook scraper used to get profile data
        save_dir: str
            Image saving folder
        
        Return
        ------
        bool
            False if the current profile has no Facebook username associated
            True if the operation is successful
        """

        if self.username is None or not fb_scraper.is_logged:
            return False

        # Create the folder if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        fb_scraper.download_profile_images(self, save_dir)
        fb_scraper.download_profile_photo(
            self, os.path.join(save_dir, 'profile.jpg'))
        return True

    def elaborate_images(self, fb_scraper, image_dir:str=None):
        """Download and process the images associated with the profile to identify faces and hashes of the images

        Parameters
        ----------
        fb_scraper: scrape_functions.fb_functions.fb_scraper
            Facebook scraper used to get profile data
        image_dir: str, optional
            Path to the image directory (if not specified, a temporary one will be used)
            Default None

        Return
        ------
        bool
            False if the user has no profile pictures
            True if the operation is successful
        """

        # Local variables
        use_temp_dir = False

        # Check the parameters
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Create a temporary folder
        else:
            image_dir = os.path.abspath(image_dir)

        # Check if there are images and download them, otherwise end the function
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(fb_scraper, image_dir) is False:
                return False

        # Process images in search of faces
        self._find_faces_profile_photos(image_dir)

        # Process images to obtain perceptual hashes
        self._elaborate_perceptual_hash_media(image_dir)

        # Delete the temporary folder used
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True


class twitter_profile(base_profile):
    """
    Class representing a Twitter account. 
    Derived from base_profile.

    Attributes
    ----------
    platform: str
        Name of the platform: Twitter
    biography: str
        User biography
    """
    def __init__(self):
        base_profile.__init__(self)
        self.platform = 'Twitter'
        self.biography = None

    def get_profile_from_username(self, tw_scraper, username:str):
        """Gets the data of a Twitter profile starting from the username of that profile

        Overwrites data previously saved in the calling profile.

        Parameters
        ----------
        tw_scraper: scrape_functions.tw_functions.tw_scraper
            Twitter scraper used to get profile data
        username: str
            Username of the Facebook user

        Return
        ------
        bool
            False if the username does not exist
            True if the operation is successful
        """

        if not tw_scraper.is_initialized:
            return False

        # Search for the profile on Twtter
        profile = tw_scraper.find_user_by_username(username)

        # The profile does not exist
        if profile is None: return False
        
        # Update profile
        self.__dict__.update(profile.__dict__)
        return True     

    def download_photos(self, tw_scraper, save_dir:str):
        """Save the last six photos posted and profile photo
        
        Parameters
        ----------
        tw_scraper: scrape_functions.tw_functions.tw_scraper
            Twitter scraper used to get profile data
        save_dir: str
            Image saving folder
        
        Return
        ------
        bool
            False if the current profile has no Twitter username associated
            True if the operation is successful
        """

        if self.username is None or not tw_scraper.is_initialized:
            return False

        # Create the folder if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        tw_scraper.download_profile_images(self, save_dir)
        tw_scraper.download_profile_photo(
            self, os.path.join(save_dir, '{}_profile.jpg'.format(self.username)))
        return True

    def elaborate_images(self, tw_scraper, image_dir:str=None):
        """Download and process the images associated with the profile to identify faces and hashes of the images

        Parameters
        ----------
        tw_scraper: scrape_functions.tw_functions.tw_scraper
            Twitter scraper used to get profile data
        image_dir: str, optional
            Path to the image directory (if not specified, a temporary one will be used)
            Default None

        Return
        ------
        bool
            False if the user has no profile pictures
            True if the operation is successful
        """

        # Local variables
        use_temp_dir = False

        # Check the parameters
        if image_dir is None:
            use_temp_dir = True
            image_dir = tempfile.mkdtemp()  # Create a temporary folder
        else:
            image_dir = os.path.abspath(image_dir)

        # Check if there are images and download them, otherwise end the function
        n_images = len([os.path.join(image_dir, name) for name in os.listdir(
            image_dir) if os.path.isfile(os.path.join(image_dir, name))])
        if n_images == 0:
            if self.download_photos(tw_scraper, image_dir) is False:
                return False

        # Process images in search of faces
        self._find_faces_profile_photos(image_dir)

        # Process images to obtain perceptual hashes
        self._elaborate_perceptual_hash_media(image_dir)

        # Delete the temporary folder used
        if use_temp_dir:
            shutil.rmtree(image_dir)
        self.is_elaborated = True
        return True
