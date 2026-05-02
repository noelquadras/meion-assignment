import random
from payers.base import BasePayer

class MediAssistPayer(BasePayer):

    def submit(self, case):
        return "SUBMITTED"

    def get_response(self, case):
        return random.choice(["APPROVED", "QUERY", "REJECTED"])