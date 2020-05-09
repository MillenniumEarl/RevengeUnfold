############### Standard Imports ###############
import glob
import multiprocessing
import os
import pickle

############### External Modules Imports ###############
from colorama import init
from termcolor import colored
from tqdm import tqdm
import face_recognition
import photohash

############### Local Modules Imports ###############
from classes import person
#from scrape_functions import fb_functions
# from scrape_functions import tg_functions -> Importato localmente in select_telegram_group(), select_and_save_group_members()
#import generic

#import password_manager


def get_faces_from_images(image_path):
    '''
    '''

    # Variabili locali
    return_dict = {'path': image_path, 'faces': []}

    # Verifica se l'immagine è valida, altrimenti la elimina
    try:
        image = face_recognition.load_image_file(image_path)
    except BaseException:
        os.remove(image_path)
        return

        # Elabora i volti
    face_encodings = face_recognition.face_encodings(image)
    if len(face_encodings) == 0:
        return  # Nessun volto individuato
    else:
        return_dict['faces'] = face_encodings
    print()


def get_faces_from_video():
    print()


def compute_hash(image_path):
    '''
    '''

    hash = photohash.average_hash(image_path)

    return {'path': image_path, 'hash': hash}


def elaborate_images(images_dir):
    '''
    '''

    global pool, max_id

    # Ottiene tutte le immagini dalla cartella base
    filepath_list = glob.glob(
        os.path.join(
            images_dir,
            '*.jpg'),
        recursive=True)

    # Rimuove le thumbnail
    filepath_list = [path for path in filepath_list if not 'thumb' in path]

    # Esegue l'hash delle immagini e le salva in un database
    hashes_dict = pool.map(compute_hash, filepath_list)

    # Legge gli hash già presenti nel database e li confronta con quelli trovati trovando le immagini nuove
    # ...
    # ...

    # Copia le immagini nella cartella di 'elaborazione'
    # ...

    # Ottiene i volti presenti nelle immagini
    faces_dict = pool.map(get_faces_from_images, filepath_list)

    # "Appiattisce" le liste di volti contenute nei dizionari
    faces_dict_tmp = []
    for dict in faces_dict:
        for face_encoding in dict['faces']:
            faces_dict_tmp.append(
                {'path': dict['path'], 'face': face_encoding})
    faces_dict = faces_dict_tmp.copy()

    # Salva le codifiche dei volti
    for dict in tqdm(faces_dict, 'Salvataggio volti rilevati', position=0):
        recognized = False

        # Verifica se esiste già qualche utente con lo stesso volto
        for person in tqdm(people_profiles_list,
                           'Analisi volti salvati', position=0):
            if recognized is True:
                continue
            # Conta quanti volti sono uguali a quello confrontato
            if face_recognition.compare_faces(
                    person.face_encodings, dict['face']).count(True) > 0:
                person.face_encodings.append(face_encoding)
                recognized = True

        # Se il volto non è stato riconosciuto crea un nuovo profilo e lo salva
        if not recognized:
            save_path = os.path.join(PEOPLE_DIR, '{}.person'.format(max_id))
            p = person.person(max_id)
            p.face_encodings.append(dict['face'])
            pickle.dump(
                p,
                open(
                    save_path,
                    'wb'),
                protocol=pickle.HIGHEST_PROTOCOL)
            max_id += 1

    # Sposta le immagini dalla cartella di 'elaborazione' alla cartella 'elaborate'
    # ...


if __name__ == '__main__':
    # Variabili globali
    pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    people_profiles_list = []
    BASE_DIR = 'data'
    WAIT_TO_PROCESS_DIR = os.path.join(BASE_DIR, 'to_compute')
    PEOPLE_DIR = os.path.join(BASE_DIR, 'people')
    PROCESSED_MEDIA = os.path.join(BASE_DIR, 'elaborated')
    PROCESSED_IMAGES = os.path.join(PROCESSED_MEDIA, 'photos')
    PROCESSED_VIDEO = os.path.join(PROCESSED_MEDIA, 'videos')

    # Carica i profili già esistenti
    # profiles = load_profiles...
    max_id = max(profile.id for profile in profiles) + 1
