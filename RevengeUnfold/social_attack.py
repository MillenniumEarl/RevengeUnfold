import datetime
import os
from itertools import islice

############### External Modules Imports ###############
from colorama import init
from termcolor import colored
from tqdm import tqdm

from scrape_functions import tg_functions
import generic
import password_manager


def take(n, iterable):
    '''
    Return first n items of the iterable as a list
    '''

    return list(islice(iterable, n))


def select_telegram_group():
    '''
    '''

    # Collega il client Telegram
    with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client:
        # Ottiene tutte le conversazioni a cui il profilo è connesso
        list_conversations = tg_functions.get_all_conversations(
            tg_client, only_groups=True)

    # Menu di selezione del gruppo da analizzare
    print(colored('[TELEGRAM]', 'cyan') + ' Selezione gruppo da analizzare:')
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
        ' Inserisci il numero del gruppo da analizzare: ',
        end='')  # Senza ritorno a capo per mettere l'imput sulla stessa riga
    conv_index = input()  # I colori ANSI non funzionano con input()
    target_group = list_conversations[int(conv_index)]
    group_name = generic.only_ASCII(target_group[0].title).strip()
    print(colored('[TELEGRAM]', 'cyan') +
          ' E\' stato selezionato il gruppo: {}'.format(group_name))

    return target_group


def get_most_active_users(tg_group, n_active_users=25, message_limit=3000):
    '''
    Dato un gruppo Telegram ottiene gli utenti che scrivono più messaggi

    Params:
    @tg_group: Gruppo da analizzare
    @n_active_users [25]: Numero massimo di utenti più attivi da individuare
    @message_limit[3000]: Numero massimo di messaggi da controllare per i dentificare i profili attivi
    '''

    # Variabili locali
    active_users = {}

    with tg_functions.connect_telegram_client(password_manager.tg_phone, password_manager.tg_api_id, password_manager.tg_api_hash) as tg_client:
        # Itera i messaggi della chat dal più nuovo al più vecchio
        for message in tqdm(tg_client.iter_messages(
                tg_group, limit=message_limit)):
            # Ottiene l'ID dell'utente che ha scritto il messaggio
            user_id = message.sender_id

            # Prende il numero di messaggi scritti dall'utente e lo incrementa
            count_messages = active_users.get(user_id, 0)
            count_messages += 1

            # Salva il numero di messaggi scritti dall'utente (se l'utente non
            # esiste lo crea)
            active_users[user_id] = count_messages

    # Ordina il dizionario in base al numero di messaggi scritti
    active_users = {
        k: v for k,
        v in sorted(
            active_users.items(),
            key=lambda item: item[1],
            reverse=True)}
    n_items = take(n_active_users, active_users.items())
    return n_items


init()

if __name__ == '__main__':
    group = select_telegram_group()

    most_active_users = get_most_active_users(group[0])
