############### External Modules Imports ###############
import photohash

############### Local Modules Imports ###############
from classes import profiles

# Global constants
NAME_MIN_LENGHT = 4
MIN_MATCH_THREESHOLD = 5

class person:
    """
    Class used to keep information about a person's social profiles
    
    Attributes
    ----------
    id : int
        Unique identifier of the person 
    first_name : str
        Name of the person
    last_name : str
        Surname of the person
    phones : list
        List of phones (classes.phone) associated with the person
    locations : list
        List of places (classes.location) visited by the person
    profiles : list
        List of social profiles (classes.profiles) associated with the person
    face_encodings : list
        List of face encodings (128-d) associated with the person
    perceptual_hashes : list
        List of perceptual hashes (str) identifying the images on the person's social profiles

    Methods
    -------
    add_profile(profile)
        Associate a social profile (classes.profiles) to the person
    find_facebook_profile(fb_scraper, *custom_keywords)
        Find the Facebook profile possibly belonging to the person
    find_instagram_profile(ig_scraper, *custom_keywords)
        Find the Instagram profile possibly belonging to the person
    find_telegram_profile()
        Find the Telegram profile possibly belonging to the person
    find_twitter_profile(tw_scraper, *custom_keywords)
        Find the Twitter profile possibly belonging to the person
    get_full_name()
        Gets the full name of the person regardless of null fields
    get_identifiability()
        It obtains an index of identifiability of the person on social networks
    get_profiles(platform=None)
        Get the social profiles associated with the person
    print_info()
        Print information about the person and his social profiles
    """
    def __init__(self, person_id: int):
        """
        Parameters
        ----------
        person_id : int
            Unique identifier of the person
        """
        self.id = person_id
        self.first_name = None
        self.last_name = None
        self.phones = []
        self.locations = []
        self.profiles = []
        self.face_encodings = []
        self.perceptual_hashes = []

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d

    def _prepare_search_data(self, custom_keywords:list = None):
        '''Collects the data associated with the user profile and creates a list of usernames and keywords to be used in the search for profiles

        Parameters
        ----------
        custom_keywords : list, optional
            List of additional keywords (str) to be used in the search

        Return
        ------
        dict
            'usernames_list': List of usernames
            'keywords_list': List of keyword
        '''

        # Local variables
        keywords = []

        # Prepare the social profiles associated with the user for comparison
        unready_profiles = [p for p in self.profiles if not p.is_elaborated]
        for p in unready_profiles:
            p.elaborate_images()

        # Get unique usernames from the social profiles associated with the user
        usernames_list = list({p.username for p in self.profiles if p.username is not None}) # Set comprehension

        # Create a list of unique tuples with first and last name of the associated profiles and the person
        keywords_tuple_list = [(p.first_name, p.last_name) for p in self.profiles]
        keywords_tuple_list.append((self.first_name, self.last_name))
        keywords_tuple_list = list({t for t in keywords_tuple_list})  # Set comprehension

        # Combine additional keywords into one value
        if custom_keywords is None: custom_keywords = []
        extra_keywords = ' '.join([str(k) for k in custom_keywords])

        # Compile a list of keywords with which to search for similar profiles
        for tup in keywords_tuple_list:
            first_name = tup[0]
            last_name = tup[1]

            # If the first or last name is null, the search will most likely give false positives
            if first_name is None or last_name is None:
                continue

            # If name or surname are few characters long they are most likely fake
            if len(first_name) < NAME_MIN_LENGHT or len(last_name) < NAME_MIN_LENGHT:
                continue

            # Verify that no duplicates have been added to the list of keywords (names and surnames reversed for example)
            if '{} {}'.format(first_name, last_name) in keywords or '{} {}'.format(last_name, first_name) in keywords:
                continue

            # If all the conditions are verified, add the keyword
            keywords.append('{} {} {}'.format(first_name, last_name, extra_keywords).strip())

        return {'usernames_list': usernames_list, 'keywords_list': keywords}

    def add_profile(self, profile):
        '''Add a social profile to the list of profiles associated with the user

        Parameters
        ----------
        profile: classes.profiles
            Social profile to associate
        '''

        # Add profile data to the person (verify that first and last name do not contain numbers)
        if self.first_name is None and profile.first_name is not None:
            if len(profile.first_name) >= NAME_MIN_LENGHT and not any(map(str.isdigit, profile.first_name)):
                self.first_name = profile.first_name
        if self.last_name is None and profile.last_name is not None:
            if len(profile.last_name) >= NAME_MIN_LENGHT and not any(map(str.isdigit, profile.last_name)):
                self.last_name = profile.last_name

        if profile.phone is not None:
            self.phones.append(profile.phone)

        # Add the places the person visited
        self.locations.extend(profile.locations)

        # Add new faces encodings
        # TODO: Check if face is already in list
        self.face_encodings.extend(profile._face_encodings)

        # Add hashes of new images
        for new_hash in profile._perceptual_hashes:
            for cmp_hash in self.perceptual_hashes:
                if photohash.hashes_are_similar(cmp_hash, new_hash):
                    self.perceptual_hashes.append(new_hash)
                    break

        # Sort the list from the most recent to the least recent location
        if len(profile.locations) > 0:
            self.locations.sort(key=lambda loc: loc.time, reverse=True)

        # Add social profile
        self.profiles.append(profile)

    def find_facebook_profile(self, fb_scraper, *custom_keywords):
        '''Based on the person's data, search for the person's Facebook profile

        Parameters
        ----------
        fb_scraper: scrape_functions.fb_scraper
            Instance of scrape_functions.fb_scraper used to search for users
        custom_keywords: args
            List of additional keywords to be used in the search

        Return
        ------
        int
            Best match value (if it is 0, no profile was found)
        '''

        # Local variables
        possibile_profiles = []

        # Get the data to use in the search
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Search user by keywords, it is useless to search by username because it is defined by Facebook and not by the person
        keywords = search_data['keywords_list']
        keywords.extend(search_data['usernames_list'])
        list(set(keywords))

        for keyword in keywords:
            ps = fb_scraper.find_user_by_keywords(keyword)
            possibile_profiles.extend(ps)

        # Filter profiles (redundant searches)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # Profiles are prepared for comparison
        # In the loop it also performs the comparison between the possible Facebook profiles and the profiles already present for the profile
        # (the sum of all comparisons is calculated).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for fbp in possibile_profiles:
            fbp.elaborate_images(fb_scraper)

            # Perform comparisons and possibly save the profile
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(fbp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = fbp

        # Once the comparisons are finished, add the best profile (if it has been found)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        return 0

    def find_instagram_profile(self, ig_scraper, *custom_keywords):
        '''Based on the person's data, search for the person's Instagram profile

        Parameters
        ----------
        ig_scraper: scrape_functions.ig_scraper
            Instance of scrape_functions.ig_scraper used to search for users
        custom_keywords: args
            List of additional keywords to be used in the search

        Return
        ------
        int
            Best match value (if it is 0, no profile was found)
        '''

        # Local variables
        possibile_profiles = []

        # Gets the data to be used in the search
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Search for usernames
        for username in search_data['usernames_list']:
            p = ig_scraper.find_user_by_username(username)
            if p is not None:
                possibile_profiles.append(p)

        # Search for keywords
        for keyword in search_data['keywords_list']:
            ig_profiles = ig_scraper.find_user_by_keywords(keyword)
            possibile_profiles.extend(ig_profiles)

        # Filter profiles (redundant searches)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # Once the possible profiles have been identified, it compares the possible Instagram profiles 
        # with the profiles already present for the profile (the sum of all the comparisons is calculated).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for pp in possibile_profiles:
            pp.elaborate_images(ig_scraper)

            # Perform comparisons and possibly save the profile
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(pp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = pp

        # Once the comparisons are finished, add the best profile (if it has been found)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        return 0

    def find_telegram_profile(self):
        '''Based on the person's data, search for the person's Telegram profile

        Return
        ------
        int
            Best match value (if it is 0, no profile was found)
        '''
        # TODO
        print()

    def find_twitter_profile(self, tw_scraper, *custom_keywords):
        '''Based on the person's data, search for the person's Twitter profile

        Parameters
        ----------
        tw_scraper: scrape_functions.tw_scraper
            Instance of scrape_functions.tw_scraper used to search for users
        custom_keywords: args
            List of additional keywords to be used in the search

        Return
        ------
        int
            Best match value (if it is 0, no profile was found)
        '''

        # Local variables
        possibile_profiles = []

        # Gets the data to be used in the search
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Search for usernames
        for username in search_data['usernames_list']:
            p = tw_scraper.find_user_by_username(username)
            if p is not None:
                possibile_profiles.append(p)

        # Search for keywords
        for keyword in search_data['keywords_list']:
            tw_profiles = tw_scraper.find_user_by_keywords(keyword)
            possibile_profiles.extend(tw_profiles)

        # Filter profiles (redundant searches)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # Once the possible profiles have been identified, it compares the possible Twitter profiles 
        # with the profiles already present for the profile (the sum of all the comparisons is calculated).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for twp in possibile_profiles:
            twp.elaborate_images(tw_scraper)

            # Perform comparisons and possibly save the profile
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(twp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = twp

        # Once the comparisons are finished, add the best profile (if it has been found)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        return 0

    def get_full_name(self):
        '''Get the person's full name checking for None values

        Return
        ------
        str
            Full name without 'None' in the string
        '''

        fullname = '{} {}'.format(self.first_name, self.last_name)
        return fullname.replace('None','').strip()

    def get_identifiability(self):
        """ It obtains an index of identifiability of the person's social profiles based on the known data

        Return
        ------
        int
            Traceability index of the person on social networks
        """

        # Local variables
        identifiability = 0

        if self.first_name is not None:
            identifiability += 1
        if self.last_name is not None:
            identifiability += 1
        identifiability += len(self.phones)
        identifiability += len(self.face_encodings)
        identifiability += len(self.perceptual_hashes)

        return identifiability

    def get_profiles(self, platform:str=None):
        """Return the social profiles associated with the person

        Parameters
        ----------
        platform: str, optional
            If specified, returns the profiles of that specific platform, otherwise all associated profiles

        Return
        ------
        list
            List of social profiles (classes.profiles)
        """

        if platform is None: return self.profiles
        return [profile for profile in self.profiles if profile.platform.lower() == platform.lower()]

    def print_info(self):
        """Print the information of the person and associated social profiles"""

        print('First name: {}'.format(self.first_name))
        print('Last name: {}'.format(self.last_name))

        for phone in self.phones:
            print('Phone: {} - {}, {}'.format(phone.number, phone.carrier, phone.geolocation))

        # Print the information of the social profiles
        print('Social profiles: {} ({} profiles)'.format(
            ', '.join([p.platform for p in self.get_profiles()]), 
            len(self.profiles)))

        if len(self.profiles) > 0:
            print('----------------------------------')
        for ps in self.profiles:
            ps.print_info()
            print('----------------------------------')

        # Print information on the last associated location
        if len(self.locations) > 0:
            # Sort the locations
            self.locations.sort(key=lambda loc: loc.time, reverse=True)
            print(
                'Last associated location: {} on {} ({}, {})'.format(
                    self.locations[0].name,
                    self.locations[0].time,
                    self.locations[0].latitude,
                    self.locations[0].longitude))

        # Print other informations
        print('Number of faces encoded: {}'.format(len(self.face_encodings)))
        print('Number of encoded images: {}'.format(
            len(self.perceptual_hashes)))
        print(
            'Profile identifiability index: {}'.format(
                self.get_identifiability()))