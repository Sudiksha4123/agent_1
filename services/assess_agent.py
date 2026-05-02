import json
from pydantic import ValidationError 
from openai import OpenAI
from schema import QuizInternal, EvaluationResponse
from models import Plan
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
    timeout=30.0,
    max_retries=3
)

def get_latest_plan(user_id: int, course_id: int, db: Session) -> Plan:
    plan = (db.query(Plan).filter(Plan.user_id == user_id, Plan.course_id == course_id).order_by(Plan.created_at.desc()).first())

    if not plan:
        raise ValueError("No plan found for this course")

    return plan

def generate_quiz(topics: list[str], difficulty: str):
    prompt = f"""
You are an expert assessment designer.

Generate questions:
- MCQs
- subjective questions

Generate 10 questions in a way that the topics are properly assessed.
Both MCQs and Subjective Questions and REQUIRED. The quiz should be a proper mix of MCQs and Subjective Questions for all round assessment.

Topics: {topics}
Difficulty: {difficulty}

Rules:
- Questions should be distributed across all topics
- Do not focus on only one topic
- Each MCQ must have 4 options
- Include correct answer
- Include explanation
- Each subjective question must include evaluation points

Return STRICT JSON matching this format:

{{
  "topics": [],
  "difficulty": "",
  "mcqs": [
    {{
      "question": "",
      "options": ["", "", "", ""],
      "correct_answer": "",
      "explanation": ""
    }}
  ],
  "subjective": [
    {{
      "question": "",
      "evaluation_points": ["", ""]
    }}
  ]
}}

Both MCQs and the Subjective questions MUST be present.
Do not omit any fields.
Do NOT include explanations, comments, or extra text.
"""

    completion = client.chat.completions.create(
    model=os.environ["MODEL_NAME"],
    temperature=0.3,
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "quiz_schema",
            "schema": QuizInternal.model_json_schema()
        }
    },
)

    content = completion.choices[0].message.content
    if isinstance(content, list):
        content = content[0].get("text", "")

    content = (content or "").strip()
    
    print("\n===== LLM RESPONSE =====")
    print(content)
    print("========================\n")
    
    #Prints json
    try:
        quiz_dict = json.loads(content)
        quiz = QuizInternal.model_validate(quiz_dict)
        return quiz
    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")
    except ValidationError as e:
        raise ValueError(f"Invalid quiz structure: {e}")

def generate_eval(quiz: dict, mcq_answers, subjective_answers) -> EvaluationResponse:

    prompt = f"""
You are an expert evaluator.

Given the quiz and user answers below:

Match each user answer with the corresponding question using `question_id`.

Use `question_id` to match each user answer with the corresponding question.

QUIZ:
{json.dumps(quiz, indent=2)}

MCQ ANSWERS:
{json.dumps([a.model_dump() for a in mcq_answers], indent=2)}

SUBJECTIVE ANSWERS:
{json.dumps([a.model_dump() for a in subjective_answers], indent=2)}

Task:
1. For EACH question, assign EXACTLY ONE topic from the provided list.
2. Do NOT create new topics.
3. Do NOT leave any question unassigned.
4. Choose the MOST relevant topic based on the concept tested.

Then:
- Group questions by assigned topic
- Evaluate answers topic-wise
- Calculate score and total per topic
- Assign understanding_score (0–100) per topic
- The understanding score should consider correctness and depth of explanation.
- Provide feedback per topic and overall
- Calculate overall score and total.
- Provide constructive feedback per topic.
- Provide final overall feedback.

Return ONLY valid JSON.

Required JSON format:

{{
  "topic_scores": [
    {{
      "topic": "string",
      "score": 0,
      "total": 0,
      "topic_understanding_score": 0,
      "feedback": "string"
    }}
  ],
  "overall_score": 0,
  "overall_total": 0,
  "final_feedback": "string"
}}
"""
  

    completion = client.chat.completions.create(
    model=os.environ["MODEL_NAME"],
    temperature=0.5,
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "evaluation_schema",
            "schema": EvaluationResponse.model_json_schema()
        }
    },
)

    content = completion.choices[0].message.content
    if isinstance(content, list):
        content = content[0].get("text", "")  

    content = (content or "").strip()

    try:
        evaluation_dict = json.loads(content)
        evaluation = EvaluationResponse.model_validate(evaluation_dict)
        return evaluation

    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")

    except ValidationError as e:
        raise ValueError(f"Invalid evaluation structure: {e}")