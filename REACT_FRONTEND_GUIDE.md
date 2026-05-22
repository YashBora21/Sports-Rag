# React Next.js TypeScript Frontend - Complete Code Templates

## Setup Instructions

```bash
# 1. In parent directory of sports-rag:
cd ..
npx create-next-app@latest sports-rag-frontend \
  --typescript \
  --tailwind \
  --eslint \
  --src-dir \
  --app \
  --import-alias "@/*" \
  --no-git

cd sports-rag-frontend
npm install axios

# 2. Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 3. Replace/create files below
# 4. Run: npm run dev
# 5. Visit: http://localhost:3000
```

---

## 1. src/lib/api.ts

```typescript
import axios, { AxiosInstance } from "axios";

export interface SourceChunk {
  text: string;
  sport: string;
  source: string;
  metadata: Record<string, any>;
  rerank_score: number;
}

export interface QueryRequest {
  question: string;
  sport_filter?: string;
  top_k?: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: SourceChunk[];
  latency_ms: Record<string, number>;
  sport_filter?: string;
}

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  version: string;
  index_vectors: number;
  components: Record<string, { status: string; detail?: string }>;
  uptime_s: number;
}

class SportsRAGApi {
  private client: AxiosInstance;

  constructor(baseURL: string = "http://localhost:8000") {
    this.client = axios.create({
      baseURL,
      headers: { "Content-Type": "application/json" },
      timeout: 60000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 503) {
          throw new Error("API is loading. Please wait...");
        }
        throw error;
      }
    );
  }

  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>("/query", request);
    return response.data;
  }

  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>("/health");
    return response.data;
  }
}

export const api = new SportsRAGApi(
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
);
```

---

## 2. src/types/index.ts

```typescript
export type Sport = "football" | "basketball" | "cricket" | "tennis" | "";

export const SPORTS: { value: Sport; label: string }[] = [
  { value: "", label: "All Sports" },
  { value: "football", label: "Football 🏆" },
  { value: "basketball", label: "Basketball 🏀" },
  { value: "cricket", label: "Cricket 🏏" },
  { value: "tennis", label: "Tennis 🎾" },
];

export const EXAMPLE_QUESTIONS = [
  "Who won the 2022 FIFA World Cup?",
  "What is Cristiano Ronaldo's international goal record?",
  "Who won the 2023 NBA Championship?",
  "What is the IPL 2024 champion?",
  "Which country won the most Olympic medals?",
];
```

---

## 3. src/components/SearchBar.tsx

```typescript
import React from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export function SearchBar({
  value,
  onChange,
  onSubmit,
  disabled = false,
  loading = false,
}: SearchBarProps) {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !disabled && !loading) {
      onSubmit();
    }
  };

  return (
    <div className="w-full">
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about sports... (e.g., Who won the 2022 World Cup?)"
          disabled={disabled || loading}
          className="w-full px-4 py-3 pl-12 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        <MagnifyingGlassIcon className="absolute w-5 h-5 text-gray-400 left-3 top-3.5" />
        <button
          onClick={onSubmit}
          disabled={disabled || loading || !value.trim()}
          className="absolute right-2 top-2.5 px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "..." : "Ask"}
        </button>
      </div>
    </div>
  );
}
```

---

## 4. src/components/SportFilter.tsx

```typescript
import React from "react";
import { SPORTS, type Sport } from "@/types";

interface SportFilterProps {
  selected: Sport;
  onChange: (sport: Sport) => void;
}

export function SportFilter({ selected, onChange }: SportFilterProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {SPORTS.map((sport) => (
        <button
          key={sport.value}
          onClick={() => onChange(sport.value)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            selected === sport.value
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-800 hover:bg-gray-300"
          }`}
        >
          {sport.label}
        </button>
      ))}
    </div>
  );
}
```

---

## 5. src/components/ResultsDisplay.tsx

```typescript
import React from "react";
import { SourceChunk } from "@/lib/api";

interface ResultsDisplayProps {
  answer: string;
  sources: SourceChunk[];
  latency_ms: Record<string, number>;
  loading?: boolean;
}

