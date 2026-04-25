from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://postgres:1234@localhost:5432/course_planner"

engine = create_engine(DATABASE_URL)
conn = engine.connect()
print("Connected!")
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()