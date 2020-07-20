################## Standard Imports ##################
import sqlite3

def create_connection(db_path:str):
    """ 
    Crea una connessione ad un database SQLite. Se non esiste il database lo crea.

    Params:
    @db_path: Percorso del database

    Return:
    Connessione al database
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as ex: print(ex)

def create_database(db_path):
    """
    Crea le tabelle del database. Se non esiste il database lo crea.

    Params:
    @db_path: Percorso del database
    """

    # Crea il database (se non esiste) e si connette
    connection = create_connection(db_path)

    # Crea la tabella principale
    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE people(id integer PRIMARY KEY, person_id integer, tg_checked integer, ig_checked integer, fb_checked integer, tw_checked integer)""")
    connection.commit()
    connection.close()

def add_new_people(db_path, people_list):
    """
    Aggiunge nuove persone al database

    Params:
    @db_path: Percorso del database
    @people_list: Lista di profili (classes.person) da aggiungere
    """

    # Variabili locali
    sql_insert_query = 'INSERT INTO people VALUES (NULL, ?, 0, 0, 0, 0)'

    # Si connette al database
    connection = create_connection(db_path)

    # Inserisce i dati
    cursor = connection.cursor()

    # Ottiene gli ID delle persone da inserire
    p_ids = [(p.id,) for p in people_list]

    # Inserisce gli ID
    cursor.executemany(sql_insert_query, p_ids)

    # Salva i dati
    connection.commit()

    # Termina la connessione
    connection.close()

def get_uncheked_people_ids_for_platform(db_path, platform):
    """
    Ritorna una lista di ID di persone che non sono state controllate per una specifica piattaforma

    Params:
    @db_path: Percorso del database
    @platform: Nome della piattaforma da controllare

    Return:
    Lista di ID di classes.person che non sono stati controllati per la piattaforma specificata
    """

    # Variabili globali
    prefix = ''
    sql_select_query = 'SELECT person_id FROM people WHERE {}_checked == 0'

    # Ottiene il prefisso da usare nella query
    if not platform.isalpha: return []

    if platform.lower() == 'telegram': prefix = 'tg'
    elif platform.lower() == 'instagram': prefix = 'ig'
    elif platform.lower() == 'facebook': prefix = 'fb'
    elif platform.lower() == 'twitter': prefix = 'tw'
    else: return []

    # Si connette al database
    connection = create_connection(db_path)

    # Legge i dati
    cursor = connection.cursor()
    cursor.execute(sql_select_query.format(prefix))
    rows = cursor.fetchall()

    # Termina la connessione
    connection.close()

    # Ritorna la lista di ID
    return [row[0] for row in rows]

def get_completed_people_ids(db_path):
    """
    Ritorna una lista di ID di persone che hanno subito un controllo per tutti i profili

    Params:
    @db_path: Percorso del database

    Return:
    Lista di ID di classes.person che sono stati controllati per tutte le piattaforme disponibili
    """

    # Variabili globali
    sql_select_query = 'SELECT person_id FROM people WHERE tg_checked == 1 AND fb_checked == 1 AND ig_checked == 1 AND tw_checked == 1'

    # Si connette al database
    connection = create_connection(db_path)

    # Legge i dati
    cursor = connection.cursor()
    cursor.execute(sql_select_query)
    rows = cursor.fetchall()

    # Termina la connessione
    connection.close()

    # Ritorna la lista di ID
    return [row[0] for row in rows]

def set_person_checked(db_path, person_id, platform):
    """
    Imposta una persona come 'controllata' per una specifica piattaforma

    Params:
    @db_path: Percorso del database
    @person_id: ID della persona controllata
    @platform: Nome della piattaforma
    """

    # Variabili locali
    prefix = ''
    sql_update_query = 'UPDATE people SET {}_checked=1 WHERE person_id=?'

    # Ottiene il prefisso da usare nella query
    if not platform.isalpha: return False

    if platform.lower() == 'telegram': prefix = 'tg'
    elif platform.lower() == 'instagram': prefix = 'ig'
    elif platform.lower() == 'facebook': prefix = 'fb'
    elif platform.lower() == 'twitter': prefix = 'tw'
    else: return False

    # Si connette al database
    connection = create_connection(db_path)

    # Crea un cursore
    cursor = connection.cursor()

    # Scrive i dati nel database
    cursor.execute(sql_update_query.format(prefix), (person_id,))

    # Salva i dati
    connection.commit()

    # Chiude la connessione
    connection.close()

    return True
