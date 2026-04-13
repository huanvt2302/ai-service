"use client"

import { useState } from "react"
import { Copy, Check, ChevronDown, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

const endpoints = [
  {
    group: "Authentication",
    routes: [
      {
        method: "POST", path: "/auth/register",
        desc: "Register a new user and team",
        body: `{ "email": "user@example.com", "password": "secret123", "full_name": "John Doe", "team_name": "My Team" }`,
        response: `{ "access_token": "eyJ...", "token_type": "bearer" }`,
      },
      {
        method: "POST", path: "/auth/login",
        desc: "Authenticate and receive JWT",
        body: `{ "email": "user@example.com", "password": "secret123" }`,
        response: `{ "access_token": "eyJ...", "token_type": "bearer" }`,
      },
      { method: "GET", path: "/auth/me", desc: "Get current user profile", auth: true },
    ],
  },
  {
    group: "Models",
    routes: [
      { method: "GET", path: "/v1/models", desc: "List available models", auth: "api-key" },
    ],
  },
  {
    group: "Chat Completions",
    routes: [
      {
        method: "POST", path: "/v1/chat/completions",
        desc: "OpenAI-compatible chat completions with optional streaming",
        auth: "api-key",
        body: `{
  "model": "qwen3.5-plus",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello!" }
  ],
  "stream": false,
  "temperature": 0.7
}`,
        response: `{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [{ "message": { "role": "assistant", "content": "Hello! How can I help?" }, "finish_reason": "stop" }],
  "usage": { "prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30 }
}`,
      },
    ],
  },
  {
    group: "Embeddings",
    routes: [
      {
        method: "POST", path: "/v1/embeddings",
        desc: "Generate vector embeddings",
        auth: "api-key",
        body: `{ "input": "Hello world", "model": "text-embedding-3-small" }`,
        response: `{ "data": [{ "embedding": [0.01, ...], "index": 0 }], "usage": { "total_tokens": 3 } }`,
      },
    ],
  },
  {
    group: "RAG — Collections",
    routes: [
      { method: "GET", path: "/v1/collections", desc: "List all collections", auth: true },
      {
        method: "POST", path: "/v1/collections",
        desc: "Create a new collection",
        auth: true,
        body: `{ "name": "Product Docs", "description": "Product documentation" }`,
      },
      { method: "GET", path: "/v1/collections/{id}", desc: "Get collection with documents", auth: true },
      { method: "DELETE", path: "/v1/collections/{id}", desc: "Delete collection and all documents", auth: true },
      {
        method: "POST", path: "/v1/collections/{id}/search",
        desc: "Semantic search in collection",
        auth: true,
        body: `{ "query": "How to reset password?", "top_k": 5 }`,
      },
    ],
  },
  {
    group: "RAG — Documents",
    routes: [
      {
        method: "POST", path: "/v1/documents",
        desc: "Upload and process document (multipart/form-data)",
        auth: true,
        body: `FormData:\n  collection_id: <uuid>\n  file: <binary>`,
      },
      { method: "GET", path: "/v1/documents/{id}", desc: "Get document status and chunk count", auth: true },
      { method: "DELETE", path: "/v1/documents/{id}", desc: "Delete document and its chunks", auth: true },
    ],
  },
  {
    group: "Memory Chat",
    routes: [
      {
        method: "POST", path: "/v1/memchat/completions",
        desc: "Chat with conversation memory (persists across calls)",
        auth: "api-key",
        body: `{ "agent_id": "<uuid>", "contact_id": "<uuid>", "messages": [{ "role": "user", "content": "Hi" }] }`,
      },
      { method: "GET", path: "/v1/messages?contact_id=<uuid>&limit=100", desc: "Retrieve conversation history", auth: "api-key" },
    ],
  },
  {
    group: "Convert",
    routes: [
      {
        method: "POST", path: "/v1/convert/markdown",
        desc: "Convert uploaded file to markdown",
        auth: "api-key",
        body: `FormData:\n  file: <binary>\n  ocr: false`,
      },
    ],
  },
]

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/15 text-emerald-400",
  POST: "bg-blue-500/15 text-blue-400",
  DELETE: "bg-red-500/15 text-red-400",
  PUT: "bg-amber-500/15 text-amber-400",
  PATCH: "bg-violet-500/15 text-violet-400",
}

