# Adaptive Course Planner

## Overview

* Backend system for generating quizzes and evaluating learner performance.
* Developed as a **semester project** focusing on backend architecture first.
* Uses an **LLM (gpt-oss-20b)** to generate quizzes and evaluate answers.
* Designed to support **adaptive learning systems** where assessments can later be used to adjust course difficulty.

---

## Features Implemented

* Quiz generation based on **topic and difficulty level**.
* Each quiz contains 10 questions
* MCQs include:

  * Question
  * Four options
  * Correct answer
  * Explanation
* Subjective questions include:
* 
  * Evaluation points for grading.
* Answer evaluation system that:

  * Checks MCQ answers
  * Evaluates subjective responses using the LLM
  * Generates feedback and performance score.

---

## API Endpoints

* **POST /generate-quiz**

  * Input: topic and difficulty
  * Output: structured quiz

* **POST /evaluate**

  * Input: user answers
  * Output: score and feedback

* **POST /update-profile**

  * Updates user learning profile information.

---

## Technologies Used

* Python
* FastAPI
* Pydantic
* JSON parsing
* **gpt-oss-20b LLM**

---

## Project Structure

* `main.py` – FastAPI application and API endpoints
* `schemas.py` – Pydantic models for quiz and evaluation structures
* `assess_agent.py` – logic for quiz generation and evaluation using the LLM
* `requirements.txt` – project dependencies

---

## Current Development Stage

* Quiz generation implemented
* Answer evaluation implemented
* API endpoints created
* Structured output using Pydantic models
* Backend ready for future database integration and frontend development

---

## Future Improvements

* User performance tracking
* Adaptive difficulty adjustment
* Database integration
* Learning progress analytics
* Frontend interface for learners

