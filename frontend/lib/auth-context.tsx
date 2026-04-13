"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi } from '@/lib/api'

interface User {
  id: string
  email: string
  full_name: string
  role: string
  team_id: string
  team_name: string
  avatar_url?: string
}

interface AuthContext {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string, teamName: string) => Promise<void>
  logout: () => void
}

const AuthCtx = createContext<AuthContext | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async (tk: string) => {
    try {
      const me = await authApi.me()
      setUser(me)
    } catch {
      localStorage.removeItem('ai_platform_token')
      setToken(null)
    }
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem('ai_platform_token')
    if (stored) {
      setToken(stored)
      fetchMe(stored).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [fetchMe])

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    localStorage.setItem('ai_platform_token', res.access_token)
    setToken(res.access_token)
    const me = await authApi.me()
    setUser(me)
  }

  const register = async (email: string, password: string, fullName: string, teamName: string) => {
    const res = await authApi.register(email, password, fullName, teamName)
    localStorage.setItem('ai_platform_token', res.access_token)
    setToken(res.access_token)
    const me = await authApi.me()
    setUser(me)
  }

  const logout = () => {
    localStorage.removeItem('ai_platform_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthCtx.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
