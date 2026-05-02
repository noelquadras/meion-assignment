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


@app.post("/create-case/")
def create_case(patient_id: str, payer: str):

    db = SessionLocal()

    case = Case(
        patient_id=patient_id,
        payer=payer,
        state=State.ADMISSION,
        docs=["id_proof", "insurance_card"]
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return {"case_id": case.id}


@app.post("/start-case/{case_id}")
def start_case(case_id: int, background_tasks: BackgroundTasks):

    db = SessionLocal()
    case = db.query(Case).filter(Case.id == case_id).first()

    background_tasks.add_task(process_case, db, case)

    return {"status": "processing started"}


@app.get("/case/{case_id}")
def get_case(case_id: int):

    db = SessionLocal()
    case = db.query(Case).filter(Case.id == case_id).first()

    return {
        "id": case.id,
        "state": case.state,
        "payer": case.payer,
        "docs": case.docs,
        "query": case.query_text
    }