"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, Key, Webhook, BarChart3, CreditCard,
  Users, Database, Brain, Mic, BookOpen, Zap,
  ChevronRight, LogOut, Moon, Sun, Settings
} from "lucide-react"
import { useTheme } from "next-themes"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "API Keys", href: "/keys", icon: Key },
  { label: "Webhooks", href: "/webhooks", icon: Webhook },
  { label: "Usage", href: "/usage", icon: BarChart3 },
  { label: "Billing", href: "/billing", icon: CreditCard },
  { label: "Teams", href: "/teams", icon: Users },
  { label: "RAG", href: "/rag", icon: Database },
  { label: "Data", href: "/data", icon: Brain },
  { label: "AI & Memory", href: "/agents", icon: Zap },
  { label: "STT & TTS", href: "/stt-tts", icon: Mic },
  { label: "API Docs", href: "/docs", icon: BookOpen },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, logout } = useAuth()

  return (
    <aside className="flex flex-col w-[260px] h-screen border-r border-border/40 bg-card/50 shrink-0 backdrop-blur-sm relative z-20">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-6 border-b border-border/40">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-primary/20">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="text-[15px] font-bold text-foreground tracking-tight">NeuralAPI</p>
          <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Platform</p>
        </div>
      </div>

      {/* Team badge */}
      {user && (
        <div className="mx-4 mt-6 px-4 py-2.5 rounded-xl bg-muted/40 border border-border/50 flex items-center justify-between group cursor-pointer hover:bg-muted/60 transition-colors">
          <div className="min-w-0">
            <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-0.5">Team</p>
            <p className="text-sm font-semibold text-foreground truncate">{user.team_name || "My Workspace"}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-[13px] font-medium transition-all duration-200 group relative overflow-hidden",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0 transition-colors", active ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
              <span className="flex-1">{label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Bottom actions */}
      <div className="p-4 space-y-2 relative before:absolute before:top-0 before:left-4 before:right-4 before:h-px before:bg-border/40">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-[13px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-200"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
        {user && (
          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-[13px] font-medium text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        )}

        {/* User info */}
        {user && (
          <div className="flex items-center gap-3 px-2 py-2 mt-2 cursor-pointer hover:bg-muted/50 rounded-xl transition-colors">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary/20 to-indigo-500/20 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary">
              {user.full_name?.[0] || user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-foreground truncate leading-tight">{user.full_name || user.email}</p>
              <p className="text-[11px] text-muted-foreground capitalize font-medium">{user.role}</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
