import logging
from payers.base import BasePayer

logger = logging.getLogger("Payer.CGHS")


class CGHSPayer(BasePayer):
    """
    CGHS (Central Government Health Scheme) — Physical forms + in-person submission.

    Real-world flow:
    1. submit():  Print the pre-auth form, attach physical copies of documents,
                  and submit in person or via courier to the CGHS office.
                  The agent CANNOT automate this — it can only pre-fill the form
                  and flag the case for manual submission.
    2. get_response():  Response comes via physical letter or phone call.
                        No digital channel exists. Must be manually entered.

    CGHS is the payer that cannot be meaningfully automated.
    The agent's role here is limited to: pre-filling the form template,
    flagging the case as ready for manual submission, and tracking the SLA.
    """

    CHANNEL = "physical"

    def submit(self, case) -> dict:
        logger.warning("[CGHS] ⚠️ Physical submission required — cannot automate.")
        logger.info(f"[CGHS] Pre-filling form template for patient={case.patient_id}")
        logger.info(f"[CGHS] Documents prepared for print: {case.docs}")
        logger.warning("[CGHS] Flagging case for manual courier/in-person submission.")
        # In production: generate a pre-filled PDF form and notify billing team
        return {"status": "FLAGGED_FOR_MANUAL", "message": "CGHS requires physical submission"}

    def get_response(self, case) -> str:
        # In production: billing team manually enters response after receiving physical letter
        logger.warning("[CGHS] ⚠️ No digital response channel — response is physical letter or phone.")
        logger.warning("[CGHS] Waiting for human to enter TPA response into system.")
        return "PENDING"  # Always pending until human enters result
