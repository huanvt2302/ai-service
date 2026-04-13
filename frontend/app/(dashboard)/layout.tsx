"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import Sidebar from "@/components/sidebar"
import { Bell, Search } from "lucide-react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login")
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans text-foreground">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden relative">
        {/* Header */}
        <header className="flex items-center justify-between gap-4 px-8 py-5 border-b border-border/40 bg-background/80 backdrop-blur-md z-10 sticky top-0">
          <div className="flex items-center gap-2 flex-1 max-w-sm rounded-[10px] border border-border/50 bg-muted/50 px-3 py-2 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all duration-300">
            <Search className="w-4 h-4 text-muted-foreground/70" />
            <input
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/70 font-medium"
              placeholder="Search anything..."
            />
          </div>
          <div className="flex items-center gap-4">
            <button className="relative p-2 rounded-xl hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-all duration-200">
              <Bell className="w-4 h-4 text-muted-foreground" />
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary border-[2px] border-background" />
            </button>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-8 animate-fade-in">
          <div className="max-w-[1600px] mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
