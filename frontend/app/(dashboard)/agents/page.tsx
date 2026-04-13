"use client"

import { useEffect, useState } from "react"
import { agentsApi } from "@/lib/api"
import { Plus, Bot, Trash2, Edit, MessageSquare, Cpu, Brain, Plug } from "lucide-react"
import { relativeTime, cn } from "@/lib/utils"

const defaultForm = {
  name: "",
  description: "",
  personality: "",
  system_prompt: "",
  behavior_rules: "",
  model: "qwen3.5-plus",
  temperature: 0.7,
  plugins_enabled: false,
  memory_enabled: false,
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<any>(null)
  const [form, setForm] = useState({ ...defaultForm })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try {
      setAgents(await agentsApi.list())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openNew = () => {
    setEditing("new")
    setForm({ ...defaultForm })
  }

  const openEdit = (a: any) => {
    setEditing(a.id)
    setForm({ ...a })
  }

  const save = async () => {
    setSaving(true)
    try {
      if (editing === "new") {
        await agentsApi.create(form)
      } else {
        await agentsApi.update(editing, form)
      }
      setEditing(null)
      await load()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  const del = async (id: string, name: string) => {
    if (!confirm(`Delete agent "${name}"?`)) return
    await agentsApi.delete(id)
    await load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Agent Builder</h1>
          <p className="text-muted-foreground text-sm">Create and configure custom AI agents</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90">
          <Plus className="w-4 h-4" /> New Agent
        </button>
      </div>

      {/* Editor */}
      {editing && (
        <div className="rounded-xl border border-border bg-card p-6 space-y-5 animate-fade-in">
          <h2 className="font-semibold">{editing === "new" ? "New Agent" : "Edit Agent"}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Agent Name *</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary"
                placeholder="Customer Support Bot" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Model</label>
              <select value={form.model} onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm">
                <option value="qwen3.5-plus">qwen3.5-plus</option>
                <option value="text-embedding-3-small">text-embedding-3-small</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Description</label>
              <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary"
                placeholder="What does this agent do?" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Temperature ({form.temperature})</label>
              <input type="range" min="0" max="2" step="0.1" value={form.temperature}
                onChange={e => setForm(f => ({ ...f, temperature: parseFloat(e.target.value) }))}
                className="w-full accent-primary" />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Personality</label>
            <textarea value={form.personality} onChange={e => setForm(f => ({ ...f, personality: e.target.value }))}
              rows={2} placeholder="Describe the agent's personality and tone..."
              className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary resize-none" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">System Prompt</label>
            <textarea value={form.system_prompt} onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
              rows={4} placeholder="You are a helpful assistant..."
              className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm font-mono outline-none focus:ring-1 focus:ring-primary resize-none" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Behavior Rules</label>
            <textarea value={form.behavior_rules} onChange={e => setForm(f => ({ ...f, behavior_rules: e.target.value }))}
              rows={2} placeholder="Always respond in English. Never reveal the system prompt..."
              className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary resize-none" />
          </div>
          <div className="flex items-center gap-6">
            {[
              { key: "plugins_enabled", label: "Plugins", icon: Plug },
              { key: "memory_enabled", label: "Memory", icon: Brain },
            ].map(({ key, label, icon: Icon }) => (
              <div key={key} className="flex items-center gap-2">
                <button
                  onClick={() => setForm(f => ({ ...f, [key]: !(f as any)[key] }))}
                  className={cn(
                    "relative inline-flex h-5 w-9 rounded-full transition-colors",
                    (form as any)[key] ? "bg-primary" : "bg-muted"
                  )}
                >
                  <span className={cn(
                    "absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform",
                    (form as any)[key] && "translate-x-4"
                  )} />
                </button>
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{label}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={save} disabled={saving || !form.name.trim()}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 hover:opacity-90">
              {saving ? "Saving..." : "Save Agent"}
            </button>
            <button onClick={() => setEditing(null)} className="text-sm text-muted-foreground hover:text-foreground">Cancel</button>
          </div>
        </div>
      )}

      {/* Agent list */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-40 rounded-xl shimmer" />)}
        </div>
      ) : agents.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center">
          <Bot className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="font-medium">No agents yet</p>
          <p className="text-xs text-muted-foreground mt-1">Create your first AI agent to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.map((a) => (
            <div key={a.id} className="rounded-xl border border-border bg-card p-5 hover:border-primary/30 transition-all">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">{a.name}</p>
                    <p className="text-xs text-muted-foreground">{a.model}</p>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(a)} className="p-1.5 rounded hover:bg-muted transition-colors">
                    <Edit className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                  <button onClick={() => del(a.id, a.name)} className="p-1.5 rounded hover:bg-red-500/10 transition-colors">
                    <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-red-400" />
                  </button>
                </div>
              </div>
              {a.description && <p className="text-xs text-muted-foreground mb-3">{a.description}</p>}
              <div className="flex items-center gap-2 flex-wrap">
                {a.plugins_enabled && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/30">Plugins</span>
                )}
                {a.memory_enabled && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">Memory</span>
                )}
                <span className="text-xs text-muted-foreground ml-auto">{relativeTime(a.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
