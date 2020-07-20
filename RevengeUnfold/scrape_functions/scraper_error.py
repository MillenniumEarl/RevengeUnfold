############### Standard Imports ###############
from typing import Type


class scraper_error:
    """Wrapper class for exceptions that occur in scraping classes

    Attributes
    ----------
    error_code: int
        Error code inside the class
    ex: Exception
        Exception occurred
    ex_time: datetime
        Timestamp of the exception
    """

    def __init__(self, error_code: int, ex: Exception,
                 ex_time: Type['datetime.datetime']):
        """
        Parameters
        ----------
        error_code: int
            Error code inside the class
        ex: Exception
            Exception occurred
        ex_time: datetime
            Timestamp of the exception
        """
        self.error_code: int = error_code
        self.exception: Exception = ex
        self.time: Type['datetime.datetime'] = ex_time
