# RevengeUnfold
[![DeepSource](https://static.deepsource.io/deepsource-badge-light-mini.svg)](https://deepsource.io/gh/MillenniumEarl/RevengeUnfold/?ref=repository-badge)
[![Code Quality Score](https://www.code-inspector.com/project/9565/score/svg)](https://frontend.code-inspector.com/public/project/9565/RevengeUnfold/dashboard)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FMillenniumEarl%2FRevengeUnfold.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FMillenniumEarl%2FRevengeUnfold?ref=badge_shield)
[![Known Vulnerabilities](https://snyk.io/test/github/MillenniumEarl/RevengeUnfold/badge.svg?targetFile=RevengeUnfold/requirements.txt)](https://snyk.io/test/github/MillenniumEarl/RevengeUnfold?targetFile=RevengeUnfold/requirements.txt)

At the beginning of April 2020, a network of Telegram groups and channels [was discovered in Italy](https://www.repubblica.it/tecnologia/social-network/2020/04/04/news/revenge_porn_e_pedopornografia_telegram_e_diventato_il_far_west_dell_abuso_su_ex_partner_e_minori-253126954/), with about 50,000 members, who shared child pornography and intimate photos/videos of former partners (RevengePorn).

This network, reported to law enforcement by more and more people, saw the entry into the field of LulzSecIta and Anonymous Italy in an attempt to stem the problem and identify the main perpetrators. During the _#RevengeGram_ operation, carried out by the two collectives (assisted by other minor groups), dozens of participants from the main groups of the network were traced.

At the end of April 2020 and as part of the _"Drop the Revenge"_ operation, the Postal and Communications Police Service made [three arrests of administrators](https://www.osservatoreitalia.eu/revenge-porn-denunciati-gli-amministratori-dei-canali-telegram-la-bibbia-5-0-e-stupro-tua-sorella-2-0/) of the main groups in the network.

## Why this program
I started writing this application around April 5th with the aim of identifying participants in one of the main groups.
Unlike the collective LulzSecIta and Anonymous Italia, which mainly used phishing and social engineering attacks, this program tries to associate with each participant of the Telegram group the Facebook, Instagram and Twitter accounts (and perhaps in the future also other platforms) that potentially can belong to the same person.

This, at least theoretically, allows you to automate the search process and identify many more users than manual search, allowing you to manually verify only the potentially identified profiles.
Unfortunately, there is an abyss between theory and practice. I had not taken into account the various limits of the various platforms and therefore more than checking profiles I found myself arguing with Facebook (_"Curse you, Cambridge Analytical!"_) and with the recognition algorithms.

Although not everything went according to plan, I have at least managed to put in place a system that works (more or less) and is able to find a person's accounts from the account of another platform or from data entered manually by the user.

## Functionality
- Get information about a person's social profiles
- Given a social profile, find the profiles of the same person on other platforms
- Find information about a person's phone numbers
- Find information about where a person has been

## How does it works
Speaking for this specific case (although we can then extend the idea), the application:
1. Identify all the participants in a specific Telegram group
2. Gets the available data of the participants (name, surname, telephone, profile pictures)
3. Look on the other platforms for profiles that correspond to the data identified
4. For each of the profiles identified on these platforms, the basic data (name, surname ...) are compared and, when available, the images through facial recognition and [perceptual hash](https://en.wikipedia.org/wiki/Perceptual_hashing)
5. All the profiles found are then associated with a 'person' entity which contains all the data available for a specific group participant

## How to use
### Installation
All the required modules are present in the `requirements.txt` file and you can install them using `pip install -r requirements.txt`.
Before installing the requirements, however, you must install cmake with the `pip install cmake` command. 
This will then allow the installation of dlib from the application requirements.

_Note_: It may take a long time

This application has been successfully tested with Python 3.8.2 on Windows 10 1909 (build 18363.778)
Developed with Visual Studio Community 2019 16.5.4
### Configure Telegram
The application uses [Telethon](https://github.com/LonamiWebs/Telethon) which, in order to function, requires access to the Telegram API, configurable by following [these](https://core.telegram.org/api/obtaining_api_id) indications. Once this is done we will need:
- API ID
- API Hash
- Telephone number (international format +1 234 567 8900)

Remember to join (in the Telegram app) the group you want to analyze!

### Set credentials
To use the application you need the following data, written in an INI file called `credentials.ini` and located in the __same execution folder of the program__ (together with `main.py`):
```
[telegram]
api_id = 0123456
api_hash = hash_here
phone = +12345678900

[instagram]
username = this_is_my_instagram_username
password = this_is_my_instagram_password

[facebook]
email = this_is_my_facebook_email
password = this_is_my_facebook_password
```

### Run script
The project contains both the individual modules for platform scraping and the actual application that uses them. It can be used with a graphical CLI (there is no version usable with parameters) via `python3 main.py` or` python main.py`.

## Important information here!
- Despite the possibility, __do not use any type of proxy__: they slow down the whole process and are the fastest way to get blocked by Facebook
- __Telegram__: You can only scrape groups, not channels (unless you are an administrator for that channel)
- __Facebook__: You are warned, being blocked on facebook is damn quick.
  - If you are blocked or put on hold, __do not restart the program to avoid resetting the request counters__ (although there is a system to prevent this eventuality)
  - Account:
    - If you are using your main account: your friends' profiles may end up in searches. You are warned
    - You should use your primary account (or at least a __account with a verified phone number__). Why? In the event of blocking, the entire account would not be blocked but only the [functionality](https://www.facebook.com/help/116393198446749). _Be careful not to get blocked too many times, you risk increasing the functionality blocking time_.
    - __Tip: do not use this option__: If you are using a profile with no associated phone number and you are blocked, you will need to request the unlock of the account by __sending a photo of a document that verifies your identity__. This procedure will be done manually so it may take some time and in the meantime you won't be able to use Facebook. Fantastic.
  - _For developers_: I set a limit of Facebook pages visited/requests for images equal to 200 requests per hour, with an automatic waiting system. The blockage comes the same but after a long time. To prevent the program from being closed and reopened in the event of a wait (which could lead to an account ban), a `session.fb_scraper` file is saved which saves data on requests made.
- __Instagram__: Instagram scraping is based on [instaloader](https://github.com/instaloader/instaloader) which implements its own internal method to manage requests. Do not force this system by closing and reopening the program in case of waiting!

## TODO
- [ ] Rewrite code for `tg_scraper`
- [ ] Convert comments from Italian to English
- [ ] Add missing comments
- [ ] Complete `scrape_attack.py` (Phishing code) 
- [ ] Clenup code

## Contributing
This is the first public project that I develop and I have tried to make the code as comprehensible as possible. If anyone wants to modify, optimize or improve the code, they are welcome!
I also realize that the project is relatively vast and touches several platforms. I do not guarantee it but I will try, in my spare time from university, to write a wiki documenting the code. 
For now I will try to translate the comments from Italian to English (at the beginning I didn't think I would share it :grimacing:)
