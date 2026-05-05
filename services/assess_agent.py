import json
from pydantic import ValidationError 
from openai import OpenAI
from schema import QuizInternal, EvaluationResponse
from models import Plan
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import time
import os
import re

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
    timeout=30.0,
    max_retries=2
)

MAX_RETRIES = 3

def extract_json(content: str) -> dict:
    content = content.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if match:
        content = match.group(1).strip()
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1:
        content = content[start:end+1]
    return json.loads(content)

def get_latest_plan(user_id: int, course_id: int, db: Session) -> Plan:
    plan = (db.query(Plan)
            .filter(
                Plan.user_id == user_id,
                Plan.course_id == course_id,
                Plan.is_initial == False  # never quiz from the course map
            )
            .order_by(Plan.created_at.desc())
            .first())
    if not plan:
        raise ValueError("No sprint plan found. Complete your first study session first.")
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
  "topics": {json.dumps(topics)},
  "difficulty": "{difficulty}" ,
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

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Quiz generation attempt {attempt}/{MAX_RETRIES}")
            completion = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                temperature=max(0.1, 0.3 - (attempt - 1) * 0.1),  # lower temp on retry
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )

            content = completion.choices[0].message.content
            if isinstance(content, list):
                content = content[0].get("text", "")
            content = (content or "").strip()

            print(f"\n===== QUIZ LLM RESPONSE (attempt {attempt}) =====")
            print(content[:500])
            print("=================================================\n")

            quiz_dict = extract_json(content)

            # fix difficulty casing
            diff = quiz_dict.get("difficulty", difficulty)
            if isinstance(diff, str):
                diff_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
                quiz_dict["difficulty"] = diff_map.get(diff.lower(), difficulty.capitalize())

            # ensure topics is set
            if not quiz_dict.get("topics"):
                quiz_dict["topics"] = topics

            quiz = QuizInternal.model_validate(quiz_dict)

            # sanity checks
            if not quiz.mcqs:
                raise ValueError("No MCQs in response")
            if not quiz.subjective:
                raise ValueError("No subjective questions in response")

            return quiz

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)  # 2s, 4s backoff
            continue

    raise ValueError(f"Quiz generation failed after {MAX_RETRIES} attempts: {last_error}")

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
- Calculate score and total per topic:
   - MCQ: 1 if correct, 0 if wrong
   - Subjective: score between 0.0 and 2.0 based on how well evaluation_points are addressed
     - 2.0 = all points addressed clearly
     - 1.0 = partial understanding, some points addressed
     - 0.5 = minimal understanding
     - 0.0 = completely wrong or blank
   - score and total CAN be decimals
- topic_understanding_score (integer 0-100) reflects DEPTH of understanding:
   - Only 1 question for this topic → cap at 60 maximum
   - Multiple questions answered perfectly with detailed explanations → 85-100
   - Mostly correct with minor gaps → 70-85
   - Partially correct → 50-69
   - Poor understanding → below 50
   - Blank or completely wrong → below 20
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
  

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Evaluation attempt {attempt}/{MAX_RETRIES}")
            completion = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                temperature=max(0.1, 0.5 - (attempt - 1) * 0.1),
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )

            content = completion.choices[0].message.content
            if isinstance(content, list):
                content = content[0].get("text", "")
            content = (content or "").strip()

            print(f"\n===== EVAL LLM RESPONSE (attempt {attempt}) =====")
            print(content[:500])
            print("=================================================\n")

            evaluation_dict = extract_json(content)
            evaluation = EvaluationResponse.model_validate(evaluation_dict)

            if not evaluation.topic_scores:
                raise ValueError("No topic scores in response")

            return evaluation

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue

    raise ValueError(f"Evaluation failed after {MAX_RETRIES} attempts: {last_error}")