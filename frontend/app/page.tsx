"use client";

import { useState } from "react";

type Citation = {
  id: string;
  title: string;
  source_file: string;
  source_url: string;
  page: number;
  content_preview: string;
};

type ChatResponse = {
  answer: string;
  citations: Citation[];
  rewritten_query: string;
  subqueries: string[];
  latency_ms: number;
  retrieval_debug?: any[];
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [role, setRole] = useState("employee");
  const [department, setDepartment] = useState("");
  const [docType, setDocType] = useState("");
  const [debug, setDebug] = useState(true);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [rating, setRating] = useState<number>(5);

  async function askQuestion() {
    if (!question.trim()) return;

    setLoading(true);
    setResponse(null);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Roles": role,
      },
      body: JSON.stringify({
        question,
        filters: {
          department: department || null,
          doc_type: docType || null,
        },
        debug,
      }),
    });

    const data = await res.json();
    setResponse(data);
    setLoading(false);
  }

  async function submitFeedback() {
    if (!response) return;

    await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        answer: response.answer,
        rating,
        comment: null,
        citations: response.citations.map((c) => c.source_file),
      }),
    });

    alert("Feedback saved.");
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 bg-slate-900 rounded-2xl p-6 shadow-xl">
          <h1 className="text-3xl font-bold mb-2">
            Enterprise Knowledge Agent
          </h1>

          <p className="text-slate-400 mb-6">
            Agentic RAG with Azure OpenAI, Azure AI Search, hybrid retrieval,
            citations, filters, access control, and feedback.
          </p>

          <textarea
            className="w-full h-32 rounded-xl bg-slate-800 border border-slate-700 p-4 outline-none"
            placeholder="Ask a question from the company knowledge base..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
            <select
              className="bg-slate-800 border border-slate-700 rounded-xl p-3"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="employee">Employee</option>
              <option value="hr">HR</option>
              <option value="finance">Finance</option>
              <option value="legal">Legal</option>
              <option value="admin">Admin</option>
            </select>

            <select
              className="bg-slate-800 border border-slate-700 rounded-xl p-3"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            >
              <option value="">All departments</option>
              <option value="hr">HR</option>
              <option value="finance">Finance</option>
              <option value="legal">Legal</option>
              <option value="product">Product</option>
            </select>

            <select
              className="bg-slate-800 border border-slate-700 rounded-xl p-3"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            >
              <option value="">All document types</option>
              <option value="policy">Policy</option>
              <option value="benefits">Benefits</option>
              <option value="contract">Contract</option>
              <option value="faq">FAQ</option>
            </select>

            <label className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl p-3">
              <input
                type="checkbox"
                checked={debug}
                onChange={(e) => setDebug(e.target.checked)}
              />
              Debug
            </label>
          </div>

          <button
            onClick={askQuestion}
            disabled={loading}
            className="mt-4 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50"
          >
            {loading ? "Thinking..." : "Ask"}
          </button>

          {response && (
            <div className="mt-8">
              <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                <h2 className="text-xl font-semibold mb-3">Answer</h2>
                <p className="whitespace-pre-wrap leading-7">
                  {response.answer}
                </p>
              </div>

              <div className="mt-4 text-sm text-slate-400">
                Latency: {response.latency_ms} ms
              </div>

              <div className="mt-6 bg-slate-800 rounded-xl p-5 border border-slate-700">
                <h2 className="text-lg font-semibold mb-2">Query Plan</h2>
                <p>
                  <span className="text-slate-400">Rewritten query:</span>{" "}
                  {response.rewritten_query}
                </p>

                <ul className="list-disc ml-6 mt-2 text-slate-300">
                  {response.subqueries.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </div>

              <div className="mt-6 bg-slate-800 rounded-xl p-5 border border-slate-700">
                <h2 className="text-lg font-semibold mb-3">Feedback</h2>

                <select
                  className="bg-slate-900 border border-slate-700 rounded-xl p-3"
                  value={rating}
                  onChange={(e) => setRating(Number(e.target.value))}
                >
                  <option value={5}>5 - Excellent</option>
                  <option value={4}>4 - Good</option>
                  <option value={3}>3 - Okay</option>
                  <option value={2}>2 - Poor</option>
                  <option value={1}>1 - Bad</option>
                </select>

                <button
                  onClick={submitFeedback}
                  className="ml-3 px-5 py-3 rounded-xl bg-green-600 hover:bg-green-500"
                >
                  Submit feedback
                </button>
              </div>
            </div>
          )}
        </section>

        <aside className="bg-slate-900 rounded-2xl p-6 shadow-xl">
          <h2 className="text-xl font-bold mb-4">Citations</h2>

          {!response?.citations?.length && (
            <p className="text-slate-500">No citations yet.</p>
          )}

          {response?.citations?.map((citation) => (
            <div
              key={citation.id}
              className="mb-4 p-4 rounded-xl bg-slate-800 border border-slate-700"
            >
              <div className="font-semibold">
                [{citation.id}] {citation.title}
              </div>

              <div className="text-sm text-slate-400 mt-1">
                {citation.source_file} · page {citation.page}
              </div>

              <p className="text-sm mt-3 text-slate-300">
                {citation.content_preview}...
              </p>
            </div>
          ))}

          {response?.retrieval_debug && (
            <div className="mt-8">
              <h2 className="text-xl font-bold mb-4">Retrieval Debug</h2>

              {response.retrieval_debug.map((item, index) => (
                <div
                  key={index}
                  className="mb-3 text-xs p-3 rounded-xl bg-slate-800 border border-slate-700"
                >
                  <div className="font-semibold">{item.title}</div>
                  <div>Score: {item.score}</div>
                  <div>Page: {item.page}</div>
                  <div>File: {item.source_file}</div>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}