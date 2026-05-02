import random
import logging
from payers.base import BasePayer

logger = logging.getLogger("Payer.StarHealth")


class StarHealthPayer(BasePayer):
    """
    Star Health — REST API channel.

    Real-world flow:
    1. submit():  POST /api/v1/preauth with JSON payload.
                  Synchronous API returns a tracking ID + sometimes an instant decision.
    2. get_response():  GET /api/v1/preauth/{tracking_id}/status
                        Returns current decision status.

    Star Health is the easiest payer to integrate because it has a proper API.
    In this prototype, both steps are simulated.
    """

    CHANNEL = "rest_api"

    def submit(self, case) -> dict:
        logger.info(f"[StarHealth] POST /api/v1/preauth — patient={case.patient_id}")
        logger.info(f"[StarHealth] Payload: docs={case.docs}")
        # In production: requests.post("https://api.starhealth.in/v1/preauth", json=payload)
        return {"status": "SUBMITTED", "tracking_id": f"SH-{case.id:05d}"}

    def get_response(self, case) -> str:
        # In production: requests.get(f"https://api.starhealth.in/v1/preauth/{tracking_id}/status")
        logger.info("[StarHealth] GET /api/v1/preauth/status — polling REST API...")
        return random.choice(["APPROVED", "QUERY", "REJECTED"])