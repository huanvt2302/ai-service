"use client"

import { useEffect, useState } from "react"
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts"
import { usageApi } from "@/lib/api"
import { formatNumber } from "@/lib/utils"
import { relativeTime } from "@/lib/utils"

const COLORS = ["hsl(262,80%,60%)", "hsl(200,100%,55%)", "hsl(160,100%,45%)", "hsl(40,100%,60%)", "hsl(0,80%,60%)"]

export default function UsagePage() {
  const [summary, setSummary] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [days, setDays] = useState(30)
  const [service, setService] = useState("")
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      usageApi.summary(days),
      usageApi.logs(page, 20, service || undefined),
    ]).then(([sum, lg]) => {
      setSummary(sum)
      setLogs(lg.items)
      setTotal(lg.total)
    }).finally(() => setLoading(false))
  }, [days, service, page])

  const chartData = (summary?.daily || []).map((d: any) => ({
    date: d.date.slice(5),
    requests: d.requests,
    tokens: Math.round(d.tokens / 1000),
    latency: Math.round(d.avg_latency || 0),
  }))

  const pieData = (summary?.by_service || []).map((s: any) => ({
    name: s.service,
    value: s.requests,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Usage Analytics</h1>
          <p className="text-muted-foreground text-sm">Monitor API consumption and performance</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={e => setDays(+e.target.value)}
            className="px-3 py-2 rounded-lg border border-border bg-card text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <select
            value={service}
            onChange={e => setService(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border bg-card text-sm"
          >
            <option value="">All services</option>
            <option value="chat">Chat</option>
            <option value="embeddings">Embeddings</option>
            <option value="stt">STT</option>
            <option value="tts">TTS</option>
          </select>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Tokens", value: formatNumber(summary?.summary?.total_tokens || 0) },
          { label: "Requests", value: formatNumber(summary?.summary?.total_requests || 0) },
          { label: "Avg Latency", value: `${summary?.summary?.avg_latency_ms?.toFixed(0) || 0}ms` },
          { label: "Success Rate", value: `${summary?.summary?.success_rate || 100}%` },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">{s.label}</p>
            <p className="text-2xl font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Requests over time */}
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Requests Over Time</h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="gr1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS[0]} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="requests" stroke={COLORS[0]} fill="url(#gr1)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Token usage */}
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Token Usage (K)</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="tokens" fill={COLORS[1]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Latency */}
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Latency (ms)</h2>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="latency" stroke={COLORS[2]} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* By service pie */}
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-4">Breakdown by Service</h2>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie data={pieData} cx={65} cy={65} innerRadius={40} outerRadius={65} dataKey="value">
                  {pieData.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {pieData.map((p: any, i: number) => (
                <div key={p.name} className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="capitalize">{p.name}</span>
                  <span className="text-muted-foreground">{formatNumber(p.value)}</span>
                </div>
              ))}
              {pieData.length === 0 && <p className="text-xs text-muted-foreground">No data</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Logs table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-semibold">Request Logs ({total})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                {["Service", "Model", "Endpoint", "Tokens", "Latency", "Status", "Time"].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-border/50 last:border-0 hover:bg-muted/20">
                  <td className="px-4 py-2.5 capitalize text-xs">{log.service}</td>
                  <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">{log.model}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{log.endpoint}</td>
                  <td className="px-4 py-2.5 text-xs">{log.total_tokens?.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-xs">{log.latency_ms?.toFixed(0)}ms</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${(log.status_code < 400) ? "badge-active" : "badge-error"}`}>
                      {log.status_code}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{relativeTime(log.created_at)}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={7} className="text-center py-8 text-xs text-muted-foreground">No logs found</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {total > 20 && (
          <div className="p-3 border-t border-border flex justify-center gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 text-xs rounded border border-border disabled:opacity-50">Prev</button>
            <span className="px-3 py-1 text-xs text-muted-foreground">Page {page}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 20 >= total} className="px-3 py-1 text-xs rounded border border-border disabled:opacity-50">Next</button>
          </div>
        )}
      </div>
    </div>
  )
}
