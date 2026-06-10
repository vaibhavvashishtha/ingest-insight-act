"use client";
import useSWR from "swr";
import { campaigns, type CampaignPlan } from "@/lib/api";
import { useState } from "react";

const CHANNELS = ["paid_search", "paid_social", "email", "organic", "display"];

export default function CampaignsPage() {
  const { data: planList, mutate } = useSWR<CampaignPlan[]>("campaign-plans", () => campaigns.listPlans());
  const [creating, setCreating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ title: "", objective: "", budget: "", channels: [] as string[], duration_weeks: 4 });

  async function handleCreate() {
    setCreating(true);
    try {
      await campaigns.createPlan({
        title: form.title,
        objective: form.objective,
        budget: form.budget ? Number(form.budget) : undefined,
        channels: form.channels,
        duration_weeks: form.duration_weeks,
      });
      setForm({ title: "", objective: "", budget: "", channels: [], duration_weeks: 4 });
      mutate();
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Campaign Plans</h1>
        <button
          onClick={() => setGenerating(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + New Plan
        </button>
      </div>

      {generating && (
        <div className="bg-white border rounded-lg p-6 mb-6">
          <h2 className="font-semibold mb-4">Create Campaign Plan</h2>
          <div className="space-y-3">
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="Campaign title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="Objective (e.g. increase brand awareness, drive purchases)"
              value={form.objective}
              onChange={(e) => setForm({ ...form, objective: e.target.value })}
            />
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="Budget (optional)"
              type="number"
              value={form.budget}
              onChange={(e) => setForm({ ...form, budget: e.target.value })}
            />
            <div>
              <div className="text-xs text-gray-500 mb-2">Channels</div>
              <div className="flex flex-wrap gap-2">
                {CHANNELS.map((ch) => (
                  <label key={ch} className="flex items-center gap-1.5 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.channels.includes(ch)}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          channels: e.target.checked ? [...form.channels, ch] : form.channels.filter((c) => c !== ch),
                        })
                      }
                    />
                    {ch}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !form.title || !form.objective}
                className="px-4 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
              >
                {creating ? "Generating..." : "Generate Plan"}
              </button>
              <button onClick={() => setGenerating(false)} className="px-4 py-2 border rounded text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {planList?.map((plan) => {
          const content = plan.plan_content as Record<string, unknown>;
          return (
            <div key={plan.id} className="bg-white border rounded-lg p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold">{plan.title}</div>
                  <div className="text-sm text-gray-500 mt-1">{plan.objective}</div>
                </div>
                <span className="text-xs px-2 py-1 bg-gray-100 rounded-full">{plan.status}</span>
              </div>
              {plan.budget && (
                <div className="text-sm text-gray-600 mt-2">Budget: ${plan.budget.toLocaleString()}</div>
              )}
              {plan.channels.length > 0 && (
                <div className="flex gap-1.5 mt-2 flex-wrap">
                  {plan.channels.map((ch) => (
                    <span key={ch} className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded-full">{ch}</span>
                  ))}
                </div>
              )}
              {typeof content.executive_summary === "string" && (
                <p className="text-sm text-gray-600 mt-3 border-t pt-3">{content.executive_summary}</p>
              )}
            </div>
          );
        })}
        {planList?.length === 0 && (
          <div className="text-gray-400 text-sm text-center py-12">No campaign plans yet.</div>
        )}
      </div>
    </div>
  );
}
