import random
from payers.base import BasePayer

class ParamountPayer(BasePayer):

    def submit(self, case):
        return "EMAIL_SENT"

    def get_response(self, case):
        return random.choice(["QUERY", "REJECTED"])