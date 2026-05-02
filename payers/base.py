class BasePayer:
    def submit(self, case):
        raise NotImplementedError

    def get_response(self, case):
        raise NotImplementedError