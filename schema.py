from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import date

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
#===============
# To request quiz generation
class QuizRequest(BaseModel):
    course_id: int
# ===============
# To generate quiz
class MCQInternal(BaseModel):
    # question_id: Optional[int] = None
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None


class SubjectiveInternal(BaseModel):
    # question_id: Optional[int] = None
    question: str
    evaluation_points: List[str]


class QuizInternal(BaseModel):
    topics: List[str]
    difficulty: Literal["Easy", "Medium", "Hard"]
    mcqs: List[MCQInternal]
    subjective: List[SubjectiveInternal]
# =================
# For API responses
class MCQ(BaseModel):
    question_id: int
    question: str
    options: List[str]


class SubjectiveQuestion(BaseModel):
    question_id: int
    question: str


class QuizSet(BaseModel):
    quiz_id: int
    topics: List[str]
    difficulty: Literal["Easy", "Medium", "Hard"]
    mcqs: List[MCQ]
    subjective: List[SubjectiveQuestion]
# ===============================
# Submitted answers

class MCQAnswer(BaseModel):
    question_id: int
    selected_option: str


class SubjectiveAnswer(BaseModel):
    question_id: int
    answer_text: str


class QuizSubmission(BaseModel):
    course_id: int
    quiz_id: int
    mcq_answers: List[MCQAnswer]
    subjective_answers: List[SubjectiveAnswer]
# ===========================================
# # until there is no database
# class QuizEvaluationRequest(BaseModel):
#     quiz: QuizSet
#     submission: QuizSubmission
    
#For Evaluation
class TopicScore(BaseModel):
    topic: str
    score: int
    total: int
    topic_understanding_score: int
    feedback: str

class EvaluationResponse(BaseModel):
    topic_scores: List[TopicScore]
    overall_score: int
    overall_total: int
    final_feedback: str

 #To update profile   
class TopicPerformance(BaseModel):
    topic: str
    average_score: float
    quizzes_attempted: int
    understanding_score: float  


class ProfileResponse(BaseModel):
    user_id: int
    total_quizzes: int
    overall_average: float
    topic_performance: List[TopicPerformance]

# To generate plan
class TopicPlan(BaseModel):
    topic: str
    focus_areas: List[str]
    study_tips: str



class PlanResponse(BaseModel):
    start_date: date
    end_date: date
    topics: List[str]
    recommended_difficulty: Literal["Easy", "Medium", "Hard"]
    study_plan: List[TopicPlan]
    daily_time_commitment: Optional[int] = None
