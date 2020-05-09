import os
from telethon.sync import TelegramClient
from telethon.errors import UsernameInvalidError, UserInvalidError, ChatAdminRequiredError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon import functions

def connect_telegram_client(phone_number, api_id, api_hash):
    '''
    Crea un client e lo connette a Telegram.
    Se il client non è autenticato invia un codice sul profilo Telegram.

    @params:
    phone_number: Numero di telefono associato all'account Telegram compreso il prefisso internazionale
    api_id: ID dell'API generato per l'account utente
    api_hash: Hash dell'API generato per l'account utente

    @return:
    Client connesso e autenticato a Telegram
    '''

    # Crea il client Telegram
    client = TelegramClient(phone_number, api_id, api_hash)

    # Si connette a Telegram
    client.connect()

    # Se il client non è autenticato esegue la procedura di autenticazione
    # il codice viene inviato su Telegram
    if not client.is_user_authorized():
        client.send_code_request(phone_number)
        client.sign_in(phone_number, input(
            'Inserire codice di autenticazione: '))

    # Ritorna il client
    return client


def check_username_existance(tg_client, username):
    '''
    Controlla se il nome utente specificato esiste
    '''

    try:
        result = tg_client(functions.account.CheckUsernameRequest(
            username=username
        ))
        return result
    except UsernameInvalidError:  # Nessun utente ha questo username
        return False


def get_profiles(tg_client, value):
    '''
    Ottiene il profilo Telegram utilizzando username o user id
    '''

    try:
        result = tg_client(functions.help.GetUserInfoRequest(user_id=value))
        return result
    except UserInvalidError:  # Nessun utente ha username o user id specificato
        return None


def download_users_profile_photos(tg_client, tg_profile, save_dir):
    '''
    Scarica tutte le foto profilo dell'utente passato per parametro.
    Le foto salvate avranno nome 'userID_index.jpg'

    Params:
    @tg_client: Client Telegram connesso da usare per estrapolare i dati
    @tg_profile: Profilo da cui scaricare le immagini
    @save_dir: Directory di salvataggio delle immagini
    '''

    # Crea una cartella che conterrà le immagini di profilo
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    # Ottiene l'elenco delle foto profilo dell'utente
    photo_index = 0
    for photo in tg_client.iter_profile_photos(tg_profile):
        # Crea il nome dell'immagine
        savepath_image = os.path.join(
            save_dir, '{}_{}'.format(tg_profile.id, photo_index))

        # Cerca di scaricare l'immagine
        try:
            tg_client.download_media(photo, savepath_image)
            photo_index += 1
        except Exception as ex:
            if 'A wait of' in str(ex):
                # if 'ExportAuthorizationRequest' in str(ex):
                import time
                from datetime import datetime, timedelta

                # Troppe richieste, attende il numero di secondi specificato
                wait_time = int(''.join(x for x in str(ex) if x.isdigit()))
                resume_time = datetime.now() + timedelta(seconds=wait_time)
                print(
                    '\nPer evitare di formulare troppe richieste il client Telegram attendera\' {} secondi (riprendera\' alle {})'.format(
                        wait_time,
                        resume_time))
                time.sleep(wait_time)

                # Riprova a scaricare l'immagine
                try:
                    tg_client.download_media(photo, savepath_image)
                    photo_index += 1
                except BaseException:
                    pass
            else:
                print('\nImpossibile scaricare l\'immagine: {}'.format(ex))


def get_all_conversations(tg_client, only_groups=False,
                          last_date=None, chat_size=200):
    '''
    Ottiene tutte le conversazioni aperte sul client impostato.

    Params:
    @tg_client: Client Telegram connesso da usare per estrapolare i dati
    @only_groups [False]: Ottiene le chat solo dai gruppi (ignora le chat private e i canali)
    @last_date [None]: Ottenere le chat fino a questo giorno
    @chat_size [200]: Numero massimo di messaggi ottenibili (???)

    @return:
    Lista di tuple, ogni record è un gruppo (gruppo, 0), un canale (canale, 1),
    una chat privata (chat, 2) o una conversazione non identificabile (?, 3)
    '''

    # Variabili locali
    chats = []
    return_values = []

    # Ottiene tutti le chat aperte e i loro messaggi
    result = tg_client(GetDialogsRequest(
        offset_date=last_date,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=chat_size,
        hash=0
    ))
    chats.extend(result.chats)

    # Separa gruppi da canali e conversazioni private
    for chat in chats:
        try:
            if chat.megagroup == True:
                return_values.append((chat, 0))  # Gruppi
            elif chat.broadcast == True:
                return_values.append((chat, 1))  # Canali
            else:
                return_values.append((chat, 2))  # Chat private
        except BaseException:
            return_values.append((chat, 3))  # Sconosciuto

    # Ottiene tutti i gruppi ed esclude gli utenti privati e i canali
    if only_groups:
        return_values = [value for value in return_values if value[1] == 0]

    # Ritorna le conversazioni individuate
    return return_values


def get_group_channel_members(tg_client, conversation):
    '''
    Ottiene gli iscritti ad uno specifico gruppo o canale.
    Può non estrarre degli utenti in caso di gruppi molto ampi.
    E' necessario essere ammnistratori per ottenere i dati di un canale privato.

    Params:
    @tg_client: Client Telegram connesso da usare per estrapolare i dati
    @group: Gruppo da cui estrarre i partecipanti

    Return:
    Lista di profili Telegram iscritti al gruppo
    '''

    # Variabili locali
    all_participants = []

    # Ottiene i partecipanti
    try:
        # Aggressive = True serve per ottenere più di 10K partecipanti
        all_participants = tg_client.get_participants(
            conversation, aggressive=True)
    except ChatAdminRequiredError as ex:
        print('Impossibile ottenere i dati se non si è amministratori del canale privato ({})'.format(ex))

    # Ritorna la lista
    return all_participants


def download_media_from_conversation(tg_client, conversation, save_dir, message_limit=3000):
    '''
    DON'T USE THIS
    '''

    import os

    for message in tg_client.iter_messages(conversation, limit=message_limit):
        if message.media is not None:
            path = message.download_media(file=os.path.abspath('test'))
            yield path
