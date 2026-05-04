from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, Table, DateTime, JSON, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password = Column(String)
    created_at = Column(DateTime, default=func.now())

    syllabi = relationship("Syllabus", back_populates="user")  # ✅ NEW
    plans = relationship("Plan", back_populates="user")
    responses = relationship("Response", back_populates="user")
    profile = relationship("Profile", back_populates="user", cascade="all,delete")

class Course(Base):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))

    name = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    created_at = Column(DateTime, default=func.now())

    user = relationship("User")
    plans = relationship("Plan", back_populates="course")
    syllabus = relationship("Syllabus", back_populates="course")
    profile = relationship("Profile", back_populates="course")

class Syllabus(Base):
    __tablename__ = "syllabus"

    syllabus_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)  # ✅ REQUIRED

    course_name = Column(String, nullable=False)
    handout = Column(Text)
    upload_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="syllabi")
    course = relationship("Course", back_populates="syllabus")

class Plan(Base):
    __tablename__ = "plans"

    plan_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    syllabus_id = Column(Integer, ForeignKey("syllabus.syllabus_id"), nullable=True) # ✅ OPTIONAL
    course_id = Column(Integer, ForeignKey("courses.course_id"))  # ADD THIS  

    start_date = Column(DateTime)
    end_date = Column(DateTime)
    # days_left = Column(Integer)
    topics = Column(JSON)
    recommended_difficulty = Column(String)
    study_plan = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="plans")
    course = relationship("Course", back_populates="plans")
    syllabus = relationship("Syllabus")
    quizzes = relationship("Quiz", back_populates="plan", cascade="all, delete")

class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.plan_id"), nullable=False)  # ✅ NEW

    topics = Column(JSON)
    difficulty = Column(String)
    mcqs = Column(JSON)
    subjective = Column(JSON)
    is_attempted = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=func.now())

    plan = relationship("Plan", back_populates="quizzes")  # ✅ NEW
    responses = relationship("Response", back_populates="quiz", cascade="all, delete")

class Response(Base):
    __tablename__ = "responses"

    response_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"), nullable=False)

    answers = Column(Text)
    submitted_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="responses")
    quiz = relationship("Quiz", back_populates="responses")

    evaluation = relationship(
    "Evaluation",
    uselist=False,
    back_populates="response",
    cascade="all, delete-orphan"
)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz_response'),
    )

class Evaluation(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey("responses.response_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))

    overall_score = Column(Float)
    overall_total = Column(Float)
    final_feedback = Column(Text)
    generated_at = Column(DateTime, default=func.now())

    response = relationship("Response", back_populates="evaluation")
    topic_scores = relationship("TopicScoreDB", back_populates="evaluation", cascade="all, delete-orphan")

class TopicScoreDB(Base):
    __tablename__ = "topic_scores"

    id=Column(Integer, primary_key=True, index=True)
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
    course_id = Column(Integer, ForeignKey("courses.course_id"), primary_key=True)

    total_quiz = Column(Integer, default=0)
    overall_avg = Column(Float, default=0.0)

    user = relationship("User", back_populates="profile")
    course = relationship("Course", back_populates="profile")