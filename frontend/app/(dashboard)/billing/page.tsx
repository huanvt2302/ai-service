"use client"

import { useEffect, useState } from "react"
import { billingApi } from "@/lib/api"
import { CreditCard, Zap, Mic, Volume2, Code, CheckCircle } from "lucide-react"
import { formatNumber, pct } from "@/lib/utils"
import { cn } from "@/lib/utils"

const PLANS = [
  {
    name: "Free",
    id: "free",
    price: 0,
    features: ["100K tokens / month", "60 min STT", "60 min TTS", "50K coding tokens", "3 API keys"],
  },
  {
    name: "Pro",
    id: "pro",
    price: 49,
    features: ["5M tokens / month", "600 min STT", "600 min TTS", "2M coding tokens", "Unlimited API keys"],
    highlighted: true,
  },
  {
    name: "Enterprise",
    id: "enterprise",
    price: 299,
    features: ["50M tokens / month", "6,000 min STT", "6,000 min TTS", "20M coding tokens", "SSO + SAML", "Priority support"],
  },
]

const SERVICE_ICONS: Record<string, React.ElementType> = {
  chat: Zap,
  stt: Mic,
  tts: Volume2,
  coding: Code,
}

export default function BillingPage() {
  const [quota, setQuota] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState<string | null>(null)

  useEffect(() => {
    billingApi.getQuota()
      .then(setQuota)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const upgrade = async (plan: string) => {
    if (!confirm(`Upgrade to ${plan} plan?`)) return
    setUpgrading(plan)
    try {
      await billingApi.upgrade(plan)
      const q = await billingApi.getQuota()
      setQuota(q)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setUpgrading(null)
    }
  }

  const currentPlan = quota?.plan || "free"

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing & Quota</h1>
        <p className="text-muted-foreground text-sm">Manage your subscription and monitor usage limits</p>
      </div>

      {/* Current quota */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold">Current Usage</h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground capitalize">Plan:</span>
            <span className="px-2.5 py-0.5 rounded-full bg-primary/15 text-primary text-xs font-semibold capitalize">
              {currentPlan}
            </span>
          </div>
        </div>
        {loading ? (
          <div className="grid grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-20 rounded-xl shimmer" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {(quota?.quotas || []).map((q: any) => {
              const Icon = SERVICE_ICONS[q.service] || Zap
              const p = pct(q.used, q.limit)
              return (
                <div key={q.service} className="p-4 rounded-xl border border-border bg-muted/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">{q.name}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {formatNumber(q.used)} / {formatNumber(q.limit)} {q.unit}
                  </p>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all", p > 80 ? "bg-red-500" : "bg-brand-gradient")}
                      style={{ width: `${p}%` }}
                    />
                  </div>
                  <p className={cn("text-xs mt-1", p > 80 ? "text-red-400" : "text-muted-foreground")}>{p}% used</p>
                </div>
              )
            })}
          </div>
        )}
        {quota?.next_billing_date && (
          <p className="text-xs text-muted-foreground mt-4">
            Next billing: {new Date(quota.next_billing_date).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Plan cards */}
      <div>
        <h2 className="font-semibold mb-4">Plans</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map(plan => (
            <div
              key={plan.id}
              className={cn(
                "rounded-xl border p-6 transition-all",
                plan.highlighted
                  ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                  : "border-border bg-card",
                currentPlan === plan.id && "ring-2 ring-emerald-500/50"
              )}
            >
              {plan.highlighted && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary text-primary-foreground font-medium">Most Popular</span>
              )}
              <h3 className="text-lg font-bold mt-2">{plan.name}</h3>
              <div className="flex items-end gap-1 my-3">
                <span className="text-3xl font-bold">${plan.price}</span>
                <span className="text-muted-foreground text-sm mb-1">/mo</span>
              </div>
              <ul className="space-y-2 mb-5">
                {plan.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => upgrade(plan.id)}
                disabled={currentPlan === plan.id || upgrading !== null}
                className={cn(
                  "w-full py-2 rounded-lg text-sm font-medium transition-all",
                  currentPlan === plan.id
                    ? "bg-emerald-500/15 text-emerald-400 cursor-default"
                    : "bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50"
                )}
              >
                {currentPlan === plan.id ? "Current Plan" : upgrading === plan.id ? "Upgrading..." : `Upgrade to ${plan.name}`}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
