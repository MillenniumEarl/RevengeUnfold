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

############### Local Modules Imports ###############
import database

def _select_work_dir():
    """
    Lascia selezionare all'utente la cartella di lavoro da utilizzare

    Return:
    Percorso della cartella selezionata dall'utente
    """

    # Seleziona la cartella da cui caricare i profili
    root = tk.Tk()
    root.withdraw()

    print(colored('[SYSTEM]', 'green') + ' Press a key to select the work directory', end='')
    input()

    selected_dir = filedialog.askdirectory()

    print(colored('[SYSTEM]', 'green') + ' Selected directory: {}'.format(selected_dir))

    return selected_dir

def _load_people_profiles(load_dir):
    """
    Load previously saved user profiles

    Params:
    @load_dir: Directory where user profiles are contained

    Return:
    List of profiles (classes.person)
    """

    # Local variables
    profiles_list = []

    # Search all save files
    filepath_list = glob(os.path.join(load_dir, '*.person'))

    # Load profiles
    for filepath in tqdm(filepath_list, colored('[SYSTEM]', 'green') + ' Loading profiles'):
        p = pickle.load(open(filepath, 'rb'))
        profiles_list.append(p)

    return profiles_list

def _export_to_csv(peoples_data, save_path):
    """
    Export user profile data to a CSV file

    Params:
    @peoples_data: List of classes.person objects
    @save_path: Path to save the CSV file
    """

    # Opens the CSV file for writing saving
    with open(save_path, 'w', encoding='utf-16') as f:
        fnames = ['Full Name', 'Telegram Username', 'Telegram Phone', 'Facebook Username', 'Instagram Username', 'Twitter Username', 'Identifiability']
        writer = csv.DictWriter(f, fieldnames=fnames)  

        writer.writeheader()

        for p in peoples_data:
            # Check and get social profiles
            tg_profile = p.get_profiles('Telegram')[0] if len(p.get_profiles('Telegram')) > 0 else None
            fb_profile = p.get_profiles('Facebook')[0] if len(p.get_profiles('Facebook')) > 0 else None
            ig_profile = p.get_profiles('Instagram')[0] if len(p.get_profiles('Instagram')) > 0 else None
            tw_profile = p.get_profiles('Twitter')[0] if len(p.get_profiles('Twitter')) > 0 else None

            # Check and get Telegram phone number
            if tg_profile is None: tg_phone = 'No phone number'
            else: tg_phone = tg_profile.phone.number if tg_profile.phone is not None else 'No phone number'
            
            # Prepare and write data into CSV file
            data = {
                    'Full Name':p.get_full_name(), 
                    'Telegram Username': '@' + str(tg_profile.username) if tg_profile is not None else 'No profile', 
                    'Telefono Telegram': tg_phone, 
                    'Facebook Username': fb_profile.username if fb_profile is not None else 'No profile', 
                    'Instagram Username': ig_profile.username if ig_profile is not None else 'No profile',
                    'Twitter Username': '@' + str(tw_profile.username) if tw_profile is not None else 'No profile',
                    'Identifiability': p.get_identifiability()
                    }
            writer.writerow(data)

def visualize_result():
    # Select the workdir
    base_dir = _select_work_dir()

    if base_dir == '':
        print(colored('[ERROR]', 'red') + ' You must select a folder to continue')
        return

    # Load completed profiles IDs
    db_path = os.path.join(base_dir, 'session.sqlite')
    ids_list = database.get_completed_people_ids(db_path)

    # Load profiles
    people_profiles = _load_people_profiles(os.path.join(base_dir, 'people'))

    # Filter complete profiles
    people_profiles = [p for p in people_profiles if p.id in ids_list]

    # Sort people by their identifiability index (descending)
    people_profiles.sort(key=lambda p: p.get_identifiability(), reverse=True)

    print(colored('[SYSTEM]', 'green') + ' The profiles probably identified are {}'.format(len(people_profiles)))

    # Save a summary CSV file with completed profile data
    print(colored('[SYSTEM]', 'green') + ' Do you want to save a summary CSV file? (y/n): ', end = '')
    save_csv = input()

    if save_csv.lower() == 'y':
        save_path = filedialog.asksaveasfilename(title = 'Select save file', defaultextension='.csv', filetypes = (('CSV file','*.csv'),))
        if save_path == '':
            print(colored('[ERROR]', 'red') + ' You must select a file to continue')
            return
        else:
            _export_to_csv(people_profiles, save_path)
            print(colored('[SYSTEM]', 'green') + ' Profiles exported correctly')

    # Print the choice of profiles
    index = 1
    print(colored('[SYSTEM]', 'green') + ' Select a profile to view its details or 0 to exit: ')
    for p in people_profiles:
        print(colored('[', 'red') + str(index) + colored(']', 'red') + ': {} (Identifiability: {})'.format(p.get_full_name(), p.get_identifiability()))
        index += 1

    exit_bool = False
    while not exit_bool:
        print(colored('[SYSTEM]', 'green') + ' Select a profile to view its details or 0 to exit: ', end='')
        selected_index = input()

        # Check the validity of the entered value
        if not selected_index.isdigit():
            print(colored('[ERROR]', 'red') + ' You must enter a number')
            continue
        elif not 1 < selected_index < len(people_profiles):
            print(colored('[ERROR]', 'red') + ' You must enter a number between 1 and {}'.format(len(people_profiles)))
            continue
        elif selected_index == 0:
            print(colored('[SYSTEM]', 'green') + ' Closing visualizer')
            exit_bool = True
            continue

        # Show the details of the selected profile
        p = people_profiles[selected_index - 1]
        p.print_info()
    