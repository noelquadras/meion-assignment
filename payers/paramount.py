import random
import logging
from payers.base import BasePayer

logger = logging.getLogger("Payer.Paramount")


class ParamountPayer(BasePayer):
    """
    Paramount — Email submission + Phone-only follow-up.

    Real-world flow:
    1. submit():  Compose and send an email with pre-auth form + doc attachments
                  to Paramount's submissions inbox. No portal, no API.
    2. get_response():  There is NO digital response channel.
                        Follow-up is phone-only. The agent cannot poll for a response
                        automatically — it must flag the case for a human to call.

    This is the hardest payer to automate. The agent can automate submission
    (send the email) but must escalate the follow-up to the billing team.
    In this prototype, both steps are simulated.
    """

    CHANNEL = "email_phone"

    def submit(self, case) -> dict:
        logger.info(f"[Paramount] Composing email to submissions@paramount.in")
        logger.info(f"[Paramount] Attaching documents: {case.docs}")
        # In production: smtplib or SendGrid to send email with PDF attachments
        return {"status": "EMAIL_SENT", "message": "Pre-auth emailed to Paramount"}

    def get_response(self, case) -> str:
        # In production: this CANNOT be automated — phone-only follow-up.
        # The agent should flag this for the billing team to call Paramount.
        logger.warning("[Paramount] ⚠️ No digital response channel — follow-up is phone-only.")
        logger.warning("[Paramount] Flagging case for human phone follow-up.")
        # Simulated: randomly return a result as if a human entered it after calling
        return random.choice(["APPROVED", "QUERY", "REJECTED"])