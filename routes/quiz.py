from fastapi import APIRouter, HTTPException, WebSocket

router17 = APIRouter()

DEPRECATED_QUIZ_MESSAGE = "Quiz endpoints are deprecated and no longer available."


def raise_quiz_deprecated() -> None:
    raise HTTPException(status_code=410, detail=DEPRECATED_QUIZ_MESSAGE)


@router17.websocket("/quiz-notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.close(code=1008, reason=DEPRECATED_QUIZ_MESSAGE)


@router17.post("/create-quiz", tags=["Quiz"], deprecated=True)
async def create_quiz():
    raise_quiz_deprecated()


@router17.post("/submit-quiz/{quiz_id}", tags=["Quiz"], deprecated=True)
async def submit_quiz(quiz_id: str):
    raise_quiz_deprecated()


@router17.get("/quiz-attempts/count", tags=["Quiz"], deprecated=True)
async def get_quiz_attempt_count():
    raise_quiz_deprecated()


@router17.get("/quiz-attempts/correct-count", tags=["Quiz"], deprecated=True)
async def get_correct_quiz_attempt_count():
    raise_quiz_deprecated()
