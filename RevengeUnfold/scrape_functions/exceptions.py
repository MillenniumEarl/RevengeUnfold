# Exception definition
class WebDriverNotInitialized(Exception):
    pass

class UserNotLogged(Exception):
    pass

class FacebookAccountBlocked(Exception):
    pass

class TooManyRequests(Exception):
    pass

class NoProfilePhoto(Exception):
    pass

class UnexpectedURLValue(Exception):
    pass
