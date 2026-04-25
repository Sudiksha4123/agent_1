from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, Table, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    created_at = Column(DateTime, default=func.utcnow)

    syllabi = relationship("Syllabus", back_populates="user")  # ✅ NEW
    plans = relationship("Plan", back_populates="user")
    responses = relationship("Response", back_populates="user")
    profile = relationship("Profile", uselist=False, back_populates="user")

class Syllabus(Base):
    __tablename__ = "syllabus"

    syllabus_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))  # ✅ NEW

    course_name = Column(String, nullable=False)
    handout = Column(Text)
    upload_at = Column(DateTime, default=func.utcnow)

    user = relationship("User", back_populates="syllabi")

class Plan(Base):
    __tablename__ = "plans"

    plan_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    syllabus_id = Column(Integer, ForeignKey("syllabus.syllabus_id"), nullable=True)  # ✅ OPTIONAL

    start_date = Column(DateTime)
    end_date = Column(DateTime)
    topics = Column(Text)
    recommended_diffi = Column(String)
    study_plan = Column(Text)

    user = relationship("User", back_populates="plans")
    syllabus = relationship("Syllabus")
    quizzes = relationship("Quiz", back_populates="plan")  # ✅ NEW

class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.plan_id"))  # ✅ NEW

    topics = Column(Text)
    difficulty = Column(String)
    mcqs = Column(Text)
    subjective = Column(Text)
    generated_at = Column(DateTime, default=func.utcnow)

    plan = relationship("Plan", back_populates="quizzes")  # ✅ NEW
    responses = relationship("Response", back_populates="quiz")

class Response(Base):
    __tablename__ = "responses"

    response_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"))

    answers = Column(Text)
    submitted_at = Column(DateTime, default=func.utcnow)

    user = relationship("User", back_populates="responses")
    quiz = relationship("Quiz", back_populates="responses")

    evaluation = relationship("Evaluation", uselist=False, back_populates="response")

class Evaluation(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    response_id = Column(Integer, ForeignKey("responses.response_id"))

    overall_score = Column(Float)
    overall_total = Column(Float)
    final_feedback = Column(Text)
    generated_at = Column(DateTime, default=func.utcnow)

    response = relationship("Response", back_populates="evaluation")
    topic_scores = relationship("TopicScoreDB", back_populates="evaluation", cascade="all, delete-orphan")

class TopicScoreDB(Base):
    __tablename__ = "topic_scores"

    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.evaluation_id"))

    topic = Column(String)
    score = Column(Float)
    total = Column(Float)
    understanding_score = Column(Float)
    feedback = Column(Text)

    evaluation = relationship("Evaluation", back_populates="topic_scores")

class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    total_quiz = Column(Integer, default=0)
    overall_avg = Column(Float)

    user = relationship("User", back_populates="profile")