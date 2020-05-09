############### Standard Imports ###############
from datetime import datetime
from glob import glob
import logging
import os
import pickle
import signal
import tkinter as tk
from tkinter import filedialog

############### External Modules Imports ###############
from termcolor import colored
from tqdm import tqdm

############### Local Modules Imports ###############
from classes import profiles, person
import database
import generic
from scrape_functions import fb_functions, tg_functions, ig_functions, tw_functions
import password_manager

############### Variabili globali ###############
_terminate_program = False
_scrape_logger, _fb_logger, _ig_logger, _tg_logger, _tw_logger = (None, None, None, None, None)
_MIN_IDENTIFIABILITY_THREESHOLD = 5
_CREDENTIALS_PATH = 'credentials.ini'
_base_dir = None
_db_path = None

############### Process Interrupt Management ###############


def _end_program():
    # Mostra un messaggio all'utente
    print('\n' + colored('[SYSTEM]', 'green') +
          ' Application termination for user interruption')
    _scrape_logger.info('Application termination for user interruption')
    # Termina l'applicazione
    exit(0)


def _keyboard_interrupt_handler(rcv_signal, frame):  # noeq
    print('\n' +
          colored(
              '[SYSTEM]',
              'green') +
          ' Wait for the data to be saved and the program to end')
    _scrape_logger.info('Application termination request from the user')
    global _terminate_program
    _terminate_program = True


signal.signal(signal.SIGINT, _keyboard_interrupt_handler)

############### Base Functions Definition ###############

