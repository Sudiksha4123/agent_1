from fastapi import FastAPI
from assess_agent import generate_quiz, generate_eval
from schema import Quiz, QuizSubmission, QuizEvaluationRequest, EvaluationResponse
import random

app=FastAPI()

@app.get("/")
def home():
    return {"message": "Quiz AI backend running"}

@app.post("/quiz/generate", response_model=Quiz)
def generate_quiz_endpoint(topic: str, difficulty: str):
    quiz = generate_quiz(topic, difficulty)
    return quiz

@app.post("/quiz/evaluate", response_model=EvaluationResponse)
def evaluate_quiz(request: QuizEvaluationRequest):

    quiz_dict = request.quiz.model_dump()
    submission_dict = request.submission.model_dump()

    evaluation = generate_eval(quiz_dict, submission_dict)

    return evaluation



   