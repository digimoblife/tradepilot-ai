"use client";

import { useEffect, useState } from "react";
import {
  listEvaluationRecords,
  type EvaluationRecordItem,
} from "@/lib/api/evaluations";

export function EvaluationDashboard() {
  const [items, setItems] = useState<EvaluationRecordItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tickerFilter, setTickerFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const res = await listEvaluationRecords({
        ticker: tickerFilter || undefined,
        analysis_type: typeFilter || undefined,
        limit: 50,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [tickerFilter, typeFilter]);

  const handleExport = (format: "json" | "csv") => {
    const query = new URLSearchParams();
    if (tickerFilter) query.set("ticker", tickerFilter);
    if (typeFilter) query.set("analysis_type", typeFilter);
    query.set("limit", "100");

    const endpoint = `/api/evaluation-records/export/${format}?${query.toString()}`;
    window.open(endpoint, "_blank");
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900">Evaluation Records & Dataset</h1>
          <p className="text-xs text-zinc-500">
            Structured records capturing predictions, user decisions, and trade outcomes.
          </p>
        </div>

        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => handleExport("json")}
            className="rounded border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={() => handleExport("csv")}
            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between rounded-lg border border-zinc-200 bg-zinc-50 p-4">
        <div>
          <div className="text-xs text-zinc-500">Total Evaluation Records</div>
          <div className="text-2xl font-bold text-zinc-900">{total}</div>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Filter by ticker (e.g. BBRI)"
            value={tickerFilter}
            onChange={(e) => setTickerFilter(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Analysis Types</option>
            <option value="INITIAL_ANALYSIS">Initial Analysis</option>
            <option value="WATCHING_UPDATE">Watching Update</option>
            <option value="OPEN_POSITION_UPDATE">Open Position Update</option>
            <option value="CLOSING_ANALYSIS">Closing Analysis</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="py-8 text-center text-xs text-zinc-500">Loading evaluation records...</div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center text-xs text-zinc-500">No evaluation records found.</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-zinc-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-zinc-200 bg-zinc-100 font-semibold text-zinc-700">
              <tr>
                <th className="px-4 py-2.5">Ticker</th>
                <th className="px-4 py-2.5">Type</th>
                <th className="px-4 py-2.5">AI Rec.</th>
                <th className="px-4 py-2.5">User Action</th>
                <th className="px-4 py-2.5">Return %</th>
                <th className="px-4 py-2.5">Completeness</th>
                <th className="px-4 py-2.5">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 bg-white text-zinc-700">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-zinc-50">
                  <td className="px-4 py-2.5 font-bold text-zinc-900">{item.ticker}</td>
                  <td className="px-4 py-2.5">{item.analysis_type}</td>
                  <td className="px-4 py-2.5 font-medium">
                    {String(item.prediction_data.recommendation || "-")}
                  </td>
                  <td className="px-4 py-2.5 font-medium">
                    {String(item.user_decision_data.user_action || "-")}
                  </td>
                  <td className="px-4 py-2.5">
                    {item.outcome_data.realized_return
                      ? `${item.outcome_data.realized_return}%`
                      : "-"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-zinc-700">
                      {item.completeness_status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-zinc-500">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
