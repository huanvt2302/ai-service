"use client"

import { useEffect, useState } from "react"
import { teamsApi } from "@/lib/api"
import { Users, Crown, Shield, User, Mail } from "lucide-react"
import { relativeTime } from "@/lib/utils"
import { cn } from "@/lib/utils"

const ROLE_ICONS: Record<string, React.ElementType> = {
  owner: Crown,
  admin: Shield,
  member: User,
}

const ROLE_COLORS: Record<string, string> = {
  owner: "text-amber-400",
  admin: "text-violet-400",
  member: "text-muted-foreground",
}

export default function TeamsPage() {
  const [team, setTeam] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    teamsApi.getCurrent()
      .then(setTeam)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-24 rounded-xl shimmer" />
        <div className="h-64 rounded-xl shimmer" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Team Workspace</h1>
        <p className="text-muted-foreground text-sm">Manage your team and collaboration settings</p>
      </div>

      {/* Team info */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-brand-gradient flex items-center justify-center text-white text-2xl font-bold">
            {team?.name?.[0] || "T"}
          </div>
          <div>
            <h2 className="text-xl font-bold">{team?.name}</h2>
            <p className="text-xs text-muted-foreground font-mono">/{team?.slug}</p>
          </div>
          <div className="ml-auto flex gap-3">
            <div className="text-right">
              <p className="text-2xl font-bold">{team?.member_count}</p>
              <p className="text-xs text-muted-foreground">Members</p>
            </div>
            <div className="text-right">
              <span className="px-3 py-1 rounded-full bg-primary/15 text-primary text-sm font-semibold capitalize">
                {team?.subscription?.plan || "free"}
              </span>
              <p className="text-xs text-muted-foreground mt-1">Current plan</p>
            </div>
          </div>
        </div>
      </div>

      {/* Members */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-semibold">Members ({team?.members?.length || 0})</h2>
        </div>
        <div className="divide-y divide-border">
          {(team?.members || []).map((member: any) => {
            const RoleIcon = ROLE_ICONS[member.role] || User
            return (
              <div key={member.id} className="flex items-center gap-4 px-5 py-4 hover:bg-muted/30 transition-colors">
                <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center text-sm font-bold text-primary">
                  {member.full_name?.[0] || member.email[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{member.full_name || "—"}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    <Mail className="w-3 h-3 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">{member.email}</p>
                  </div>
                </div>
                <div className={cn("flex items-center gap-1.5", ROLE_COLORS[member.role])}>
                  <RoleIcon className="w-4 h-4" />
                  <span className="text-xs font-medium capitalize">{member.role}</span>
                </div>
                <p className="text-xs text-muted-foreground">{relativeTime(member.created_at)}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Token usage */}
      {team?.subscription && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-3">Team Token Usage</h2>
          <div className="flex items-center justify-between text-xs mb-2">
            <span>Tokens used this period</span>
            <span className="text-muted-foreground">
              {(team.subscription.tokens_used || 0).toLocaleString()} / {(team.subscription.token_quota || 0).toLocaleString()}
            </span>
          </div>
          <div className="h-3 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-brand-gradient transition-all"
              style={{ width: `${Math.min(100, ((team.subscription.tokens_used || 0) / (team.subscription.token_quota || 1)) * 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
