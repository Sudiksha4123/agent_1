import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  const login = (userData, token) => {
    localStorage.setItem('token', token)
  
    // decode JWT payload to get username
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const enrichedUser = {
        ...userData,
        username: payload.username || userData.email
      }
      localStorage.setItem('user', JSON.stringify(enrichedUser))
      setUser(enrichedUser)
    } catch {
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}