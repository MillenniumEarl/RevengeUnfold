############### Standard Imports ###############
from configparser import ConfigParser

# Credentials (Global to program)
tg_api_id = -1
tg_api_hash = ''
tg_phone = ''
ig_username = ''
ig_password = ''
fb_email = ''
fb_password = ''

def load_credential(path:str):
    """Load the credentials from a INI file

    Parameters
    ----------
    path: str
        Path to the INI file
    """

    # Instantiate parser
    config = ConfigParser()

    # Parse existing file
    config.read(path)

    # Read values from Telegram section
    global tg_api_hash, tg_api_id, tg_phone
    tg_api_id = config.getint('telegram', 'api_id')
    tg_api_hash = config.get('telegram', 'api_hash')
    tg_phone = config.get('telegram', 'phone')

    # Read values from Instagram section
    global ig_username, ig_password
    ig_username = config.get('instagram', 'username')
    ig_password = config.get('instagram', 'password')

    # Read values from Facebook section
    global fb_email, fb_password
    fb_email = config.get('facebook', 'email')
    fb_password = config.get('facebook', 'password')