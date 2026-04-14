"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type School = {
  id: string;
  name_ko: string;
  name_en: string;
  country_code: string;
  email_domain: string;
  school_type: string;
  status: string;
};

export default function AdminSchoolsPage() {
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name_ko: "", name_en: "", country_code: "KR", email_domain: "", school_type: "university" });

  useEffect(() => { void load(); }, [query]);

  async function load() {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (query) qs.set("q", query);
      qs.set("limit", "50");
      const res = await apiFetch<any>(`/admin/schools?${qs}`, { raw: true });
      setSchools(res.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function handleAdd() {
    try {
      await apiFetch("/admin/schools", { method: "POST", body: JSON.stringify(form) });
      setShowAdd(false);
      setForm({ name_ko: "", name_en: "", country_code: "KR", email_domain: "", school_type: "university" });
      void load();
    } catch { /* ignore */ }
  }

  async function toggleStatus(id: string, current: string) {
    const next = current === "active" ? "disabled" : "active";
    try {
      await apiFetch(`/admin/schools/${id}`, { method: "PATCH", body: JSON.stringify({ status: next }) });
      void load();
    } catch { /* ignore */ }
  }

  return (
    <main className="flex-1 min-w-0 max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">학교 관리</h1>
        <button onClick={() => setShowAdd(!showAdd)} className="btn-primary text-sm">+ 학교 추가</button>
      </div>

      {showAdd && (
        <div className="card p-4 mb-4 grid grid-cols-2 gap-3">
          <input placeholder="학교명 (한글) *" value={form.name_ko} onChange={(e) => setForm({ ...form, name_ko: e.target.value })}
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
          <input placeholder="School Name (EN) *" value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })}
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
          <input placeholder="이메일 도메인 * (예: snu.ac.kr)" value={form.email_domain} onChange={(e) => setForm({ ...form, email_domain: e.target.value })}
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none" />
          <div className="flex gap-2">
            <select value={form.country_code} onChange={(e) => setForm({ ...form, country_code: e.target.value })}
              className="bg-background border border-border rounded-lg px-3 py-2 text-sm flex-1">
              <option value="KR">한국</option><option value="JP">일본</option><option value="US">미국</option>
              <option value="GB">영국</option><option value="TW">대만</option><option value="HK">홍콩</option>
            </select>
            <select value={form.school_type} onChange={(e) => setForm({ ...form, school_type: e.target.value })}
              className="bg-background border border-border rounded-lg px-3 py-2 text-sm flex-1">
              <option value="university">종합대학</option><option value="art_school">예술대학</option>
              <option value="academy">아카데미</option><option value="other">기타</option>
            </select>
          </div>
          <div className="col-span-2 flex justify-end gap-2">
            <button onClick={() => setShowAdd(false)} className="text-sm text-text-muted">취소</button>
            <button onClick={handleAdd} className="btn-primary text-sm">등록</button>
          </div>
        </div>
      )}

      <input type="text" placeholder="학교명 검색" value={query} onChange={(e) => setQuery(e.target.value)}
        className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none w-64 mb-4" />

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="card p-4 animate-pulse"><div className="h-4 w-1/2 bg-surface-hover rounded" /></div>
        ))}</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted text-left">
              <tr>
                <th className="px-4 py-3">학교명</th>
                <th className="px-4 py-3">영문명</th>
                <th className="px-4 py-3">도메인</th>
                <th className="px-4 py-3">국가</th>
                <th className="px-4 py-3">유형</th>
                <th className="px-4 py-3">상태</th>
                <th className="px-4 py-3">조치</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {schools.map((s) => (
                <tr key={s.id} className="hover:bg-surface-hover/30">
                  <td className="px-4 py-3 font-medium">{s.name_ko}</td>
                  <td className="px-4 py-3 text-text-muted">{s.name_en}</td>
                  <td className="px-4 py-3 text-primary">{s.email_domain}</td>
                  <td className="px-4 py-3">{s.country_code}</td>
                  <td className="px-4 py-3 text-xs">{s.school_type}</td>
                  <td className="px-4 py-3">
                    <span className={s.status === "active" ? "text-primary" : "text-text-muted"}>{s.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleStatus(s.id, s.status)}
                      className={`text-xs hover:underline ${s.status === "active" ? "text-danger" : "text-primary"}`}>
                      {s.status === "active" ? "비활성화" : "활성화"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
