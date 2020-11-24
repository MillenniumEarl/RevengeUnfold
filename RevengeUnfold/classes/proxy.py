from fp.fp import FreeProxy


class proxy:
    def __init__(self, country_code_list=None):
        self.country_code_list = country_code_list
        self.proxy = None

    def get(self, rand=True):
        if self.country_code_list is not None:
            self.proxy = FreeProxy(
                country_id=self.country_code_list,
                rand=rand,
                timeout=5).get()
            if not 'http' in self.proxy:
                self.proxy = None
            return self.proxy
        self.proxy = FreeProxy(rand=rand).get()
        if not 'http' in self.proxy:
            self.proxy = None
        return self.proxy
