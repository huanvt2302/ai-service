"use client"

import { useEffect, useState, useRef } from "react"
import { ragApi } from "@/lib/api"
import { Plus, Database, FileText, Trash2, Upload, Search, ChevronRight, Loader2 } from "lucide-react"
import { formatBytes, relativeTime, cn } from "@/lib/utils"

export default function RagPage() {
  const [collections, setCollections] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [showNewCol, setShowNewCol] = useState(false)
  const [colForm, setColForm] = useState({ name: "", description: "" })
  const [searchQ, setSearchQ] = useState("")
  const [searchRes, setSearchRes] = useState<any[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  const loadCols = async () => {
    try {
      const cols = await ragApi.listCollections()
      setCollections(cols)
    } finally {
      setLoading(false)
    }
  }

  const loadCollection = async (id: string) => {
    const col = await ragApi.getCollection(id)
    setSelected(col)
  }

  useEffect(() => { loadCols() }, [])

  const createCollection = async () => {
    if (!colForm.name.trim()) return
    await ragApi.createCollection(colForm)
    setShowNewCol(false)
    setColForm({ name: "", description: "" })
    await loadCols()
  }

  const deleteCollection = async (id: string, name: string) => {
    if (!confirm(`Delete collection "${name}" and all its documents?`)) return
    await ragApi.deleteCollection(id)
    if (selected?.id === id) setSelected(null)
    await loadCols()
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selected) return
    setUploading(true)
    try {
      await ragApi.uploadDocument(selected.id, file)
      await loadCollection(selected.id)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  const deleteDoc = async (docId: string) => {
    await ragApi.deleteDocument(docId)
    if (selected) await loadCollection(selected.id)
    await loadCols()
  }

  const doSearch = async () => {
    if (!selected || !searchQ.trim()) return
    const res = await ragApi.search(selected.id, searchQ)
    setSearchRes(res.results || [])
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">RAG Management</h1>
          <p className="text-muted-foreground text-sm">Manage knowledge collections and documents</p>
        </div>
        <button
          onClick={() => setShowNewCol(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
        >
          <Plus className="w-4 h-4" /> New Collection
        </button>
      </div>

      {/* New collection */}
      {showNewCol && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-3 animate-fade-in">
          <h2 className="font-semibold text-sm">New Collection</h2>
          <div className="flex gap-3">
            <input value={colForm.name} onChange={e => setColForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Collection name" className="flex-1 px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary" />
            <input value={colForm.description} onChange={e => setColForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Description (optional)" className="flex-1 px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary" />
            <button onClick={createCollection} disabled={!colForm.name.trim()}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm disabled:opacity-50 hover:opacity-90">Create</button>
            <button onClick={() => setShowNewCol(false)} className="text-sm text-muted-foreground hover:text-foreground">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Collections list */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="text-sm font-semibold">Collections ({collections.length})</h2>
          </div>
          {loading ? (
            <div className="p-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
          ) : collections.length === 0 ? (
            <div className="p-8 text-center">
              <Database className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No collections yet</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {collections.map(col => (
                <button
                  key={col.id}
                  onClick={() => loadCollection(col.id)}
                  className={cn(
                    "w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/30 transition-colors",
                    selected?.id === col.id && "bg-primary/10"
                  )}
                >
                  <div>
                    <p className={cn("text-sm font-medium", selected?.id === col.id && "text-primary")}>{col.name}</p>
                    <p className="text-xs text-muted-foreground">{col.doc_count} docs</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteCollection(col.id, col.name) }}
                      className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Document panel */}
        <div className="lg:col-span-2 space-y-4">
          {selected ? (
            <>
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="font-semibold">{selected.name}</h2>
                    <p className="text-xs text-muted-foreground">{selected.description}</p>
                  </div>
                  <div className="flex gap-2">
                    <input ref={fileRef} type="file" onChange={handleUpload} className="hidden" />
                    <button
                      onClick={() => fileRef.current?.click()}
                      disabled={uploading}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-muted transition-colors disabled:opacity-50"
                    >
                      {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                      {uploading ? "Uploading..." : "Upload"}
                    </button>
                  </div>
                </div>

                {/* Documents */}
                {selected.documents?.length === 0 ? (
                  <div className="text-center py-8">
                    <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">No documents. Upload a file to start.</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="text-left border-b border-border">
                        {["Filename", "Size", "Chunks", "Status", "Uploaded", ""].map(h => (
                          <th key={h} className="pb-3 text-xs font-medium text-muted-foreground px-2">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.documents.map((doc: any) => (
                        <tr key={doc.id} className="border-b border-border/50 last:border-0 hover:bg-muted/20">
                          <td className="py-2 px-2 text-xs font-medium">{doc.filename}</td>
                          <td className="py-2 px-2 text-xs text-muted-foreground">{formatBytes(doc.file_size)}</td>
                          <td className="py-2 px-2 text-xs text-muted-foreground">{doc.chunk_count}</td>
                          <td className="py-2 px-2">
                            <span className={cn("text-xs px-1.5 py-0.5 rounded-full", `badge-${doc.status}`)}>
                              {doc.status}
                            </span>
                          </td>
                          <td className="py-2 px-2 text-xs text-muted-foreground">{relativeTime(doc.created_at)}</td>
                          <td className="py-2 px-2 text-right">
                            <button onClick={() => deleteDoc(doc.id)} className="p-1 text-muted-foreground hover:text-red-400">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Semantic search */}
              <div className="rounded-xl border border-border bg-card p-5">
                <h3 className="text-sm font-semibold mb-3">Semantic Search</h3>
                <div className="flex gap-2 mb-4">
                  <input
                    value={searchQ}
                    onChange={e => setSearchQ(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && doSearch()}
                    placeholder="Search this collection..."
                    className="flex-1 px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary"
                  />
                  <button onClick={doSearch} className="px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90">
                    <Search className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-2">
                  {searchRes.map((r, i) => (
                    <div key={i} className="p-3 rounded-lg bg-muted/50 border border-border/50">
                      <p className="text-xs text-muted-foreground mb-1">Chunk {r.chunk_index}</p>
                      <p className="text-sm">{r.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
              <Database className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <p className="font-medium">Select a collection</p>
              <p className="text-xs text-muted-foreground mt-1">Choose a collection from the left to view and manage documents</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
