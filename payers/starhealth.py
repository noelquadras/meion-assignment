import random
from payers.base import BasePayer

class StarHealthPayer(BasePayer):

    def submit(self, case):
        return {"status": "OK"}

    def get_response(self, case):
        return random.choice(["APPROVED", "QUERY"])