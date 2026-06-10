"use client";
import useSWR from "swr";
import { insights, sources, type Insight, type DataSource } from "@/lib/api";
import { useState } from "react";

export default function InsightsPage() {
  const { data: insightList, mutate } = useSWR<Insight[]>("insights", () => insights.list());
  const { data: sourceList } = useSWR<DataSource[]>("sources", () => sources.list());
  const [generating, setGenerating] = useState(false);

  async function handleGenerate() {
    if (!sourceList?.length) return;
    setGenerating(true);
    try {
      await insights.generate({
        source_ids: sourceList.map((s) => s.id),
        start_date: "2024-01-01",
        end_date: "2024-01-31",
        template_slug: "weekly_insights",
      });
      mutate();
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Insights</h1>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Insights"}
        </button>
      </div>

      <div className="space-y-4">
        {insightList?.map((insight) => {
          const content = insight.content as Record<string, unknown>;
          return (
            <div key={insight.id} className="bg-white border rounded-lg p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm text-gray-500">
                  {insight.date_range_start} → {insight.date_range_end}
                </div>
                <div className="text-xs text-gray-400">{insight.model_used}</div>
              </div>
              {typeof content.summary === "string" && (
                <p className="text-sm text-gray-700 mb-4">{content.summary}</p>
              )}
              {Array.isArray(content.next_actions) && (
                <div>
                  <div className="text-xs font-medium text-gray-500 uppercase mb-2">Next Actions</div>
                  <ul className="space-y-1">
                    {(content.next_actions as string[]).map((action, i) => (
                      <li key={i} className="text-sm flex gap-2">
                        <span className="text-indigo-500">→</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
        {insightList?.length === 0 && (
          <div className="text-gray-400 text-sm text-center py-12">No insights yet. Ingest data first, then generate insights.</div>
        )}
      </div>
    </div>
  );
}
