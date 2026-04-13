"use client"

import { Brain, Database, Search, FileText } from "lucide-react"

export default function DataPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Data</h1>
        <p className="text-muted-foreground text-sm">Explore and manage your AI training data and embeddings</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { icon: Database, title: "Vector Store", desc: "Browse pgvector embeddings stored across all collections", count: "—" },
          { icon: FileText, title: "Documents", desc: "View all uploaded and processed documents", count: "—" },
          { icon: Search, title: "Semantic Search", desc: "Search across all collections", count: "Global" },
          { icon: Brain, title: "Embeddings Explorer", desc: "Visualize embedding clusters (coming soon)", count: "v2" },
        ].map(({ icon: Icon, title, desc, count }) => (
          <div key={title} className="rounded-xl border border-border bg-card p-6 hover:border-primary/30 transition-all cursor-pointer">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2.5 rounded-lg bg-primary/15">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <span className="text-xs text-muted-foreground">{count}</span>
            </div>
            <h3 className="font-semibold mb-1">{title}</h3>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
