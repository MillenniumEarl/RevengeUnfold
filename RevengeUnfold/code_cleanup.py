import os
import subprocess
import datetime
from pathlib import Path

################ Variabili globali ################
vulture_script = 'vulture "{}" --min-confidence 70 --sort-by-size'
autopep8_script = 'autopep8 "{}" -a --in-place'
source_code_paths = [
    'main.py',
    'scrape_group.py',
    'generic.py',
    'code_cleanup.py',
    'password_manager.py',
    '_download_and_classify_media.py',
    'social_attack.py',
    os.path.join('scrape_functions', 'fb_functions.py'),
    os.path.join('scrape_functions', 'ig_functions.py'),
    os.path.join('scrape_functions', 'tg_functions.py'),
    os.path.join('scrape_functions', 'tw_functions.py'),
    os.path.join('scrape_functions', 'scraper_error.py'),
    os.path.join('classes', 'location.py'),
    os.path.join('classes', 'phone.py'),
    os.path.join('classes', 'proxy.py'),
    os.path.join('classes', 'person.py'),
    os.path.join('classes', 'profiles.py'),
]

################ Definizione funzioni ################


def run_script(script:str, output_file:str):
    """
    Esegue uno script e salva un file con l'output dello stesso
    """

    # Esegue lo script
    p = subprocess.Popen(script, stdout=subprocess.PIPE, shell=True)

    # Ottiene l'output del processo
    (output, err) = p.communicate()

    # Attende la terminazione dello script
    p_status = p.wait()

    # Salva il file di output
    with open(output_file, 'w') as f:
        f.write('#############################################################\n')
        f.write('# Esecuzione dello script:\n')
        f.write('# {}\n'.format(script))
        f.write('# Esecuzione in data: {}\n'.format(datetime.datetime.now()))
        f.write('# Lo script è terminato con codice: {}\n'.format(p_status))
        f.write('# Output:\n')
        f.write(output.decode('cp437'))  # Scrive l'output
        f.write('#############################################################\n')
        if err is not None:
            f.write('Errori rilevati:\n')
            f.write(err.decode('cp437'))
            f.write('#############################################################\n')


if __name__ == '__main__':
    # Crea le directory necessarie
    vulture_dir = os.path.abspath('vulture reports')
    autopep8_dir = os.path.abspath('autopep8 reports')

    if not os.path.exists(vulture_dir):
        os.mkdir(vulture_dir)
    if not os.path.exists(autopep8_dir):
        os.mkdir(autopep8_dir)

    for path in source_code_paths:
        filename_noext = Path(path).stem
        print('Script: {}'.format(path))
        savefile_path = '{}.txt'.format(filename_noext)

        # Esegue lo script autopep8 per la convenzione PEP8
        save_path = os.path.join(autopep8_dir, savefile_path)
        run_script(autopep8_script.format(os.path.abspath(path)), save_path)

        # Esegue lo script Volture per la ricerca di dead code
        save_path = os.path.join(vulture_dir, savefile_path)
        run_script(vulture_script.format(os.path.abspath(path)), save_path)
