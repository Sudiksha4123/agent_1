import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [courses, setCourses] = useState([])
  const [activeCourse, setActiveCourse] = useState(null)
  const [profile, setProfile] = useState(null)
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [planLoading, setPlanLoading] = useState(false)

  // fetch all courses on mount
  useEffect(() => {
    fetchCourses()
  }, [])

  // fetch profile + plan when active course changes
  useEffect(() => {
    if (activeCourse) {
      fetchCourseData(activeCourse.course_id)
    }
  }, [activeCourse])

  const fetchCourses = async () => {
    try {
      const res = await api.get('/courses')
      setCourses(res.data)
      if (res.data.length > 0) {
        setActiveCourse(res.data[0])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchCourseData = async (courseId) => {
    setPlanLoading(true)
    try {
      const [profileRes, planRes] = await Promise.allSettled([
        api.get(`/profile/${courseId}`),
        api.get(`/plan/${courseId}`)
      ])

      setProfile(profileRes.status === 'fulfilled' ? profileRes.value.data : null)
      setPlan(planRes.status === 'fulfilled' ? planRes.value.data : null)
    } catch (err) {
      console.error(err)
    } finally {
      setPlanLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* Navbar */}
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-indigo-400">QuizAI</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">
            {user?.username || user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-white transition"
          >
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header row */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-semibold">Dashboard</h2>
          <button
            onClick={() => navigate('/new-course')}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            + New Course
          </button>
        </div>

        {courses.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="text-5xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-white mb-2">No courses yet</h3>
            <p className="text-gray-400 mb-6">Start by adding your first course</p>
            <button
              onClick={() => navigate('/new-course')}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-6 py-2.5 rounded-lg transition"
            >
              + New Course
            </button>
          </div>
        ) : (
          <div className="flex gap-6">

            {/* Sidebar — course list */}
            <div className="w-56 shrink-0">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                Your Courses
              </p>
              <div className="space-y-1">
                {courses.map((course) => (
                  <button
                    key={course.course_id}
                    onClick={() => setActiveCourse(course)}
                    className={`w-full text-left px-4 py-2.5 rounded-lg text-sm transition ${
                      activeCourse?.course_id === course.course_id
                        ? 'bg-indigo-600 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                    }`}
                  >
                    {course.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Main content */}
            <div className="flex-1">
              {planLoading ? (
                <div className="flex items-center justify-center py-24">
                  <p className="text-gray-400">Loading course data...</p>
                </div>
              ) : (
                <div className="space-y-5">

                  {/* Course header */}
                  <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-xl font-semibold">{activeCourse?.name}</h3>
                        {activeCourse?.end_date && (
                          <p className="text-sm text-gray-400 mt-1">
                            Ends {new Date(activeCourse.end_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => navigate(`/quiz?course_id=${activeCourse?.course_id}`)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
                      >
                        Take Quiz
                      </button>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
                      <p className="text-sm text-gray-400 mb-1">Quizzes Taken</p>
                      <p className="text-3xl font-bold text-white">
                        {profile?.total_quiz ?? 0}
                      </p>
                    </div>
                    <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
                      <p className="text-sm text-gray-400 mb-1">Average Score</p>
                      <p className="text-3xl font-bold text-white">
                        {profile?.overall_avg
                          ? `${Math.round(profile.overall_avg)}%`
                          : '—'}
                      </p>
                    </div>
                  </div>

                  {/* Current Plan */}
                  {plan ? (
                    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                      <div className="flex items-center justify-between mb-4">
  <div>
    <h4 className="font-semibold text-white">Current Plan</h4>
    {plan.start_date && plan.end_date && (
      <p className="text-xs text-gray-500 mt-1">
        {new Date(plan.start_date).toLocaleDateString()} → {new Date(plan.end_date).toLocaleDateString()}
      </p>
    )}
  </div>
  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
    plan.recommended_difficulty === 'Easy'
      ? 'bg-green-500/10 text-green-400'
      : plan.recommended_difficulty === 'Medium'
      ? 'bg-yellow-500/10 text-yellow-400'
      : 'bg-red-500/10 text-red-400'
  }`}>
    {plan.recommended_difficulty}
  </span>
</div>

                      {/* Topics */}
                      <div className="mb-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                          Topics
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {plan.topics?.map((topic, i) => (
                            <span
                              key={i}
                              className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-full"
                            >
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Study plan */}
                      {plan.study_plan?.length > 0 && (
                        <div>
                          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                            Study Plan
                          </p>
                          <div className="space-y-3">
                            {plan.study_plan.map((item, i) => (
                              <div
                                key={i}
                                className="bg-gray-800 rounded-xl p-4"
                              >
                                <p className="text-sm font-medium text-white mb-1">
                                  {item.topic}
                                </p>
                                <p className="text-xs text-gray-400 mb-2">
                                  {item.study_tips}
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                  {item.focus_areas?.map((area, j) => (
                                    <span
                                      key={j}
                                      className="text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full"
                                    >
                                      {area}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-center">
                      <p className="text-gray-400 text-sm">No plan generated yet for this course</p>
                    </div>
                  )}

                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  )
}