"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuth } from "@/lib/auth-context"
import { Zap, Eye, EyeOff, Loader2 } from "lucide-react"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await login(email, password)
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.message || "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_hsl(262_80%_60%_/_0.15),_transparent_70%)] pointer-events-none" />

      <div className="w-full max-w-md px-4">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-xl font-bold gradient-text">NeuralAPI</p>
            <p className="text-xs text-muted-foreground">AI Platform Console</p>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-8 shadow-2xl">
          <h1 className="text-xl font-bold mb-1">Welcome back</h1>
          <p className="text-sm text-muted-foreground mb-6">Sign in to your account</p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full px-4 py-2.5 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Password</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="text-center text-xs text-muted-foreground mt-5">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary hover:underline">Sign up</Link>
          </p>
        </div>

        {/* Demo hint */}
        <div className="mt-4 p-3 rounded-xl border border-border/50 bg-card/50 text-center">
          <p className="text-xs text-muted-foreground">
            No account? <Link href="/register" className="text-primary hover:underline">Create one free</Link> to get started.
          </p>
        </div>
      </div>
    </div>
  )
}
