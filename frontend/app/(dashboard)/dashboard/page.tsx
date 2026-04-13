"use client"

import { useEffect, useState } from "react"
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, LineChart, Line
} from "recharts"
import {
  Zap, Key, TrendingUp, DollarSign, Activity,
  ArrowUpRight, Clock, CheckCircle, XCircle
} from "lucide-react"
import { usageApi, keysApi, billingApi } from "@/lib/api"
import { formatNumber, pct, relativeTime } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface StatCard {
  label: string
  value: string
  sub: string
  icon: React.ElementType
  color: string
  trend?: number
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null)
  const [keys, setKeys] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [quota, setQuota] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      usageApi.summary(30),
      keysApi.list(),
      usageApi.logs(1, 10),
      billingApi.getQuota(),
    ])
      .then(([sum, ks, lg, q]) => {
        setSummary(sum)
        setKeys(ks)
        setLogs(lg.items || [])
        setQuota(q)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const stats: StatCard[] = [
    {
      label: "Total Tokens",
      value: formatNumber(summary?.summary?.total_tokens || 0),
      sub: "This month",
      icon: Zap,
      color: "text-violet-400",
      trend: 12,
    },
    {
      label: "API Requests",
      value: formatNumber(summary?.summary?.total_requests || 0),
      sub: "30-day period",
      icon: Activity,
      color: "text-cyan-400",
      trend: 8,
    },
    {
      label: "Active Keys",
      value: String(keys.filter((k) => k.status === "active").length),
      sub: `${keys.length} total keys`,
      icon: Key,
      color: "text-emerald-400",
    },
    {
      label: "Success Rate",
      value: `${summary?.summary?.success_rate || 100}%`,
      sub: `${summary?.summary?.avg_latency_ms?.toFixed(0) || 0}ms avg latency`,
      icon: TrendingUp,
      color: "text-amber-400",
    },
  ]

  const chartData = (summary?.daily || []).map((d: any) => ({
    date: d.date.slice(5), // MM-DD
    requests: d.requests,
    tokens: d.tokens / 1000, // K
    latency: d.avg_latency,
  }))

  const quotaItems = quota?.quotas || []

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl shimmer" />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-64 rounded-xl shimmer" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-[15px] font-medium mt-1">Monitor your AI platform usage and activity in real-time</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map(({ label, value, sub, icon: Icon, color, trend }, i) => (
          <div 
            key={label} 
            className={cn(
              "group rounded-2xl border border-border/50 bg-card/40 backdrop-blur-md p-6 cursor-pointer",
              "hover:border-primary/50 hover:bg-card/80 hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 transition-all duration-300",
              `animate-fade-in delay-${(i % 4) * 100}`
            )}
          >
            <div className="flex items-center justify-between mb-4">
              <p className="text-[13px] font-medium text-muted-foreground uppercase tracking-wider group-hover:text-foreground transition-colors">{label}</p>
              <div className={cn("p-2.5 rounded-xl bg-muted/50 group-hover:scale-110 transition-transform duration-300", color)}>
                <Icon className="w-[18px] h-[18px]" />
              </div>
            </div>
            <p className="text-[32px] leading-none font-bold tracking-tight text-foreground">{value}</p>
            <div className="flex items-center gap-2 mt-3">
              {trend ? (
                <span className="text-[11px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5 bg-emerald-500/15 text-emerald-500">
                  <ArrowUpRight className="w-3 h-3" />+{trend}%
                </span>
              ) : null}
              <p className="text-xs text-muted-foreground font-medium">{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-2">
        {/* Requests chart */}
        <div className="lg:col-span-2 rounded-2xl border border-border/50 bg-card/40 backdrop-blur-md p-6 hover:border-primary/20 hover:bg-card/60 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 cursor-pointer">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-[15px] font-bold tracking-tight">Requests Over Time</h2>
              <p className="text-[12px] text-muted-foreground font-medium mt-1">Total platform calls from last 30 days</p>
            </div>
          </div>
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickMargin={10} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickMargin={10} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12, fontSize: 12, boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                  labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600, marginBottom: 4 }}
                  itemStyle={{ fontSize: 13, fontWeight: 500 }}
                  cursor={{ stroke: 'hsl(var(--primary))', strokeWidth: 1, strokeDasharray: '4 4' }}
                />
                <Area type="monotone" dataKey="requests" stroke="hsl(var(--primary))" fill="url(#colorRequests)" strokeWidth={3} activeDot={{ r: 6, fill: "hsl(var(--primary))", strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* By service */}
        <div className="rounded-2xl border border-border/50 bg-card/40 backdrop-blur-md p-6 hover:border-primary/20 hover:bg-card/60 hover:shadow-xl transition-all duration-300">
          <h2 className="text-[15px] font-bold tracking-tight mb-6">Usage By Service</h2>
          <div className="space-y-5">
            {(summary?.by_service || []).map((s: any) => (
              <div key={s.service} className="group">
                <div className="flex items-center justify-between text-[13px] mb-2 font-medium">
                  <span className="capitalize text-foreground group-hover:text-primary transition-colors">{s.service}</span>
                  <span className="text-muted-foreground">{formatNumber(s.requests)}</span>
                </div>
                <div className="h-2 rounded-full bg-muted/60 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary relative overflow-hidden group-hover:opacity-90 transition-opacity"
                    style={{ width: `${Math.min(100, (s.requests / Math.max(...(summary?.by_service || [{}]).map((x: any) => x.requests || 1))) * 100)}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 w-[20%] -skew-x-[20deg] animate-[slide-in_2s_ease-in-out_infinite]" />
                  </div>
                </div>
              </div>
            ))}
            {(!summary?.by_service || summary.by_service.length === 0) && (
              <p className="text-sm text-muted-foreground text-center py-10 font-medium">No data points yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Quota + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-2">
        {/* Quota progress */}
        <div className="rounded-2xl border border-border/50 bg-card/40 backdrop-blur-md p-6 hover:border-primary/20 hover:bg-card/60 transition-all duration-300">
          <h2 className="text-[15px] font-bold tracking-tight mb-6">Quota Usage</h2>
          <div className="space-y-6">
            {quotaItems.map((q: any) => (
              <div key={q.service} className="group">
                <div className="flex justify-between text-[13px] font-medium mb-2">
                  <span className="text-foreground group-hover:text-primary transition-colors">{q.name}</span>
                  <span className="text-muted-foreground">
                    <span className="text-foreground font-semibold">{formatNumber(q.used)}</span> / {formatNumber(q.limit)} {q.unit}
                  </span>
                </div>
                <div className="h-2.5 rounded-full bg-muted/60 overflow-hidden mb-1">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-1000 ease-out",
                      pct(q.used, q.limit) > 80 ? "bg-red-500" : pct(q.used, q.limit) > 50 ? "bg-amber-500" : "bg-primary"
                    )}
                    style={{ width: `${pct(q.used, q.limit)}%` }}
                  />
                </div>
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">{pct(q.used, q.limit)}% Consumed</p>
              </div>
            ))}
            {quotaItems.length === 0 && (
              <p className="text-[13px] text-muted-foreground font-medium text-center py-4">Calculating quotas...</p>
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div className="rounded-2xl border border-border/50 bg-card/40 backdrop-blur-md p-6 hover:border-primary/20 hover:bg-card/60 transition-all duration-300">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-[15px] font-bold tracking-tight">Recent Activity</h2>
            <button className="text-[13px] text-primary hover:text-primary/80 font-medium transition-colors">View All</button>
          </div>
          <div className="space-y-1 mt-2">
            {logs.length === 0 && (
              <p className="text-[13px] text-muted-foreground text-center py-8 font-medium">No activity in the last 24h</p>
            )}
            {logs.map((log: any) => (
              <div key={log.id} className="flex items-center gap-4 p-3 -mx-3 rounded-xl hover:bg-muted/50 cursor-pointer transition-colors group">
                {log.status_code < 400 ? (
                  <div className="p-2 rounded-lg bg-emerald-500/10 shrink-0 group-hover:scale-110 transition-transform">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  </div>
                ) : (
                  <div className="p-2 rounded-lg bg-red-500/10 shrink-0 group-hover:scale-110 transition-transform">
                    <XCircle className="w-4 h-4 text-red-500" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] font-semibold truncate group-hover:text-primary transition-colors">{log.endpoint}</p>
                  <p className="text-[12px] text-muted-foreground font-medium mt-0.5">{log.model} • <span className="text-foreground/80">{formatNumber(log.total_tokens)} tx</span></p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[13px] font-medium text-foreground">{log.latency_ms?.toFixed(0)} <span className="text-muted-foreground text-[11px]">ms</span></p>
                  <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mt-0.5">{relativeTime(log.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
