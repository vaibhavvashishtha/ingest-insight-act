"use client";
import { useState } from "react";
import useSWR from "swr";
import { sources, ingestion, type DataSource } from "@/lib/api";

const fetcher = () => sources.list();

export default function SourcesPage() {
  const { data, mutate } = useSWR<DataSource[]>("sources", fetcher);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ display_name: "", property_id: "" });

  async function handleAdd() {
    await sources.create({
      connector_type: "ga4",
      display_name: form.display_name,
      config: { property_id: form.property_id },
    });
    setAdding(false);
    setForm({ display_name: "", property_id: "" });
    mutate();
  }

  async function handleExplore(id: string) {
    const res = await fetch(`/api/v1/ingestion/explore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: id }),
    });
    alert("Schema exploration queued");
  }

  async function handleIngest(id: string) {
    const job = await ingestion.trigger({
      source_id: id,
      start_date: "2024-01-01",
      end_date: "2024-01-31",
    });
    alert(`Job ${job.id} queued (status: ${job.status})`);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Data Sources</h1>
        <button
          onClick={() => setAdding(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Add Source
        </button>
      </div>

      {adding && (
        <div className="bg-white border rounded-lg p-6 mb-6">
          <h2 className="font-semibold mb-4">Add GA4 Source</h2>
          <div className="space-y-3">
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="Display name"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder="GA4 Property ID (e.g. 123456789)"
              value={form.property_id}
              onChange={(e) => setForm({ ...form, property_id: e.target.value })}
            />
            <div className="flex gap-2">
              <button onClick={handleAdd} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm">Save</button>
              <button onClick={() => setAdding(false)} className="px-4 py-2 border rounded text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {data?.map((source) => (
          <div key={source.id} className="bg-white border rounded-lg p-4 flex items-center justify-between">
            <div>
              <div className="font-medium">{source.display_name}</div>
              <div className="text-sm text-gray-500">
                {source.connector_type} · Last ingested: {source.last_ingested_at ? new Date(source.last_ingested_at).toLocaleDateString() : "Never"}
              </div>
              {source.schema_map && (
                <div className="text-xs text-green-600 mt-1">{source.schema_map.length} fields mapped</div>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExplore(source.id)}
                className="px-3 py-1.5 border rounded text-xs hover:bg-gray-50"
              >
                Explore Schema
              </button>
              <button
                onClick={() => handleIngest(source.id)}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700"
                disabled={!source.schema_map}
              >
                Ingest Data
              </button>
            </div>
          </div>
        ))}
        {data?.length === 0 && (
          <div className="text-gray-400 text-sm text-center py-12">No sources configured yet.</div>
        )}
      </div>
    </div>
  );
}
