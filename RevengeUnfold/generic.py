############### Standard Imports ###############
import time
import logging
import string

############### External Modules Imports ###############
from PIL import Image


def only_ASCII(s):
    '''
    Elimina tutti i caratteri non ASCII da una stringa

    Params:
    @s: Stringa da cui rimuovere i caratteri

    Return:
    Stringa senza caratter non ASCII
    '''

    # Ottiene il set di caratteri non stampabili da rimuovere
    printable = set(string.printable)

    # Se la stringa è nulla la ritorna
    if s is None: return None

    # Rimuove i caratteri
    s = ''.join(filter(lambda x: x in printable, s))

    # Ritorna la stringa risultante
    return s


def list_to_chunks(list, n):
    '''
    Divide una lista in liste da n parti ciascuna

    Params:
    @list: Lista da dividere
    @n: Numero di elementi per sottolista

    Return:
    Lista di liste
    '''
    for i in range(0, len(list), n):
        yield list[i:i + n]


def concat(*args, separator=' '):
    '''
    '''

    nonnull_args = [str(arg).strip() for arg in args if arg]  # Filter NULLs
    good_args = [arg for arg in nonnull_args if arg]          # Filter blanks

    retval = separator.join(good_args)

    return retval


def check_image_validity(image_path):
    try:

        im = Image.load(image_path)
        im.verify()  # I perform also verify, don't know if he sees other types o defects
        im.close()  # reload is necessary in my case
        return True
    except Exception as ex:
        print(ex)
        return False


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        with open('logtime.log', 'a+') as f:
            f.write(
                '[{}]: {:.2f}\n'.format(
                    method.__name__.upper(),
                    (te - ts) * 1000))

        return result
    return timed


def banner():
    '''
    '''

    from pyfiglet import Figlet

    custom_fig = Figlet(font='shadow')
    print(custom_fig.renderText('RevengeUnfold'))


def create_logger(name, save_path):
    '''
    '''

    # Crea il logger e la formattazione da usare
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        '[%(asctime)s - %(name)s - %(levelname)s]: %(message)s')

    # Crea un handler per scrivere su file
    fh = logging.FileHandler(save_path)
    fh.setFormatter(formatter)

    # Associa al logger l'handler per la scrittura su file
    logger.addHandler(fh)

    return logger
