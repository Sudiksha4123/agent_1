import json
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.assess_agent import get_latest_plan, generate_quiz, generate_eval
# from services.build_profile import update_profile, generate_profile
# from services.planner_agent import fetch_profile, generate_plan
from workflow import run_quiz_pipeline
from schema import QuizRequest, QuizSet, MCQ, SubjectiveQuestion, QuizSubmission, EvaluationResponse, ProfileResponse,TopicPerformance, PlanResponse
from models import Evaluation, TopicScoreDB, Quiz, Plan
app=FastAPI()

@app.get("/")
def home():
    return {"message": "Quiz AI backend running"}

app = FastAPI()


@app.post("/quiz/generate", response_model=QuizSet)
def generate_quiz_endpoint(request: QuizRequest, db: Session = Depends(get_db)):

    try:
        plan = get_latest_plan(request.user_id, request.course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    print("PLAN.TOPICS RAW:", repr(plan.topics))
    print("TYPE:", type(plan.topics))

    topics = plan.topics
    difficulty = plan.recommended_difficulty

    quiz = generate_quiz(topics, difficulty)

    db_quiz = Quiz(
        plan_id=plan.plan_id,  
        topics=topics,
        difficulty=difficulty,
        mcqs=json.dumps([mcq.model_dump() for mcq in quiz.mcqs]),
        subjective=json.dumps([q.model_dump() for q in quiz.subjective]),
        is_attempted=False
    )

    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)

    return QuizSet(
        quiz_id=db_quiz.quiz_id,
        topics=topics,
        difficulty=difficulty,
        mcqs=[
            MCQ(**mcq.model_dump(), question_id=i + 1)
            for i, mcq in enumerate(quiz.mcqs)
        ],
        subjective=[
            SubjectiveQuestion(**q.model_dump(), question_id=i + 1)
            for i, q in enumerate(quiz.subjective)
        ],
    )

@app.post("/quiz/submit")
def submit_quiz(request: QuizSubmission, db: Session = Depends(get_db)):
    # try:
        result = run_quiz_pipeline(request, db)
        return result

    # except Exception as e:
    #     db.rollback()
    #     raise HTTPException(status_code=500, detail=str(e))