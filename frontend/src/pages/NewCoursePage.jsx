import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'

export default function NewCoursePage() {
  const navigate = useNavigate()

  const [step, setStep] = useState(1) // 1 = course details, 2 = syllabus option
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [courseForm, setCourseForm] = useState({
    name: '',
    start_date: '',
    end_date: ''
  })

  const [createdCourse, setCreatedCourse] = useState(null)
  const [syllabus, setSyllabus] = useState('')
  const [syllabusLoading, setSyllabusLoading] = useState(false)

  const handleCourseChange = (e) => {
    setCourseForm({ ...courseForm, [e.target.name]: e.target.value })
  }

  // Step 1 — create the course
  const handleCreateCourse = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await api.post('/courses', courseForm)
      setCreatedCourse(res.data)
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create course')
    } finally {
      setLoading(false)
    }
  }

  // Step 2a — submit syllabus then go to dashboard
  const handleSubmitSyllabus = async () => {
    if (!syllabus.trim()) {
      setError('Please enter your syllabus')
      return
    }

    setError('')
    setSyllabusLoading(true)

    try {
      await api.post('/syllabus', {
        course_id: createdCourse.course_id,
        course_name: createdCourse.name,
        handout: syllabus
      })
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save syllabus')
    } finally {
      setSyllabusLoading(false)
    }
  }

  // Step 2b — skip syllabus and go straight to dashboard
  const handleSkip = async () => {
    setError('')
    setSyllabusLoading(true)
    try {
      await api.post(`/courses/${createdCourse.course_id}/generate-plan`)
    } catch (err) {
      console.error('Plan generation failed:', err)
      // still navigate even if plan fails
    } finally {
      setSyllabusLoading(false)
      navigate('/dashboard')
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-lg">

        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white">QuizAI</h1>
          <p className="text-gray-400 mt-2">
            {step === 1 ? 'Set up your new course' : 'Add your syllabus'}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`h-2 w-16 rounded-full transition-all ${
            step >= 1 ? 'bg-indigo-500' : 'bg-gray-700'
          }`} />
          <div className={`h-2 w-16 rounded-full transition-all ${
            step >= 2 ? 'bg-indigo-500' : 'bg-gray-700'
          }`} />
        </div>

        {/* Card */}
        <div className="bg-gray-900 rounded-2xl p-8 shadow-xl border border-gray-800">

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3 mb-5">
              {error}
            </div>
          )}

          {/* ── Step 1: Course details ── */}
          {step === 1 && (
            <>
              <h2 className="text-xl font-semibold text-white mb-6">
                Course Details
              </h2>

              <form onSubmit={handleCreateCourse} className="space-y-5">
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    Course Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={courseForm.name}
                    onChange={handleCourseChange}
                    required
                    placeholder="e.g. Data Structures"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    Start Date
                  </label>
                  <input
                    type="date"
                    name="start_date"
                    value={courseForm.start_date}
                    onChange={handleCourseChange}
                    required
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    End Date
                  </label>
                  <input
                    type="date"
                    name="end_date"
                    value={courseForm.end_date}
                    onChange={handleCourseChange}
                    required
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium rounded-lg py-2.5 text-sm transition"
                >
                  {loading ? 'Creating...' : 'Continue'}
                </button>
              </form>
            </>
          )}

          {/* ── Step 2: Syllabus ── */}
          {step === 2 && (
            <>
              <h2 className="text-xl font-semibold text-white mb-2">
                Add Syllabus
              </h2>
              <p className="text-sm text-gray-400 mb-6">
                Paste your course syllabus so we can build a personalised study plan.
                You can skip this and add it later.
              </p>

              <textarea
                value={syllabus}
                onChange={(e) => setSyllabus(e.target.value)}
                rows={8}
                placeholder="Paste your syllabus here..."
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none mb-5"
              />

              <div className="flex gap-3">
              <button
                  onClick={handleSkip}
                  disabled={syllabusLoading}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-300 font-medium rounded-lg py-2.5 text-sm transition"
                >
                  {syllabusLoading ? 'Generating plan...' : 'Skip for now'}
                </button>
                <button
                  onClick={handleSubmitSyllabus}
                  disabled={syllabusLoading}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium rounded-lg py-2.5 text-sm transition"
                >
                  {syllabusLoading ? 'Saving...' : 'Save & Continue'}
                </button>
              </div>
            </>
          )}

        </div>

        {/* Back button */}
        {step === 1 && (
          <p className="text-center text-gray-500 text-sm mt-6">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-indigo-400 hover:text-indigo-300 transition"
            >
              ← Back to dashboard
            </button>
          </p>
        )}

      </div>
    </div>
  )
}