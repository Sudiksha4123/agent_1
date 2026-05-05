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
  const [quizStatus, setQuizStatus] = useState(null)
  const [topicPerformance, setTopicPerformance] = useState([])
  const [loading, setLoading] = useState(true)
  const [planLoading, setPlanLoading] = useState(false)
  const [generatingSprint, setGeneratingSprint] = useState(false)

  // course map modal
  const [showCourseMap, setShowCourseMap] = useState(false)
  const [courseMap, setCourseMap] = useState(null)

  // profile modal
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => { fetchCourses() }, [])
  useEffect(() => {
    if (activeCourse) fetchCourseData(activeCourse.course_id)
  }, [activeCourse])

  const fetchCourses = async () => {
    try {
      const res = await api.get('/courses')
      setCourses(res.data)
      if (res.data.length > 0) setActiveCourse(res.data[0])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchCourseData = async (courseId) => {
    setPlanLoading(true)
    try {
      const [profileRes, planRes, statusRes] = await Promise.allSettled([
        api.get(`/profile/${courseId}`),
        api.get(`/plan/${courseId}`),
        api.get(`/quiz/status/${courseId}`)
      ])
      setProfile(profileRes.status === 'fulfilled' ? profileRes.value.data : null)
      setPlan(planRes.status === 'fulfilled' ? planRes.value.data : null)
      setQuizStatus(statusRes.status === 'fulfilled' ? statusRes.value.data : null)
      setTopicPerformance(
        profileRes.status === 'fulfilled'
          ? profileRes.value.data.topic_performance ?? []
          : []
      )
    } catch (err) {
      console.error(err)
    } finally {
      setPlanLoading(false)
    }
  }

  const fetchCourseMap = async (courseId) => {
    try {
      const res = await api.get(`/plan/${courseId}/initial`)
      setCourseMap(res.data)
      setShowCourseMap(true)
    } catch (err) {
      console.error(err)
    }
  }

  const handleStartLearning = async () => {
    setGeneratingSprint(true)
    try {
      await api.post(`/courses/${activeCourse.course_id}/start-learning`)
      await fetchCourseData(activeCourse.course_id)
    } catch (err) {
      console.error(err)
    } finally {
      setGeneratingSprint(false)
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
        <h1 className="text-xl font-bold text-indigo-400">PlannerAI</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{user?.username}</span>
          <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-white transition">
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
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

            {/* Sidebar */}
            <div className="w-56 shrink-0">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Your Courses</p>
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
            <div className="flex-1 space-y-5">
              {planLoading ? (
                <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-center">
                  <p className="text-gray-400 text-sm">Loading course data...</p>
                </div>
              ) : (
                <>
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
                        {/* Course map link */}
                        <button
                          onClick={() => fetchCourseMap(activeCourse.course_id)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition mt-2"
                        >
                          View Course Map →
                        </button>
                      </div>

                      {plan && !plan.is_initial && (
                        quizStatus?.sprint_ready ? (
                          <button
                            onClick={() => navigate(`/quiz?course_id=${activeCourse?.course_id}`)}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
                          >
                            Take Quiz
                          </button>
                        ) : (
                          <div className="relative group">
                            <button disabled className="bg-gray-700 text-gray-500 cursor-not-allowed text-sm font-medium px-4 py-2 rounded-lg">
                              Take Quiz
                            </button>
                            <div className="absolute right-0 top-10 w-52 bg-gray-800 text-gray-300 text-xs rounded-lg p-3 hidden group-hover:block z-10 border border-gray-700">
                              Sprint plan is being prepared
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
                      <p className="text-sm text-gray-400 mb-1">Quizzes Taken</p>
                      <p className="text-3xl font-bold text-white">{profile?.total_quiz ?? 0}</p>
                    </div>
                    <div
                      className="bg-gray-900 rounded-2xl p-5 border border-gray-800 cursor-pointer hover:border-indigo-500/50 transition"
                      onClick={() => topicPerformance.length > 0 && setShowProfile(true)}
                    >
                      <p className="text-sm text-gray-400 mb-1">Average Score</p>
                      <p className="text-3xl font-bold text-white">
                      {profile?.overall_avg
  ? `${Math.round(profile.overall_avg)} / ${Math.round(profile.overall_max || 0)}`
  : '—'}
                      </p>
                      {topicPerformance.length > 0 && (
                        <p className="text-xs text-indigo-400 mt-2">View performance →</p>
                      )}
                    </div>
                  </div>

                  {/* Plan section */}
                  {!plan ? (
                    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-center">
                      <p className="text-gray-400 text-sm">No plan found for this course</p>
                    </div>
                  ) : plan.is_initial ? (
                    <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800 text-center">
                      <div className="text-4xl mb-4">🎯</div>
                      <h4 className="text-white font-semibold text-lg mb-2">Ready to start learning?</h4>
                      <p className="text-gray-400 text-sm mb-6">
                        We'll build your first personalised study sprint from your course plan.
                      </p>
                      <button
                        onClick={handleStartLearning}
                        disabled={generatingSprint}
                        className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium px-6 py-2.5 rounded-lg text-sm transition"
                      >
                        {generatingSprint ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                            Generating sprint...
                          </span>
                        ) : 'Start Learning'}
                      </button>
                    </div>
                  ) : (
                    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h4 className="font-semibold text-white">Current Sprint</h4>
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

                      <div className="mb-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Topics</p>
                        <div className="flex flex-wrap gap-2">
                          {plan.topics?.map((topic, i) => (
                            <span key={i} className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-full">
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>

                      {plan.study_plan?.length > 0 && (
                        <div>
                          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Study Plan</p>
                          <div className="space-y-3">
                            {plan.study_plan.map((item, i) => (
                              <div key={i} className="bg-gray-800 rounded-xl p-4">
                                <p className="text-sm font-medium text-white mb-1">{item.topic}</p>
                                <p className="text-xs text-gray-400 mb-2">{item.study_tips}</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {item.focus_areas?.map((area, j) => (
                                    <span key={j} className="text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full">
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
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Course Map Modal ── */}
      {showCourseMap && courseMap && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-800 sticky top-0 bg-gray-900">
              <div>
                <h3 className="font-semibold text-white text-lg">Course Map</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Full learning plan for {activeCourse?.name}
                </p>
              </div>
              <button
                onClick={() => setShowCourseMap(false)}
                className="text-gray-400 hover:text-white transition text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-6">
              {/* Dates + difficulty */}
              <div className="flex items-center gap-3 mb-5">
                {courseMap.start_date && courseMap.end_date && (
                  <span className="text-xs text-gray-400 bg-gray-800 px-3 py-1 rounded-full">
                    {new Date(courseMap.start_date).toLocaleDateString()} → {new Date(courseMap.end_date).toLocaleDateString()}
                  </span>
                )}
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                  courseMap.recommended_difficulty === 'Easy'
                    ? 'bg-green-500/10 text-green-400'
                    : courseMap.recommended_difficulty === 'Medium'
                    ? 'bg-yellow-500/10 text-yellow-400'
                    : 'bg-red-500/10 text-red-400'
                }`}>
                  {courseMap.recommended_difficulty}
                </span>
              </div>

              {/* All topics */}
              <div className="mb-5">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">All Topics</p>
                <div className="flex flex-wrap gap-2">
                  {courseMap.topics?.map((topic, i) => (
                    <span key={i} className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-full">
                      {i + 1}. {topic}
                    </span>
                  ))}
                </div>
              </div>

              {/* Full study plan */}
              {courseMap.study_plan?.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Study Plan</p>
                  <div className="space-y-3">
                    {courseMap.study_plan.map((item, i) => (
                      <div key={i} className="bg-gray-800 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs text-indigo-400 font-medium bg-indigo-500/10 px-2 py-0.5 rounded-full">
                            {i + 1}
                          </span>
                          <p className="text-sm font-medium text-white">{item.topic}</p>
                        </div>
                        <p className="text-xs text-gray-400 mb-2">{item.study_tips}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {item.focus_areas?.map((area, j) => (
                            <span key={j} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
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
          </div>
        </div>
      )}

      {/* ── Performance Profile Modal ── */}
      {showProfile && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-800 sticky top-0 bg-gray-900">
              <div>
                <h3 className="font-semibold text-white text-lg">Performance Profile</h3>
                <p className="text-xs text-gray-500 mt-1">{activeCourse?.name}</p>
              </div>
              <button
                onClick={() => setShowProfile(false)}
                className="text-gray-400 hover:text-white transition text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-6">

              {/* Overall stats */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-800 rounded-xl p-4 text-center">
                  <p className="text-xs text-gray-400 mb-1">Quizzes Taken</p>
                  <p className="text-3xl font-bold text-white">{profile?.total_quiz ?? 0}</p>
                </div>
                <div className="bg-gray-800 rounded-xl p-4 text-center">
                  <p className="text-xs text-gray-400 mb-1">Overall Average</p>
                  <p className="text-3xl font-bold text-white">
                  {profile?.overall_avg
  ? `${Math.round(profile.overall_avg)} / ${Math.round(profile.overall_max || 0)}`
  : '—'}
                  </p>
                </div>
              </div>

              {/* Topic breakdown */}
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-4">Topic Breakdown</p>
              <div className="space-y-5">
                {topicPerformance.map((t, i) => (
                  <div key={i} className="bg-gray-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-medium text-white">{t.topic}</p>
                      <span className="text-xs text-gray-500">
                        {t.quizzes_attempted} {t.quizzes_attempted === 1 ? 'attempt' : 'attempts'}
                      </span>
                    </div>

                    {/* Score */}
                    <div className="mb-2">
                      <div className="flex justify-between mb-1">
                        <p className="text-xs text-gray-500">Score</p>
                        <p className="text-xs text-gray-400">{t.average_score}%</p>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            t.average_score >= 75 ? 'bg-green-500'
                            : t.average_score >= 50 ? 'bg-yellow-500'
                            : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(t.average_score, 100)}%` }}
                        />
                      </div>
                    </div>

                    {/* Understanding */}
                    <div>
                      <div className="flex justify-between mb-1">
                        <p className="text-xs text-gray-500">Understanding</p>
                        <p className={`text-xs font-medium ${
                          t.understanding_score >= 75 ? 'text-green-400'
                          : t.understanding_score >= 50 ? 'text-yellow-400'
                          : 'text-red-400'
                        }`}>
                          {t.understanding_score}/100
                        </p>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            t.understanding_score >= 75 ? 'bg-green-500'
                            : t.understanding_score >= 50 ? 'bg-yellow-500'
                            : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(t.understanding_score, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}