def _define_loggers():
    '''
    Vengono creati i logger per l'applicazione e per gli scraper
    '''

    global _scrape_logger, _fb_logger, _ig_logger, _tg_logger, _tw_logger

    # Creazione cartella dei log
    log_dir = os.path.abspath('logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Creazione logger
    today_s = datetime.now().strftime('%d_%m_%y')

    _scrape_logger = generic.create_logger(
        'scrape_logger', os.path.join(
            log_dir, f'scrape_group_{today_s}.log'))
    _scrape_logger.setLevel(logging.WARNING)

    _fb_logger = generic.create_logger(
        'facebook_logger', os.path.join(
            log_dir, f'facebook_scraper_{today_s}.log'))
    _fb_logger.setLevel(logging.WARNING)

    _ig_logger = generic.create_logger(
        'instagram_logger', os.path.join(
            log_dir, f'instagram_scraper_{today_s}.log'))
    _ig_logger.setLevel(logging.WARNING)

    _tg_logger = generic.create_logger(
        'telegram_logger', os.path.join(
            log_dir, f'telegram_scraper_{today_s}.log'))
    _tg_logger.setLevel(logging.WARNING)

    _tw_logger = generic.create_logger(
        'twitter_logger', os.path.join(
            log_dir, f'twitter_scraper_{today_s}.log'))
    _tw_logger.setLevel(logging.WARNING)


def _select_telegram_group():
    '''
    Elenca tutti i gruppi a cui l'utente sta partecipando e gli permette di selezionarne uno

    Return:
    Gruppo selezionato (Telethon entity) o None se si vuole riprendere una sessione precedente
    '''

    # Collega il client Telegram
    with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client:
        # Ottiene tutte le conversazioni a cui il profilo è connesso
        list_conversations = tg_functions.get_all_conversations(
            tg_client, only_groups=True)

    # Menu di selezione del gruppo da analizzare
    print(colored('[TELEGRAM]', 'cyan') +
          ' Selection of Telegram group to analyze:')
    i = 0
    for conv in list_conversations:
        conv_name = generic.only_ASCII(conv[0].title).strip()
        print(
            colored(
                '[',
                'red') +
            str(i) +
            colored(
                ']',
                'red') +
            ' {}'.format(conv_name))
        i += 1

    # Lascia selezionare all'utente il gruppo da analizzare
    print(
        colored(
            '[TELEGRAM]',
            'cyan') +
        ' Enter the index of the group to be analyzed: ',
        end='')  # Senza ritorno a capo per mettere l'imput sulla stessa riga
    conv_index = input()  # I colori ANSI non funzionano con input()

    target_group = list_conversations[int(conv_index - 1)][0]
    group_name = generic.only_ASCII(target_group.title).strip()
    print(colored('[TELEGRAM]', 'cyan') +
          ' Selected Telegram group: {}'.format(group_name))
    _scrape_logger.info('Selected Telegram group: {}'.format(group_name))

    return target_group


def _select_and_save_group_members(target_group, save_dir, aquired_profiles=None):
    '''
    Data una directory converte i partecipanti in un oggetto 'person'

    Params:
    @target_group: Gruppo da cui ottenere i partecipanti
    @save_dir: Directory di salvataggio dei file utente
    @aquired_profiles [None]: Lista di profili già configurati. Se specificata, viene ritornata una lista di profili comprendente quelli passati per parametro e i nuovi utenti presenti nel gruppo

    Return:
    Lista di profili (person)
    '''

    # Variabili locali
    profiles_list = []

    # Collega il client Telegram
    _scrape_logger.info('Group member acquisition...')
    print(colored('[TELEGRAM]', 'cyan') + ' Group member acquisition...')
    with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client:
        tg_group_members = tg_functions.get_group_channel_members(
            tg_client, target_group)  # --> Perchè [0]?

    print(colored('[TELEGRAM]', 'cyan') +
          ' Identified {} participants'.format(len(tg_group_members)))
    _scrape_logger.info(
        'Identified {} participants'.format(
            len(tg_group_members)))

    # Converte i profili da Telethon a profili Telegram
    # interni all'applicazione, poi li aggiunge ad una
    # entità 'person' e li salva su disco
    index = 0

    # Ottiene solo i nuovi profili aggiunti al gruppo
    if aquired_profiles is not None:
        # Ordina i profili per ottenere l'ID maggiore (+ 1 per poterlo poi
        # usare)
        index = max(profile.id for profile in aquired_profiles) + 1

        # Filtra i profili per ID
        tg_saved_members_ids = [p.get_profiles(
            'Telegram')[0].user_id for p in aquired_profiles]
        tg_group_members = [
            tg_member for tg_member in tg_group_members if tg_member.id not in tg_saved_members_ids]

        print(colored('[TELEGRAM]', 'cyan') +
              ' {} new participants identified'.format(len(tg_group_members)))

    _scrape_logger.info('Saving profiles (Telegram) ...')
    for tg_profile in tqdm(tg_group_members, colored(
            '[TELEGRAM]', 'cyan') + ' Saving Telegram profiles'):
        # Crea il profilo interno Telegram
        tgp = profiles.telegram_profile()
        tgp.get_profile_from_tg_profile(tg_profile)

        # Lo aggiunge ad una entità persona
        save_path = os.path.join(save_dir, '{}.person'.format(index))
        p = person.person(index)
        p.add_profile(tgp)
        pickle.dump(p, open(save_path, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
        profiles_list.append(p)
        index += 1

    if _terminate_program:
        _end_program()

    profiles_list.extend(aquired_profiles)
    return profiles_list


def _load_people_profiles(load_dir):
    '''
    Carica i profili utente salvati in precedenza

    Params:
    @load_dir: Directory dove sono contenuti i profili utente

    Return:
    Lista di profili (classes.person)
    '''

    # Variabili locali
    profiles_list = []

    # Ricerca tutti i file di salvataggio
    filepath_list = glob(os.path.join(load_dir, '*.person'))

    # Carica i profili
    _scrape_logger.info('Loading profiles ...')
    for filepath in tqdm(filepath_list, colored(
            '[SYSTEM]', 'green') + ' Loading profiles'):
        if _terminate_program:
            _end_program()

        p = pickle.load(open(filepath, 'rb'))
        profiles_list.append(p)

    return profiles_list


def _select_work_dir():
    '''
    Lascia selezionare all'utente la cartella di lavoro da utilizzare

    Return:
    Percorso della cartella selezionata dall'utente
    '''

    # Seleziona la cartella da cui caricare i profili
    root = tk.Tk()
    root.withdraw()

    print(colored('[SYSTEM]', 'green') + ' Press a key to select the work directory', end='')
    input()

    selected_dir = filedialog.askdirectory()

    print(colored('[SYSTEM]', 'green') + ' Selected directory: {}'.format(selected_dir))

    return selected_dir

############### Scraping Functions Definition ###############

def _scrape_telegram(people, save_people_dir, image_dir):
    '''
    Scarica le foto profilo degli utenti Telegram

    Params:
    @people: Profili (classes.person) di cui completare il profilo Telegram scaricandone le immagini
    @save_people_dir: Directory dove salvare le informazioni dei profili
    @image_dir: Directory dove salvare le cartelle contenenti le immagini profilo
    '''

    # Variabili locali
    tg_profiles_list = []

    # Ottiene ed elabora le immagini dei profili Telegram
    _scrape_logger.info('Download Telegram profile pictures')

    # Elabora solo i profili non ancora elaborati
    for p in people:
        ps = p.get_profiles('Telegram')
        for tg_profile in ps:
            if not tg_profile.is_elaborated:
                tg_profiles_list.append(tg_profile)

    # Se non ci sono profili ritorna evitando di creare un instanta Telethon
    if not len(tg_profiles_list) > 0: return

    # Scarica le immagini
    with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client:
        for p in tqdm(profiles, colored('[TELEGRAM]', 'cyan') + ' Download and image processing of Telegram profiles images'):
            # Se richiesto dall'utente esce dal ciclo (per chiudere il client Telegram aperto con with)
            # e poi termina il programma
            if _terminate_program:
                break

            ps = p.get_profiles('Telegram')
            if len(ps) == 0:
                continue

            tg_profile = ps[0]  # L'unico profilo disponibile
            if tg_profile.is_elaborated:
                continue

            _scrape_logger.debug('Elaborating Telegram profile with username {} (ID {})'.format(tg_profile.username, tg_profile.user_id))

            # Forma i percorsi
            images_path = os.path.join(image_dir, 'person_{}_images'.format(str(p.id)))
            save_path = os.path.join(save_people_dir, '{}.person'.format(p.id))

            # Crea la cartella che conterrà le immagini
            if not os.path.exists(images_path): os.makedirs(images_path)
            
            # Scarica ed elabora le immagini
            tg_profile.download_profile_photos(images_path, tg_client)
            tg_profile.elaborate_images(images_path, tg_client)

            # Salva i dati
            pickle.dump(p, open(save_path, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
            database.set_person_checked(_db_path, p.id, 'Telegram')

    if _terminate_program:
        _end_program()


def _scrape_facebook_instagram(people, save_people_dir):
    '''
    Esegue l'associazione dei profili delle persone a Facebook e Instagram.
    Vengono eseguite le associazioni in maniera alternata, così da limitare 
    i casi di blocco degli account o di attesa per troppe richieste.

    Params:
    @people: Lista di classes.person a cui associare un profilo Twitter
    @save_people_dir: Cartella dove salvare i file profilo
    '''

    # Apre il browser per Facebook
    _scrape_logger.info('Creation of Facebook scraper')
    fb_scraper = fb_functions.fb_scraper(_fb_logger)
    fb_scraper.init_scraper(use_proxy=False)
    if not fb_scraper.fb_login(password_manager.fb_email, password_manager.fb_password):
        print(colored('[FACEBOOK]', 'blue', 'on_white') +
              ' Unable to login to Facebook')
        _scrape_logger.error('Unable to login to Facebook')
        fb_scraper.terminate()

    # Crea l'istanza per Instagram
    _scrape_logger.info('Creation of Instagram scraper')
    ig_scraper = ig_functions.ig_scraper(_ig_logger)
    if not ig_scraper.login_anonymously():
        print(colored('[INSTAGRAM]', 'magenta') +
              ' Unable to login to Instagram')
        _scrape_logger.error('Unable to login to Instagram')
        ig_scraper.terminate()

    # Inizia lo scraping
    _scrape_logger.info('Search for Instagram and Facebook users')
    for p in tqdm(people, 'Search for Instagram and Facebook users'):
        # Ottiene il percorso di salvataggio del file
        save_path = os.path.join(save_people_dir, '{}.person'.format(p.id))

        # Se l'utente ha scelto di terminare l'applicazione
        # vengono chiuse le istanze degli scraper
        if _terminate_program:
            fb_scraper.terminate()
            ig_scraper.terminate()
            _end_program()

        _scrape_logger.debug('Search user FB/IG profiles with profile ID {}, name {} {}'
                             .format(p.id, p.first_name, p.last_name))

        # Verifica che il profilo Facebook non sia stato bloccato
        if fb_scraper.is_blocked:
            fb_scraper.terminate()
            tqdm.write(colored('[Facebook]', 'blue', 'on_white') + ' Facebook profile has been blocked, now proceeding with only Instagram...')

        # Verifica se già esiste un profilo Facebook
        if not len(p.get_profiles('Facebook')) > 0 and fb_scraper.is_logged:
            # Ricerca del profilo Instagram
            result = p.find_facebook_profile(fb_scraper, 'italia')
            if result > 0:
                tqdm.write(colored('[Facebook]', 'blue', 'on_white') +
                           generic.only_ASCII(' Identified compatible Facebook profile for {} {} ({} references)'
                                              .format(p.first_name, p.last_name, result)))

            # Salva i risultati
            pickle.dump(p, open(save_path, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
            database.set_person_checked(_db_path, p.id, 'Facebook')

        # Verifica se già esiste un profilo Instagram
        if not len(p.get_profiles('Instagram')) > 0 and ig_scraper.is_initialized:
            # Ricerca del profilo Instagram
            result = p.find_instagram_profile(ig_scraper)
            if result > 0:
                tqdm.write(colored('[Instagram]', 'magenta') +
                           generic.only_ASCII(' Identified compatible Instagram profile for {} {} ({} references)'
                                              .format(p.first_name, p.last_name, result)))

            # Salva i risultati
            pickle.dump(p, open(save_path, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
            database.set_person_checked(_db_path, p.id, 'Instagram')

    # Chiude il browser Facebook
    _scrape_logger.info('Facebook WebDriver instance termination')
    fb_scraper.terminate()

    # Chiude il client Instagram
    _scrape_logger.info('Instagram client termination')
    ig_scraper.terminate()


def _scrape_twitter(people, save_people_dir):
    '''
    Esegue l'associazione dei profili delle persone a Twitter

    Params:
    @people: Lista di classes.person a cui associare un profilo Twitter
    @save_people_dir: Cartella dove salvare i file profilo
    '''

    # Istanzia lo scraper per Twitter
    tw_scraper = tw_functions.tw_scraper(_tw_logger)

    _scrape_logger.info('Search for Twitter users')
    for p in tqdm(people, 'Search for Twitter users'):
        # Gestisce l'interruzione della ricerca da parte dell'utente
        if _terminate_program:
            tw_scraper.terminate()
            _end_program()

        _scrape_logger.debug('Search user TW profiles with profile ID {}, name {} {}'
                             .format(p.id, p.first_name, p.last_name))

        # Verifica se già esiste un profilo Facebook
        if not len(p.get_profiles('Twitter')) > 0 and tw_scraper.is_initialized:
            # Ricerca del profilo Twitter
            result = p.find_twitter_profile(tw_scraper, 'italia')

            if result > 0:
                tqdm.write(colored('[Twitter]', 'white', 'on_cyan') +
                           generic.only_ASCII(' Identified compatible Twitter profile for {} {} ({} references)'
                                              .format(p.first_name, p.last_name, result)))

            # Salva i risultati
            save_path = os.path.join(save_people_dir, '{}.person'.format(p.id))
            pickle.dump(p, open(save_path, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)
            database.set_person_checked(_db_path, p.id, 'Twitter')

############### Main Functions Definition ###############

def scrape_group():
    global _base_dir, _db_path

    # Vengono definiti i logger
    _define_loggers()

    # Viene selezionata la cartella di lavoro
    _base_dir = _select_work_dir()

    # Crea i percorsi
    people_save_dir = os.path.join(_base_dir, 'people')
    tg_save_images_dir = os.path.join(_base_dir, 'telegram_images')
    _db_path = os.path.join(_base_dir, 'session.sqlite')

    # Crea la cartella
    if not os.path.exists(people_save_dir): os.makedirs(people_save_dir)
    if not os.path.exists(tg_save_images_dir): os.makedirs(tg_save_images_dir)

    # Crea il database
    if not os.path.exists(_db_path): database.create_database(_db_path)
    else: 
        print(colored('[ERROR]', 'red') + ' You have selected the working dir of an active scraping project, please select another directory')
        return

    # Selezione del gruppo da analizzare
    _scrape_logger.info('New session creation')
    target_group = _select_telegram_group()

    # Ottiene e salva i membri del gruppo Telegram come entità 'person'
    people_profiles = _select_and_save_group_members(target_group, people_save_dir)
    database.add_new_people(_db_path, people_profiles)

    # Ordina le persone in base al loro indice di identificabilità
    # (decrescente) e solo se hanno una possibilità di essere identificabili
    people_profiles = [p for p in people_profiles if p.get_identifiability() > _MIN_IDENTIFIABILITY_THREESHOLD]
    people_profiles.sort(key=lambda p: p.get_identifiability(), reverse=True)

    # Vengono scaricate le foto profilo degli utenti Telegram
    _scrape_telegram(people_profiles, people_save_dir, tg_save_images_dir)

    # Vengono elaborati i profili Facebook e Instagram
    _scrape_facebook_instagram(people_profiles, people_save_dir)

    # Vengono elaborati i profili Twitter
    _scrape_twitter(people_profiles, people_save_dir)
    
    print(colored('[SYSTEM]', 'green') + ' Social profile search completed, press a button to terminate the application')
    _scrape_logger.info('Social profile search finished')


def resume_scrape_session():
    '''
    Riprende l'esecuzione di una precedente operazione di scraping
    '''

    global _base_dir, _db_path

    # Vengono definiti i logger
    _define_loggers()

    # Viene selezionata la cartella di lavoro
    _base_dir = _select_work_dir()

    # Crea i percorsi
    people_save_dir = os.path.join(_base_dir, 'people')
    tg_save_images_dir = os.path.join(_base_dir, 'telegram_images')
    _db_path = os.path.join(_base_dir, 'session.sqlite')

    # Crea la cartella
    if not os.path.exists(people_save_dir): os.makedirs(people_save_dir)
    if not os.path.exists(tg_save_images_dir): os.makedirs(tg_save_images_dir)

    # Verifica l'esistenza del database
    if not os.path.exists(_db_path): 
        print(colored('[ERROR]', 'red') + 'Can\'t recover previous session, no database found!')
        return

    # Carica i profili creati in precedenza
    _scrape_logger.info('Restoring previous session')
    people_profiles = _load_people_profiles(people_save_dir)

    # Verifica se ci sono nuovi membri nel gruppo
    print(colored('[SYSTEM]','green') + ' Do you want to check if there are new members in the group? (y/n) ', end='')
    if input().lower() == 'y':
        # Selezione del gruppo da analizzare
        target_group = _select_telegram_group()

        _scrape_logger.info('Search for new Telegram profiles in the group (differential)')

        # Ottiene e salva i membri del gruppo Telegram come entità 'person'
        people_profiles = _select_and_save_group_members(target_group, people_save_dir, people_profiles)

    # Ordina le persone in base al loro indice di identificabilità
    # (decrescente) e solo se hanno una possibilità di essere identificabili
    people_profiles = [p for p in people_profiles if p.get_identifiability() > _MIN_IDENTIFIABILITY_THREESHOLD]
    people_profiles.sort(key=lambda p: p.get_identifiability(), reverse=True)

    # Vengono scaricate le foto profilo degli utenti Telegram
    ids_list = database.get_uncheked_people_ids_for_platform(_db_path, 'Telegram')
    tg_people_list = [p for p in people_profiles if p.id in ids_list]
    _scrape_telegram(tg_people_list, people_save_dir, tg_save_images_dir)

    # Vengono elaborati i profili Facebook e Instagram
    ids_list = database.get_uncheked_people_ids_for_platform(_db_path, 'Facebook')
    ids_list.extend(database.get_uncheked_people_ids_for_platform(_db_path, 'Instagram'))
    ids_list = list(set(ids_list))
    fb_ig_people_list = [p for p in people_profiles if p.id in ids_list]
    _scrape_facebook_instagram(fb_ig_people_list, people_save_dir)

    # Vengono elaborati i profili Twitter
    ids_list = database.get_uncheked_people_ids_for_platform(_db_path, 'Twitter')
    tw_people_list = [p for p in people_profiles if p.id in ids_list]
    _scrape_twitter(tw_people_list, people_save_dir)

    print(colored('[SYSTEM]', 'green') + ' Social profile search completed, press a button to terminate the application')
    _scrape_logger.info('Social profile search finished')


# Run when imported
if __name__ == 'scrape_group':
    # Load credentials
    password_manager.load_credential(_CREDENTIALS_PATH)
