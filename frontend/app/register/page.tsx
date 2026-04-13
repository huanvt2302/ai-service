"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuth } from "@/lib/auth-context"
import { Zap, Loader2 } from "lucide-react"

export default function RegisterPage() {
  const [form, setForm] = useState({ email: "", password: "", full_name: "", team_name: "" })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password.length < 8) { setError("Password must be at least 8 characters"); return }
    setError("")
    setLoading(true)
    try {
      await register(form.email, form.password, form.full_name, form.team_name)
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.message || "Registration failed")
    } finally {
      setLoading(false)
    }
  }

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_hsl(262_80%_60%_/_0.15),_transparent_70%)] pointer-events-none" />
      <div className="w-full max-w-md px-4">
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
          <h1 className="text-xl font-bold mb-1">Create your account</h1>
          <p className="text-sm text-muted-foreground mb-6">Start building with AI today</p>
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { label: "Full Name", key: "full_name", type: "text", placeholder: "John Doe" },
              { label: "Team Name", key: "team_name", type: "text", placeholder: "My Company" },
              { label: "Email", key: "email", type: "email", placeholder: "you@example.com" },
              { label: "Password", key: "password", type: "password", placeholder: "Min 8 characters" },
            ].map(({ label, key, type, placeholder }) => (
              <div key={key} className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">{label}</label>
                <input
                  type={type}
                  value={(form as any)[key]}
                  onChange={update(key)}
                  required
                  placeholder={placeholder}
                  className="w-full px-4 py-2.5 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>
          <p className="text-center text-xs text-muted-foreground mt-5">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
