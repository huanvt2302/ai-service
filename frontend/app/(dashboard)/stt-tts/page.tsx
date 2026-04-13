"use client"

import { Mic, Volume2 } from "lucide-react"

export default function SttTtsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">STT & TTS</h1>
        <p className="text-muted-foreground text-sm">Speech-to-text and text-to-speech services</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="p-2.5 rounded-lg bg-emerald-500/15 w-fit mb-4">
            <Mic className="w-5 h-5 text-emerald-400" />
          </div>
          <h3 className="font-semibold mb-1">Speech to Text (STT)</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Convert audio to text using Whisper or compatible models.
          </p>
          <div className="p-3 rounded-lg border border-dashed border-border text-center">
            <Mic className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">Upload audio file or use microphone</p>
            <p className="text-xs text-muted-foreground mt-1">(Integration coming soon)</p>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="p-2.5 rounded-lg bg-violet-500/15 w-fit mb-4">
            <Volume2 className="w-5 h-5 text-violet-400" />
          </div>
          <h3 className="font-semibold mb-1">Text to Speech (TTS)</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Convert text to natural speech audio.
          </p>
          <textarea
            className="w-full px-3 py-2 rounded-lg border border-border bg-muted/50 text-sm outline-none focus:ring-1 focus:ring-primary resize-none"
            rows={4}
            placeholder="Enter text to synthesize..."
          />
          <button className="mt-3 w-full py-2 rounded-lg bg-primary/15 text-primary text-sm hover:bg-primary/25 transition-colors">
            Generate Audio (coming soon)
          </button>
        </div>
      </div>
    </div>
  )
}
