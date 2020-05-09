############### External Modules Imports ###############
from colorama import init
from termcolor import colored

############### Local Modules Imports ###############
import generic
from scrape_group import scrape_group, resume_scrape_session
from result_visualizer import visualize_result


def select_function():
    '''
    Mostra all'utente le scelte possibili per il programma

    Return:
    Indice dell'operazione selezionata, -1 se il valore non e' valido
    '''

    # Menu di selezione del gruppo da analizzare
    print(colored('[SYSTEM]', 'green') + ' Select operation:')

    print(colored('[', 'red') + str(0) + colored(']', 'red') +
        ' Resume Telegram group scraping')
    print(colored('[', 'red') + str(1) + colored(']', 'red') +
        ' Analyze Telegram group')
    print(colored('[', 'red') + str(2) + colored(']', 'red') +
          ' View Telegram group analysis results')
    print(colored('[', 'red') + str(3) + colored(']', 'red') +
          ' Social Engineering - NOT IMPLEMENTED YET')

    # Lascia selezionare all'utente l'operazione
    print(
        colored(
            '[SYSTEM]',
            'green') +
        ' Select the operation to be performed: ',
        end='')  # Senza ritorno a capo per mettere l'imput sulla stessa riga
    op_index = input()  # I colori ANSI non funzionano con input()

    # Controlla se il valore è valido
    if not op_index.isdigit():
        op_index = -1
    elif 0 > int(op_index) > 3:
        op_index = -1

    return int(op_index)


# Inizializza i colori ANSI
init()

if __name__ == '__main__':
    # Mostra il banner dell'applicazione
    generic.banner()

    # Lascia selezionare all'utente l'operazione da eseguire
    selection = select_function()

    # Esegue l'operazione
    if selection == 0:
        resume_scrape_session()
    elif selection == 1:
        scrape_group()
    elif selection == 2:
        visualize_result()
