import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'pixora_token'
const REFRESH_KEY = 'pixora_refresh'
const USER_KEY = 'pixora_user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (stored && storedUser) {
      setToken(stored)
      try { setUser(JSON.parse(storedUser)) } catch {}
    }

    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    const urlRefresh = params.get('refresh')
    if (urlToken) {
      localStorage.setItem(TOKEN_KEY, urlToken)
      if (urlRefresh) localStorage.setItem(REFRESH_KEY, urlRefresh)
      setToken(urlToken)
      fetchMe(urlToken)
      window.history.replaceState({}, '', window.location.pathname)
    } else if (stored) {
      fetchMe(stored)
    } else {
      setLoading(false)
    }
  }, [])

  async function fetchMe(tok) {
    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${tok}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data.user)
        localStorage.setItem(USER_KEY, JSON.stringify(data.user))
        setToken(tok)
      } else {
        logout()
      }
    } catch {
      logout()
    } finally {
      setLoading(false)
    }
  }

  async function login(email, password) {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(REFRESH_KEY, data.refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
    return data
  }

  async function signup(email, password, name) {
    const res = await fetch('/api/v1/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Signup failed')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(REFRESH_KEY, data.refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
    return data
  }

  function loginWithGoogle() {
    window.location.href = '/api/v1/auth/google'
  }

  function logout() {
    const refresh = localStorage.getItem(REFRESH_KEY)
    if (refresh) {
      fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      }).catch(() => {})
    }
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, loginWithGoogle, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
