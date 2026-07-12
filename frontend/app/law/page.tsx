"use client";

import { useState } from "react";
import { Search, BookOpen } from "lucide-react";
import { lawSearch } from "@/lib/api";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import type { LawSearchResult } from "@/types";

const TOPICS = ["全部", "工時", "加班費", "休假", "資遣", "工資"];

const docTypeLabel: Record<string, { label: string; color: string }> = {
  statute: { label: "法條", color: "bg-navy-50 text-navy-700" },
  enforcement_rule: { label: "施行細則", color: "bg-blue-100 text-blue-700" },
  interpretation: { label: "函釋", color: "bg-indigo-100 text-indigo-700" },
  judgment: { label: "判決", color: "bg-purple-100 text-purple-700" },
  arbitration: { label: "仲裁", color: "bg-orange-100 text-orange-700" },
};

export default function LawPage() {
  const [query, setQuery] = useState("");
  const [activeTopic, setActiveTopic] = useState("全部");
  const [results, setResults] = useState<LawSearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(q?: string) {
    const searchQ = q ?? query;
    if (!searchQ.trim()) return;
    setLoading(true);
    setResults(null);
    try {
      const res = await lawSearch(searchQ);
      setResults(res.results);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-black text-ink">法條查詢</h1>
        <p className="text-[15px] text-muted mt-1">搜尋勞基法條文、函釋與相關判決</p>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="輸入關鍵字，例如：年假、加班費..."
          className="flex-1 border border-line rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-navy"
        />
        <button
          onClick={() => handleSearch()}
          disabled={!query.trim() || loading}
          className="flex items-center gap-1.5 bg-gradient-to-b from-navy-600 to-navy-800 text-white rounded-xl px-4 py-3 font-bold hover:brightness-110 disabled:opacity-50 transition-colors"
        >
          <Search size={16} /> 搜尋
        </button>
      </div>

      {/* Topic tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {TOPICS.map((topic) => (
          <button
            key={topic}
            onClick={() => { setActiveTopic(topic); handleSearch(topic === "全部" ? query : topic); }}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeTopic === topic
                ? "bg-navy text-white"
                : "bg-card border border-line text-ink hover:border-navy-600"
            }`}
          >
            {topic}
          </button>
        ))}
      </div>

      {/* Results */}
      {loading && <LoadingSkeleton lines={5} />}

      {results !== null && (
        <div className="space-y-3">
          <p className="text-sm text-muted">找到 {results.length} 筆結果</p>
          {results.length === 0 && (
            <div className="text-center py-12 text-muted">找不到相關法條，請嘗試其他關鍵字</div>
          )}
          {results.map((r) => {
            const dt = docTypeLabel[r.doc_type] ?? { label: r.doc_type, color: "bg-gray-100 text-gray-600" };
            return (
              <a
                key={r.article_no}
                href={r.source_url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-card border border-line rounded-2xl p-4 hover:border-navy-600 transition-colors space-y-2"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${dt.color}`}>{dt.label}</span>
                  <span className="font-bold text-ink">{r.title}</span>
                </div>
                <p className="text-sm text-muted line-clamp-3">{r.snippet}</p>
              </a>
            );
          })}
        </div>
      )}

      {results === null && !loading && (
        <div className="text-center py-12 space-y-2">
          <BookOpen size={36} strokeWidth={1.5} className="mx-auto text-muted" />
          <p className="text-muted text-sm">輸入關鍵字或選擇主題開始搜尋</p>
        </div>
      )}
    </div>
  );
}
