from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, SessionLocal
from models import Case
from state_machine import State
from agent import process_case

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from pydantic import BaseModel
from typing import List

class CaseCreate(BaseModel):
    patient_id: str
    payer: str
    docs: List[str]

@app.post("/create-case/")
def create_case(case_req: CaseCreate, db = Depends(get_db)):
    case = Case(
        patient_id=case_req.patient_id,
        payer=case_req.payer,
        state=State.ADMISSION,
        docs=case_req.docs
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"case_id": case.id}



@app.post("/start-case/{case_id}")
def start_case(case_id: int, background_tasks: BackgroundTasks, db = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {"error": "Case not found"}, 404
        
    if case.state != State.ADMISSION:
        return {"status": "already started or completed", "state": case.state}

    # Instead of passing the request's db session to the background task (which will be closed
    # right after the response), we pass the case ID and let the background task create its own session.
    background_tasks.add_task(process_case_bg, case_id)
    return {"status": "processing started"}


def process_case_bg(case_id: int):
    """Wrapper to create a new DB session for the background task"""
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case:
            process_case(db, case)
    finally:
        db.close()

@app.get("/case/{case_id}")
def get_case(case_id: int, db = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {"error": "Case not found"}, 404

    return {
        "id": case.id,
        "state": case.state,
        "payer": case.payer,
        "docs": case.docs,
        "query": case.query_text
    }