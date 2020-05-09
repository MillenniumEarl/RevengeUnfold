############### External Modules Imports ###############
import photohash

############### Local Modules Imports ###############
from classes import profiles

# Costanti globali
NAME_MIN_LENGHT = 4
MIN_MATCH_THREESHOLD = 5


class person:
    def __init__(self, id):
        self.id = id
        self.first_name = None
        self.last_name = None
        self.phones = []
        self.locations = []
        self.profiles = []
        self.face_encodings = []
        self.perceptual_hashes = []

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d

    def _prepare_search_data(self, custom_keywords = None):
        '''
        Raccogli i dati associati al profilo utente e crea una lista di nomi utente e keywords da usare nella ricerca dei profili

        Params:
        @custom_keywords [None]: Lista di parole chiave aggiuntive da usare nella ricerca

        Return:
        Dizionario composto da:
            usernames_list: Lista di nomi utente
            keywords_list: LIsta di parole chiave
        '''

        # Prepara i profili social associati all'utente al confronto
        unready_profiles = [p for p in self.profiles if not p.is_elaborated]
        for p in unready_profiles:
            p.elaborate_images()

        # Ottiene gli username unici dai profili social associati all'utente
        usernames_list = [p.username for p in self.profiles if p.username is not None]
        usernames_list = list(set(usernames_list))  # Rimuove i duplicati

        # Crea una lista di tuple con nome e cognome dei profili associati
        keywords_tuple_list = [(p.first_name, p.last_name) for p in self.profiles]

        # Aggiunge alla lista nome e cognome dell'utente
        keywords_tuple_list.append((self.first_name, self.last_name))
        keywords_tuple_list = list(set(keywords_tuple_list))  # Rimuove i duplicati

        # Unisce le parole chiave aggiungtive in un'unico valore
        if custom_keywords is None: custom_keywords = []
        extra_keywords = [str(k) for k in custom_keywords]
        extra_keyword = ' '.join(extra_keywords)

        # Compila una lista di keywords con cui cercare i profili simili
        keywords = []
        for tup in keywords_tuple_list:
            # Scompatta la tupla
            first_name = tup[0]
            last_name = tup[1]

            # Se nome o cognome sono nulli la ricerca darà molto probabilmente
            # falsi positivi
            if first_name is None or last_name is None:
                continue

            # Se nome o cognome sono lunghi pochi caratteri molto probabilmente
            # sono falsi
            if len(first_name) < NAME_MIN_LENGHT or len(last_name) < NAME_MIN_LENGHT:
                continue

            # Verifica che non siano stati inseriti duplicati nell'elenco delle
            # keywords (nomi e cognomi invertiti per esempio)
            if '{} {}'.format(first_name, last_name) in keywords or '{} {}'.format(last_name, first_name) in keywords:
                continue

            # Se tutte le condizioni sono verificate aggiunge le keywords
            keywords.append('{} {} {}'.format(first_name, last_name, extra_keyword))

        return {'usernames_list': usernames_list, 'keywords_list': keywords}

    def print_info(self):
        '''
        Stampa le informazioni  di questo oggetto
        '''

        # Stampa nome e cognome
        print('Nome: {}'.format(self.first_name))
        print('Cognome: {}'.format(self.last_name))

        # Stampa i dati sui numeri di telefono
        for phone in self.phones:
            print('Telefono: {} - {}, {}'.format(phone.number,
                                                 phone.carrier, phone.geolocation))

        # Stampa le informazioni sui profili
        print('Profili social: {} ({} profili)'.format(
            ', '.join([p.platform for p in self.get_profiles()]), len(self.profiles)))
        if len(self.profiles) > 0:
            print('----------------------------------')
        for ps in self.profiles:
            ps.print_info()
            print('----------------------------------')

        # Stampa informazioni sull'ultima localitá associata
        if len(self.locations) > 0:
            # Ordina le localitá
            self.locations.sort(key=lambda loc: loc.utc_time, reverse=True)
            print(
                'Ultima localita\' associata: {} in data {} ({}, {})'.format(
                    self.locations[0].name,
                    self.locations[0].time,
                    self.locations[0].latitude,
                    self.locations[0].longitude))

        # Stampa altre informazione
        print('Numero di volti codificati: {}'.format(len(self.face_encodings)))
        print('Numero di immagini codificate: {}'.format(
            len(self.perceptual_hashes)))
        print(
            'Indice di identificabilita\' del profilo: {}'.format(
                self.get_identifiability()))

    def get_profiles(self, platform=None):
        '''
        Ritorna i profili social associati alla persona

        Params:
        @platform [None]: Nome della piattaforma con cui filtrare i profili. Se None ritorna tutti i profili.

        Return:
        Lista di profili associati all'utente
        '''

        if platform is None:
            return self.profiles
        return [profile for profile in self.profiles if profile.platform.lower()
                == platform.lower()]

    def add_profile(self, profile):
        '''
        Aggiunge un profilo social all'elenco di profili associati all'utente

        Params:
        @profile: Profilo da associare
        '''

        # Aggiunge i dati del profilo alla persona
        if self.first_name is None and profile.first_name is not None:
            if len(profile.first_name) >= NAME_MIN_LENGHT and not any(
                    map(str.isdigit, profile.first_name)):
                self.first_name = profile.first_name
        if self.last_name is None and profile.last_name is not None:
            if len(profile.last_name) >= NAME_MIN_LENGHT and not any(
                    map(str.isdigit, profile.first_name)):
                self.last_name = profile.last_name
        if profile.phone is not None:
            self.phones.append(profile.phone)

        # Aggiunge i luoghi visitati dalla persona
        self.locations.extend(profile.locations)

        # Aggiunge i nuovi volti
        self.face_encodings.extend(profile._face_encodings)

        # Aggiunge gli hash delle nuove immagini
        for cmp_hash in profile._perceptual_hashes:
            for hash in self.perceptual_hashes:
                if photohash.hashes_are_similar(hash, cmp_hash):
                    self.perceptual_hashes.append(cmp_hash)
                    break

        # Ordina la lista dalla locazione più recente a quella meno recente
        if len(profile.locations) > 0:
            self.locations.sort(key=lambda loc: loc.utc_time, reverse=True)

        # Aggiunge il profilo
        self.profiles.append(profile)

    def get_identifiability(self):
        '''
        Ottiene un indice di identificabilità dell'utente in base ai dati dei profili social associati

        Return:
        Valore intero che indica la rintracciabilità sui social network
        '''

        # Indica l'identificabilità della persona
        identifiability = 0

        if self.first_name is not None:
            identifiability += 1
        if self.last_name is not None:
            identifiability += 1
        identifiability += len(self.phones)
        identifiability += len(self.face_encodings)
        identifiability += len(self.perceptual_hashes)

        return identifiability

    def find_telegram_profile(self):
        '''
        In base ai dati che possiede ricerca il profilo Telegram della persona

        Return:
        Valore del match migliore
        '''

        print()

    def find_instagram_profile(self, ig_scraper, *custom_keywords):
        '''
        In base ai dati che possiede ricerca il profilo Instagram della persona

        Params:
        @ig_scraper: Istanza di scrape_functions.ig_scraper utilizzata per cercare gli utenti
        @custom_keywords: Elenco di parole chiave aggiuntive da usare nella ricerca

        Return:
        Valore del match migliore
        '''

        # Variabili locali
        possibile_profiles = []

        # Ottiene i dati da usare nella ricerca
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Ricerca per nomi utenti
        for username in search_data['usernames_list']:
            p = ig_scraper.find_user_by_username(username)
            if p is not None:
                possibile_profiles.append(p)

        # Ricerca per parole chiave
        for keyword in search_data['keywords_list']:
            ig_profiles = ig_scraper.find_user_by_keywords(keyword)
            if ig_profiles is not None:
                possibile_profiles.extend(ig_profiles)

        # Filtra profili (ricerche ridondanti)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # Una volta individuati i possibili profili li converte negli oggetti
        # profiles.instagram_profile e li preprara per il confronto.
        # Nel loop esegue anche il confronto tra i possibili profili Instagram e i profili già presenti per il profilo.
        # (si calcola la somma di tutti i confronti).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for pp in possibile_profiles:
            igp = profiles.instagram_profile()
            igp.get_profile_from_ig_profile(pp)
            igp.elaborate_images(ig_scraper)

            # Esegue i confronti ed eventualmente salva il profilo
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(igp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = igp

        # Una volta terminati i confronti si aggiunge il profilo migliore (se è
        # stato trovato)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        else:
            return 0

    def find_facebook_profile(self, fb_scraper, *custom_keywords):
        '''
        In base ai dati che possiede ricerca il profilo Facebook della persona

        Params:
        @fb_scraper: Istanza di scrape_functions.fb_scraper utilizzata per cercare gli utenti
        @custom_keywords: Elenco di parole chiave aggiuntive da usare nella ricerca

        Return:
        Valore del match migliore
        '''

        # Variabili locali
        possibile_profiles = []

        # Ottiene i dati da usare nella ricerca
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Ricerca per parole chiave, è inutile ricercare per nome utente perchè
        # viene definito da Facebook e non dalla persona
        keywords = search_data['keywords_list']
        keywords.extend(search_data['usernames_list'])
        list(set(keywords))

        for keyword in keywords:
            ps = fb_scraper.find_user_by_keywords(keyword)
            possibile_profiles.extend(ps)

        # Filtra profili (ricerche ridondanti)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # I profili vengono preparati per il confronto
        # Nel loop esegue anche il confronto tra i possibili profili Facebook e i profili già presenti per il profilo.
        # (si calcola la somma di tutti i confronti).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for fbp in possibile_profiles:
            fbp.elaborate_images(fb_scraper)

            # Esegue i confronti ed eventualmente salva il profilo
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(fbp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = fbp

        # Una volta terminati i confronti si aggiunge il profilo migliore (se è
        # stato trovato)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        else:
            return 0

    def find_twitter_profile(self, tw_scraper, *custom_keywords):
        '''
        In base ai dati che possiede ricerca il profilo Twitter della persona

        Params:
        @tw_scraper: Istanza di scrape_functions.tw_scraper utilizzata per cercare gli utenti
        @custom_keywords: Elenco di parole chiave aggiuntive da usare nella ricerca

        Return:
        Valore del match migliore
        '''

        # Variabili locali
        possibile_profiles = []

        # Ottiene i dati da usare nella ricerca
        search_data = self._prepare_search_data([k for k in custom_keywords])

        # Ricerca per nomi utenti
        for username in search_data['usernames_list']:
            p = tw_scraper.find_user_by_username(username)
            if p is not None:
                possibile_profiles.append(p)

        # Ricerca per parole chiave
        for keyword in search_data['keywords_list']:
            tw_profiles = tw_scraper.find_user_by_keywords(keyword)
            if tw_profiles is not None:
                possibile_profiles.extend(tw_profiles)

        # Filtra profili (ricerche ridondanti)
        possibile_profiles = list({p for p in possibile_profiles if p is not None}) # Set comprehension

        # Una volta individuati i possibili profili li converte negli oggetti
        # profiles.instagram_profile e li preprara per il confronto.
        # Nel loop esegue anche il confronto tra i possibili profili Instagram e i profili già presenti per il profilo.
        # (si calcola la somma di tutti i confronti).
        best_profile = None
        best_match = MIN_MATCH_THREESHOLD
        for twp in possibile_profiles:
            twp.elaborate_images(tw_scraper)

            # Esegue i confronti ed eventualmente salva il profilo
            tot_match = 0
            for p in self.profiles:
                tot_match += p.compare_profile(twp)
            if tot_match > best_match:
                best_match = tot_match
                best_profile = twp

        # Una volta terminati i confronti si aggiunge il profilo migliore (se è
        # stato trovato)
        if best_profile is not None:
            self.add_profile(best_profile)
            return best_match
        else:
            return 0
