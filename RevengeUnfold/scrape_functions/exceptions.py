# Exception definition
class WebDriverNotInitialized(Exception):
    """Exception thrown when trying to use a WebDriver that has not been initialized correctly"""
    pass

class UserNotLogged(Exception):
    """Exception thrown when trying to access a protected platform without performing the authentication procedure"""
    pass

class InstagramClientBlocked(Exception):
    """Exception thrown when Instagram servers block the profile logged and used for scraping"""
    pass

class FacebookAccountBlocked(Exception):
    """Exception thrown when Facebook servers block the profile logged and used for scraping"""
    pass

class TooManyRequests(Exception):
    """Exception thrown when the maximum number of requests for the user currently logged/the current IP to the platform servers is exceeded"""
    pass

class NoProfilePhoto(Exception):
    """Exception thrown when a social profile does not have a primary profile image"""
    pass

class UnexpectedURLValue(Exception):
    """Exception thrown when trying to use a URL with an incorrect format"""
    pass
