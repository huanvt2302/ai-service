"use client"

import { useEffect, useState } from "react"
import { webhooksApi } from "@/lib/api"
import { Plus, Webhook, Trash2, Activity } from "lucide-react"
import { relativeTime } from "@/lib/utils"

const EVENTS = [
  "usage.exceeded", "key.revoked", "key.created",
  "document.processed", "agent.created", "billing.updated"
]

export default function WebhooksPage() {
  const [hooks, setHooks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: "", url: "", events: [] as string[] })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try { setHooks(await webhooksApi.list()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const toggleEvent = (e: string) => {
    setForm(f => ({
      ...f,
      events: f.events.includes(e) ? f.events.filter(x => x !== e) : [...f.events, e]
    }))
  }

  const create = async () => {
    setSaving(true)
    try {
      await webhooksApi.create(form)
      setShowCreate(false)
      setForm({ name: "", url: "", events: [] })
      await load()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  const del = async (id: string) => {
    if (!confirm("Delete this webhook?")) return
    await webhooksApi.delete(id)
    await load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Webhooks</h1>
          <p className="text-muted-foreground text-sm">Receive real-time notifications for platform events</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
        >
          <Plus className="w-4 h-4" /> Add Webhook
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-border bg-card p-6 space-y-4 animate-fade-in">
          <h2 className="font-semibold">New Webhook</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Webhook" className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Endpoint URL</label>
              <input value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
                placeholder="https://example.com/webhook" className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary" />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Events to listen</label>
            <div className="flex flex-wrap gap-2">
              {EVENTS.map(e => (
                <button
                  key={e}
                  onClick={() => toggleEvent(e)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                    form.events.includes(e)
                      ? "bg-primary/15 border-primary/40 text-primary"
                      : "border-border text-muted-foreground hover:border-primary/30"
                  }`}
                >
                  {e}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={create} disabled={saving || !form.name || !form.url}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm disabled:opacity-50 hover:opacity-90">
              {saving ? "Creating..." : "Create Webhook"}
            </button>
            <button onClick={() => setShowCreate(false)} className="text-sm text-muted-foreground">Cancel</button>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center"><div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" /></div>
        ) : hooks.length === 0 ? (
          <div className="p-12 text-center">
            <Webhook className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="font-medium text-sm">No webhooks configured</p>
            <p className="text-xs text-muted-foreground mt-1">Add a webhook to receive event notifications</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left">
                {["Name", "URL", "Events", "Last Triggered", "Status", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {hooks.map(hook => (
                <tr key={hook.id} className="border-b border-border/50 last:border-0 hover:bg-muted/20">
                  <td className="px-4 py-3 text-sm font-medium">{hook.name}</td>
                  <td className="px-4 py-3 text-xs font-mono text-muted-foreground truncate max-w-48">{hook.url}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(hook.events || []).map((e: string) => (
                        <span key={e} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{e}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {hook.last_triggered_at ? relativeTime(hook.last_triggered_at) : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${hook.is_active ? "badge-active" : "badge-revoked"}`}>
                      {hook.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => del(hook.id)} className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
