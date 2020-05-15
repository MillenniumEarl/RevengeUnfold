############### External Modules Imports ###############
from fp.fp import FreeProxy

class proxy:
    """Wrapper class that can be used to get a proxy server at run-time

    Attributes
    ----------
    proxy: str
        Proxy selected in the format IP:PORT
    country_code_list: list
        List of international prefixes ('IT', 'FR', 'US', 'DE', ...) corresponding to the locations of the usable proxy servers
    """
    def __init__(self, country_code_list:list=None):
        """
        Parameters
        ----------
        country_code_list: list
            List of international prefixes ('IT', 'FR', 'US', 'DE', ...) corresponding to the locations of the usable proxy servers
        """
        self.country_code_list = country_code_list
        self.proxy = None

    def get(self, rand:bool=True, max_timeout:float=2):
        """Gets a HTTP proxy server

        Parameters
        ----------
        rand: bool
            Indicates whether to take the first proxy in the list (rand = False) or to choose it randomly (rand = True).
            Default True.

        max_timeout: float
            Indicates the maximum response time of the server (in seconds). Servers with a longer timeout will be excluded from the choice.
            Default 2.

        Return
        ------
        str
            Proxy selected in the format IP:PORT or None if no proxy was found
        """

        if self.country_code_list is not None:
            self.proxy = FreeProxy(
                country_id=self.country_code_list,
                rand=rand,
                timeout=max_timeout).get()
        else:
            self.proxy = FreeProxy(rand=rand, timeout=max_timeout).get()

        if not 'http' in self.proxy: self.proxy = None
        return self.proxy
