from sqlalchemy import Column, Integer, String, JSON, DateTime
from database import Base
import datetime

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String)
    payer = Column(String)
    state = Column(String)
    docs = Column(JSON)
    query_text = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)