export default function DocsPage() {
  const [openGroup, setOpenGroup] = useState<string | null>("Chat Completions")
  const [openRoute, setOpenRoute] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const buildCurl = (r: any) => {
    const auth = r.auth === "api-key"
      ? `-H "x-api-key: sk-your-key"`
      : r.auth ? `-H "Authorization: Bearer <jwt>"` : ""
    const body = r.body && !r.body.startsWith("FormData")
      ? `-H "Content-Type: application/json" -d '${r.body.replace(/\n\s*/g, " ")}'`
      : r.body?.startsWith("FormData") ? `-F "file=@/path/to/file"` : ""
    return `curl -X ${r.method} "${API_BASE}${r.path}" ${auth} ${body}`.trim()
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">API Documentation</h1>
        <p className="text-muted-foreground text-sm">OpenAI-compatible API reference for the NeuralAPI platform</p>
      </div>

      {/* Base URL */}
      <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-3">
        <span className="text-xs text-muted-foreground">Base URL:</span>
        <span className="font-mono text-sm text-primary">{API_BASE}</span>
        <button onClick={() => copy(API_BASE, "base")} className="ml-auto p-1.5 rounded hover:bg-muted">
          {copied === "base" ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-muted-foreground" />}
        </button>
      </div>

      {/* Auth note */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <p className="text-xs text-amber-400 font-semibold mb-1">Authentication</p>
        <p className="text-xs text-muted-foreground">
          External API calls use <code className="bg-muted px-1 rounded">x-api-key: sk-...</code> header.<br />
          Dashboard routes use <code className="bg-muted px-1 rounded">Authorization: Bearer &lt;jwt&gt;</code> from login.
        </p>
      </div>

      {/* Endpoint groups */}
      {endpoints.map(group => (
        <div key={group.group} className="rounded-xl border border-border bg-card overflow-hidden">
          <button
            onClick={() => setOpenGroup(openGroup === group.group ? null : group.group)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-muted/30 transition-colors"
          >
            <h2 className="font-semibold text-sm">{group.group}</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{group.routes.length} endpoints</span>
              {openGroup === group.group
                ? <ChevronDown className="w-4 h-4 text-muted-foreground" />
                : <ChevronRight className="w-4 h-4 text-muted-foreground" />
              }
            </div>
          </button>

          {openGroup === group.group && (
            <div className="border-t border-border divide-y divide-border">
              {group.routes.map(route => {
                const routeId = `${route.method}:${route.path}`
                const isOpen = openRoute === routeId
                return (
                  <div key={routeId}>
                    <button
                      onClick={() => setOpenRoute(isOpen ? null : routeId)}
                      className="w-full flex items-center gap-3 px-5 py-3 hover:bg-muted/20 transition-colors text-left"
                    >
                      <span className={cn("text-xs font-bold px-2 py-0.5 rounded font-mono w-14 text-center", METHOD_COLORS[route.method] || "bg-muted")}>
                        {route.method}
                      </span>
                      <span className="font-mono text-sm text-foreground">{route.path}</span>
                      <span className="text-xs text-muted-foreground ml-2">{route.desc}</span>
                      {route.auth && (
                        <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">
                          {route.auth === "api-key" ? "API Key" : "JWT"}
                        </span>
                      )}
                    </button>

                    {isOpen && (
                      <div className="px-5 pb-4 space-y-3">
                        {route.body && (
                          <div>
                            <p className="text-xs text-muted-foreground mb-1.5">Request Body:</p>
                            <pre className="relative bg-muted rounded-lg p-3 text-xs font-mono overflow-x-auto">
                              {route.body}
                              <button
                                onClick={() => copy(route.body!, routeId + "body")}
                                className="absolute top-2 right-2 p-1 rounded hover:bg-background"
                              >
                                {copied === routeId + "body" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-muted-foreground" />}
                              </button>
                            </pre>
                          </div>
                        )}
                        {(route as any).response && (
                          <div>
                            <p className="text-xs text-muted-foreground mb-1.5">Response:</p>
                            <pre className="bg-muted rounded-lg p-3 text-xs font-mono overflow-x-auto">{(route as any).response}</pre>
                          </div>
                        )}
                        <div>
                          <p className="text-xs text-muted-foreground mb-1.5">cURL Example:</p>
                          <pre className="relative bg-muted rounded-lg p-3 text-xs font-mono overflow-x-auto">
                            {buildCurl(route)}
                            <button
                              onClick={() => copy(buildCurl(route), routeId + "curl")}
                              className="absolute top-2 right-2 p-1 rounded hover:bg-background"
                            >
                              {copied === routeId + "curl" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-muted-foreground" />}
                            </button>
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
