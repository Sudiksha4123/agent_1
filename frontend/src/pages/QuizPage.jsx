import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api/axios'

const STEPS = {
  LOADING: 'loading',
  QUIZ: 'quiz',
  SUBMITTING: 'submitting',
  RESULT: 'result',
  EVAL_ERROR: 'eval_error',
  QUIZ_ERROR: 'quiz_error'
}

export default function QuizPage() {
  const [searchParams] = useSearchParams()
  const courseId = searchParams.get('course_id')
  const navigate = useNavigate()

  const [step, setStep] = useState(STEPS.LOADING)
  const [quiz, setQuiz] = useState(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [mcqAnswers, setMcqAnswers] = useState({})
  const [subjectiveAnswers, setSubjectiveAnswers] = useState({})

  useEffect(() => {
    if (!courseId) { navigate('/dashboard'); return }
    generateQuiz()
  }, [])

  const generateQuiz = async () => {
    setStep(STEPS.LOADING)
    setError('')
    setMcqAnswers({})
    setSubjectiveAnswers({})
    try {
      const res = await api.post('/quiz/generate', { course_id: parseInt(courseId) })
      setQuiz(res.data)
      setStep(STEPS.QUIZ)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate quiz')
      setStep(STEPS.QUIZ_ERROR)
    }
  }

  const handleMcqAnswer = (questionId, selectedOption) => {
    setMcqAnswers({ ...mcqAnswers, [questionId]: selectedOption })
  }

  const handleSubjectiveAnswer = (questionId, text) => {
    setSubjectiveAnswers({ ...subjectiveAnswers, [questionId]: text })
  }

  const allAnswered = () => {
    if (!quiz) return false
    const mcqDone = quiz.mcqs.every(q => mcqAnswers[q.question_id])
    const subDone = quiz.subjective.every(q => subjectiveAnswers[q.question_id]?.trim())
    return mcqDone && subDone
  }

  const submitQuiz = async () => {
    setStep(STEPS.SUBMITTING)
    try {
      const payload = {
        course_id: parseInt(courseId),
        quiz_id: quiz.quiz_id,
        mcq_answers: quiz.mcqs.map(q => ({
          question_id: q.question_id,
          selected_option: mcqAnswers[q.question_id] || ''
        })),
        subjective_answers: quiz.subjective.map(q => ({
          question_id: q.question_id,
          answer_text: subjectiveAnswers[q.question_id] || ''
        }))
      }
      const res = await api.post('/quiz/submit', payload)
      setResult(res.data)
      setStep(STEPS.RESULT)
    } catch (err) {
      setError(err.response?.data?.detail || 'Evaluation failed')
      setStep(STEPS.EVAL_ERROR) // quiz stays intact, only eval failed
    }
  }

  // retry evaluation only — quiz stays the same
  const retryEvaluation = async () => {
    setError('')
    await submitQuiz()
  }

  // ── Loading ──
  if (step === STEPS.LOADING) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center gap-4">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">Generating your quiz...</p>
      </div>
    )
  }

  // ── Quiz generation error ──
  if (step === STEPS.QUIZ_ERROR) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-red-400 mb-2">Failed to generate quiz</p>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={generateQuiz}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg transition">
              Try Again
            </button>
            <button onClick={() => navigate('/dashboard')}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm px-4 py-2 rounded-lg transition">
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Evaluation error — show quiz again with retry ──
  if (step === STEPS.EVAL_ERROR) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-red-400 mb-2">Evaluation failed</p>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={retryEvaluation}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg transition">
              Retry Evaluation
            </button>
            <button onClick={() => navigate('/dashboard')}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm px-4 py-2 rounded-lg transition">
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Submitting ──
  if (step === STEPS.SUBMITTING) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center gap-4">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">Evaluating your answers...</p>
      </div>
    )
  }

  // ── Result ──
  if (step === STEPS.RESULT && result) {
    return (
      <div className="min-h-screen bg-gray-950 text-white px-4 py-10">
        <div className="max-w-2xl mx-auto">
          <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800 text-center mb-6">
            <p className="text-gray-400 text-sm mb-2">Overall Score</p>
            <p className="text-6xl font-bold text-indigo-400 mb-1">
              {result.overall_score}
              <span className="text-3xl text-gray-500">/{result.overall_total}</span>
            </p>
            <p className="text-gray-400 text-sm mt-4">{result.final_feedback}</p>
          </div>

          {result.topic_scores?.length > 0 && (
            <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 mb-6">
              <h3 className="font-semibold text-white mb-4">Topic Breakdown</h3>
              <div className="space-y-4">
                {result.topic_scores.map((t, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm text-white">{t.topic}</p>
                      <p className="text-sm text-gray-400">{t.score}/{t.total}</p>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${Math.min((t.score / t.total) * 100, 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{t.feedback}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={generateQuiz}
              className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2.5 rounded-lg transition">
              Take Another Quiz
            </button>
            <button onClick={() => navigate('/dashboard')}
              className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium py-2.5 rounded-lg transition">
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Quiz ──
  return (
    <div className="min-h-screen bg-gray-950 text-white px-4 py-10">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold">Quiz</h2>
            <p className="text-sm text-gray-400 mt-1">
              {quiz?.topics?.join(', ')} · {quiz?.difficulty}
            </p>
          </div>
          <button onClick={() => navigate('/dashboard')}
            className="text-sm text-gray-400 hover:text-white transition">
            ← Dashboard
          </button>
        </div>

        {quiz?.mcqs?.length > 0 && (
          <div className="mb-8">
            <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">Multiple Choice</h3>
            <div className="space-y-5">
              {quiz.mcqs.map((q) => (
                <div key={q.question_id} className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                  <p className="text-sm text-white font-medium mb-4">
                    <span className="text-indigo-400 mr-2">Q{q.question_id}.</span>
                    {q.question}
                  </p>
                  <div className="space-y-2">
                    {q.options.map((option, i) => (
                      <button key={i} onClick={() => handleMcqAnswer(q.question_id, option)}
                        className={`w-full text-left px-4 py-3 rounded-xl text-sm transition border ${
                          mcqAnswers[q.question_id] === option
                            ? 'border-indigo-500 bg-indigo-500/10 text-white'
                            : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600'
                        }`}>
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {quiz?.subjective?.length > 0 && (
          <div className="mb-8">
            <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">Short Answer</h3>
            <div className="space-y-5">
              {quiz.subjective.map((q) => (
                <div key={q.question_id} className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                  <p className="text-sm text-white font-medium mb-4">
                    <span className="text-indigo-400 mr-2">Q{q.question_id}.</span>
                    {q.question}
                  </p>
                  <textarea rows={4}
                    value={subjectiveAnswers[q.question_id] || ''}
                    onChange={(e) => handleSubjectiveAnswer(q.question_id, e.target.value)}
                    placeholder="Write your answer here..."
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <button onClick={submitQuiz} disabled={!allAnswered()}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl text-sm transition">
          {allAnswered() ? 'Submit Quiz' : 'Answer all questions to submit'}
        </button>
      </div>
    </div>
  )
}