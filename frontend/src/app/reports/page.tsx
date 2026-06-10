"use client";
import useSWR from "swr";
import { reports, insights, type Report, type Insight } from "@/lib/api";
import { useState } from "react";

export default function ReportsPage() {
  const { data: reportList, mutate } = useSWR<Report[]>("reports", () => reports.list());
  const { data: insightList } = useSWR<Insight[]>("insights", () => insights.list());
  const [publishing, setPublishing] = useState(false);
  const [title, setTitle] = useState("");
  const [selected, setSelected] = useState<string[]>([]);

  async function handlePublish() {
    if (!title || !selected.length) return;
    setPublishing(true);
    try {
      await reports.publish({ title, insight_ids: selected });
      setTitle("");
      setSelected([]);
      mutate();
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reports</h1>

      {insightList && insightList.length > 0 && (
        <div className="bg-white border rounded-lg p-6 mb-6">
          <h2 className="font-semibold mb-4">Publish New Report</h2>
          <input
            className="w-full border rounded px-3 py-2 text-sm mb-3"
            placeholder="Report title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <div className="space-y-2 mb-4">
            {insightList.map((insight) => (
              <label key={insight.id} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.includes(insight.id)}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked ? [...selected, insight.id] : selected.filter((id) => id !== insight.id)
                    )
                  }
                />
                {insight.date_range_start} → {insight.date_range_end}
              </label>
            ))}
          </div>
          <button
            onClick={handlePublish}
            disabled={publishing || !title || !selected.length}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
          >
            {publishing ? "Publishing..." : "Publish Report"}
          </button>
        </div>
      )}

      <div className="space-y-3">
        {reportList?.map((report) => (
          <div key={report.id} className="bg-white border rounded-lg p-4">
            <div className="font-medium">{report.title}</div>
            <div className="text-sm text-gray-500 mt-1">
              {report.insight_ids.length} insight(s) · Published {report.published_at ? new Date(report.published_at).toLocaleDateString() : "—"}
            </div>
          </div>
        ))}
        {reportList?.length === 0 && (
          <div className="text-gray-400 text-sm text-center py-12">No reports yet.</div>
        )}
      </div>
    </div>
  );
}
