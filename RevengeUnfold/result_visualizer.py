############### Standard Imports ###############
import csv
from glob import glob
import os
import pickle
import tkinter as tk
from tkinter import filedialog

############### External Modules Imports ###############
from termcolor import colored
from tqdm import tqdm

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
    for filepath in tqdm(filepath_list, colored('[SYSTEM]', 'green') + ' Loading profiles'):
        p = pickle.load(open(filepath, 'rb'))
        profiles_list.append(p)

    return profiles_list

def _export_to_csv(peoples_data, save_path):
    '''
    Esporta i dati dei profili degli utenti in un file CSV

    Params:
    @peoples_data: Lista di oggetti classes.person
    @save_path: Percorso di salvataggio del file CSV
    '''

    # Apre il file per il salvataggio in scrittura
    with open(save_path, 'w', encoding='utf-8') as f:
        fnames = ['Nome', 'Cognome', 'Username Telegram', 'Telefono Telegram', 'Username Facebook', 'Username Instagram', 'Identificabilità']
        writer = csv.DictWriter(f, fieldnames=fnames)  

        writer.writeheader()

        for p in peoples_data:
            tg_profile = p.get_profiles('Telegram')[0]
            fb_profile = p.get_profiles('Facebook')[0]
            ig_profile = p.get_profiles('Instagram')[0]
            tg_phone = tg_profile.phone.number if tg_profile.phone is not None else 'Nessun numero'

            data = {
                    'Nome':p.first_name, 
                    'Cognome':p.last_name, 
                    'Username Telegram': '@' + tg_profile.username,
                    'Telefono Telegram': tg_phone, 
                    'Username Facebook': fb_profile.username, 
                    'Username Instagram': ig_profile.username, 
                    'Identificabilità': p.get_identifiability()
                    }
            writer.writerow(data)

def visualize_result():
    # Seleziona la cartella da cui caricare i profili
    root = tk.Tk()
    root.withdraw()

    print(colored('[SYSTEM]', 'green') + ' Press a key to select the folder containing the profiles', end = '')
    input()

    dir_path = filedialog.askdirectory()
    if dir_path == '':
        print(colored('[ERROR]', 'red') + ' You must select a folder to continue')
        return

    # Carica i profili
    profiles = _load_people_profiles(dir_path)

    # Filtra solo i profili che possiedono account Telegram, Instagram e Facebook
    profiles = [profile for profile in profiles if len(profile.get_profiles('Telegram')) > 0 and len(profile.get_profiles('Facebook')) > 0 and len(profile.get_profiles('Instagram')) > 0]

    # Ordina le persone in base al loro indice di identificabilità
    # (decrescente)
    profiles.sort(key=lambda p: p.get_identifiability(), reverse=True)

    print(colored('[SYSTEM]', 'green') + ' I profili probabilmente identificati sono {}'.format(len(profiles)))

    # Salva un file CSV con i dati
    print(colored('[SYSTEM]', 'green') + ' Vuoi salvare un file CSV riepilogativo? (y/n): ', end = '')
    save_csv = input()

    if save_csv.lower() == 'y':
        save_path = filedialog.asksaveasfilename(title = 'Seleziona file di salvataggi', defaultextension='.csv', filetypes = (('File CSV','*.csv'),))
        if save_path == '':
            print(colored('[ERROR]', 'red') + ' You must select a file to continue')
            return
        _export_to_csv(profiles, save_path)
        print(colored('[SYSTEM]', 'green') + ' Profiles exported correctly')

    # Stampa i profili
    for profile in profiles:
        print('#################################################')
        profile.print_info()
        print(colored('[SYSTEM]', 'green') + ' Press a key to show the next profile', end = '')
        input()

    print(colored('[SYSTEM]', 'green') + ' All profiles showed')