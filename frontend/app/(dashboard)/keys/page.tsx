"use client"

import { useEffect, useState } from "react"
import { keysApi } from "@/lib/api"
import { relativeTime, cn } from "@/lib/utils"
import { Key, Plus, Trash2, Copy, Eye, EyeOff, AlertCircle } from "lucide-react"

export default function KeysPage() {
  const [keys, setKeys] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newKey, setNewKey] = useState<any>(null)
  const [form, setForm] = useState({ name: "", expires_in_days: "" })
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = async () => {
    try {
      const ks = await keysApi.list()
      setKeys(ks)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const create = async () => {
    if (!form.name.trim()) return
    setCreating(true)
    try {
      const key = await keysApi.create(
        form.name,
        form.expires_in_days ? parseInt(form.expires_in_days) : undefined
      )
      setNewKey(key)
      setForm({ name: "", expires_in_days: "" })
      await load()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setCreating(false)
    }
  }

  const revoke = async (id: string, name: string) => {
    if (!confirm(`Revoke "${name}"? This cannot be undone.`)) return
    await keysApi.revoke(id)
    await load()
  }

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-muted-foreground text-sm">Manage authentication keys for API access</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setNewKey(null) }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" /> Create Key
        </button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="rounded-xl border border-border bg-card p-6 space-y-4">
          <h2 className="font-semibold">New API Key</h2>

          {newKey ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <p className="text-xs text-amber-400">Copy this key now. It won't be shown again.</p>
              </div>
              <div className="flex items-center gap-2 font-mono text-sm p-3 rounded-lg bg-muted border border-border">
                <span className="flex-1 truncate">{newKey.full_key}</span>
                <button onClick={() => copyKey(newKey.full_key)} className="shrink-0">
                  <Copy className={cn("w-4 h-4", copied ? "text-emerald-400" : "text-muted-foreground")} />
                </button>
              </div>
              <button onClick={() => setShowCreate(false)} className="text-sm text-primary hover:underline">Done</button>
            </div>
          ) : (
            <div className="flex items-end gap-3">
              <div className="flex-1 space-y-1">
                <label className="text-xs text-muted-foreground">Key Name</label>
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Production API"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="w-36 space-y-1">
                <label className="text-xs text-muted-foreground">Expires (days)</label>
                <input
                  type="number"
                  value={form.expires_in_days}
                  onChange={e => setForm(f => ({ ...f, expires_in_days: e.target.value }))}
                  placeholder="Never"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <button
                onClick={create}
                disabled={creating || !form.name.trim()}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 hover:opacity-90"
              >
                {creating ? "Creating..." : "Create"}
              </button>
              <button onClick={() => setShowCreate(false)} className="text-sm text-muted-foreground hover:text-foreground">Cancel</button>
            </div>
          )}
        </div>
      )}

      {/* Keys table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold">{keys.length} Keys</h2>
        </div>
        {loading ? (
          <div className="p-8 text-center">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : keys.length === 0 ? (
          <div className="p-12 text-center">
            <Key className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium">No API keys yet</p>
            <p className="text-xs text-muted-foreground">Create your first key to get started</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left">
                {["Name", "Prefix", "Status", "Last Used", "Expires", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key.id} className="border-b border-border/50 last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium">{key.name}</td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs bg-muted px-2 py-1 rounded">{key.prefix}...</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", `badge-${key.status}`)}>
                      {key.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {key.last_used_at ? relativeTime(key.last_used_at) : "Never"}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {key.status === "active" && (
                      <button
                        onClick={() => revoke(key.id, key.name)}
                        className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
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