export function ResultsDisplay({
  answer,
  sources,
  latency_ms,
  loading = false,
}: ResultsDisplayProps) {
  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-24 bg-gray-200 rounded-lg"></div>
        <div className="h-32 bg-gray-200 rounded-lg"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Answer */}
      <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-600">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Answer</h3>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
          {answer}
        </p>
        <p className="text-xs text-gray-500 mt-4">
          ⏱️ Retrieval: {latency_ms?.retrieval_ms}ms | LLM: {latency_ms?.llm_ms}
          ms | Total: {latency_ms?.total_ms}ms
        </p>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            📚 Retrieved Sources ({sources.length})
          </h3>
          <div className="space-y-3">
            {sources.map((source, idx) => (
              <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex justify-between items-start mb-2">
                  <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
                    {source.sport.toUpperCase()}
                  </span>
                  {source.rerank_score > 0 && (
                    <span className="text-xs text-gray-600">
                      Score: {(source.rerank_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-700 line-clamp-3 mb-2">
                  {source.text}
                </p>
                <p className="text-xs text-gray-500">
                  📌 {source.source}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 6. src/components/HealthCheck.tsx

```typescript
import React, { useEffect, useState } from "react";
import { api, HealthResponse } from "@/lib/api";
import {
  CheckCircleIcon,
  ExclamationIcon,
  XCircleIcon,
} from "@heroicons/react/24/outline";

export function HealthCheck() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.health();
        setHealth(data);
      } catch (error) {
        console.error("Health check failed:", error);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Every 10s

    return () => clearInterval(interval);
  }, []);

  if (loading) return null;
  if (!health) return null;

  const statusIcon = {
    ok: <CheckCircleIcon className="w-5 h-5 text-green-600" />,
    degraded: <ExclamationIcon className="w-5 h-5 text-yellow-600" />,
    error: <XCircleIcon className="w-5 h-5 text-red-600" />,
  }[health.status];

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-center gap-2 mb-2">
        {statusIcon}
        <span className="font-semibold text-sm">
          API Status: {health.status.toUpperCase()}
        </span>
      </div>
      <p className="text-xs text-gray-600">
        📊 {health.index_vectors.toLocaleString()} vectors | ⏱️ {health.uptime_s.toFixed(1)}s uptime
      </p>
    </div>
  );
}
```

---

## 7. src/app/page.tsx

```typescript
"use client";

import { useState } from "react";
import { api, QueryResponse } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { ResultsDisplay } from "@/components/ResultsDisplay";
import { SportFilter } from "@/components/SportFilter";
import { HealthCheck } from "@/components/HealthCheck";
import { EXAMPLE_QUESTIONS, type Sport } from "@/types";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [sport, setSport] = useState<Sport>("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleQuery = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await api.query({
        question: question.trim(),
        sport_filter: sport || undefined,
        top_k: 5,
      });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to get response. Is the API running?"
      );
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Sports RAG 🏆</h1>
          <p className="text-gray-600 text-sm mt-1">
            Ask any sports question. Powered by Ollama Gemma4 + FAISS
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Health Check */}
        <HealthCheck />

        {/* Search Section */}
        <div className="mt-8 bg-white rounded-lg shadow-md p-6">
          <SearchBar
            value={question}
            onChange={setQuestion}
            onSubmit={handleQuery}
            disabled={loading}
            loading={loading}
          />

          {/* Sport Filter */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Sport (optional)
            </label>
            <SportFilter selected={sport} onChange={setSport} />
          </div>

          {/* Example Questions */}
          {!result && (
            <div className="mt-6">
              <p className="text-sm font-medium text-gray-700 mb-3">
                Try these questions:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setQuestion(q);
                    }}
                    className="text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm font-medium">❌ Error</p>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-8">
            <ResultsDisplay
              answer={result.answer}
              sources={result.sources}
              latency_ms={result.latency_ms}
              loading={loading}
            />
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="mt-8 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-4 text-gray-600">Thinking...</span>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-16 bg-gray-900 text-white py-8 text-center text-sm">
        <p>
          Sports RAG v1.0 | LLM: Ollama Gemma4 | Retrieval: FAISS + BM25 +
          Cross-Encoder
        </p>
      </footer>
    </div>
  );
}
```

---

## 8. src/app/layout.tsx

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sports RAG - AI Sports Q&A",
  description: "Ask questions about sports. Powered by Ollama Gemma4 and FAISS",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

---

## 9. tailwind.config.ts

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#3B82F6",
        secondary: "#10B981",
      },
    },
  },
  plugins: [],
};
export default config;
```

---

## 10. next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Add any other Next.js config here
};

module.exports = nextConfig;
```

---

## Quick Installation

```bash
# 1. Create project
cd ..
npx create-next-app@latest sports-rag-frontend --typescript --tailwind --eslint --src-dir --app --import-alias "@/*" --no-git

# 2. Move into project
cd sports-rag-frontend

# 3. Install axios
npm install axios

# 4. Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 5. Copy the TypeScript files above into:
#    - src/lib/api.ts
#    - src/types/index.ts
#    - src/components/SearchBar.tsx
#    - src/components/SportFilter.tsx
#    - src/components/ResultsDisplay.tsx
#    - src/components/HealthCheck.tsx
#    - src/app/page.tsx
#    - src/app/layout.tsx

# 6. Run!
npm run dev
```

Visit: **http://localhost:3000** 🚀
