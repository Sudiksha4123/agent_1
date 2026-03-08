from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import date

# To generate quiz
class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

class SubjectiveQuestion(BaseModel):
    question: str
    evaluation_points: List[str]

class Quiz(BaseModel):
    topic: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    mcqs: List[MCQ]
    subjective: List[SubjectiveQuestion]

# Submitted answers
class UserAnswer(BaseModel):
    question: str
    selected_answer: str

class QuizSubmission(BaseModel):
    answers: List[UserAnswer] 

# until there is no database
class QuizEvaluationRequest(BaseModel):
    quiz: Quiz
    submission: QuizSubmission
    
#For Evaluation
class TopicScore(BaseModel):
    topic: str
    score: int
    total: int
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

class ProfileResponse(BaseModel):
    user_id: str
    total_quizzes: int
    overall_average: float
    topic_performance: List[TopicPerformance]
    strong_topics: List[str]
    weak_topics: List[str]
    last_quiz_score: Optional[float] = None

# To generate plan
class TopicPlan(BaseModel):
    topic: str
    focus_areas: List[str]
    study_tips: str

class PlanResponse(BaseModel):
    user_id: str
    
    # Timeline
    start_date: date
    end_date: date
    total_duration_days: int
    total_days_left: int

    # Plan configuration
    generated_for_topics: List[str]
    recommended_difficulty: Literal["easy", "medium", "hard"]

    # Study breakdown
    study_plan: List[TopicPlan]

    # Optional tracking
    daily_time_commitment_minutes: Optional[int] = None
