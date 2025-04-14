"use client";

import { useState, useEffect } from 'react';

interface AgentOutput {
  marketCreationAgent: string;
  oddsManagerAgent: string;
  riskManagerAgent: string;
  gameStatusAgent: string;
}

interface ApiError {
    error: string;
    details?: string;
}

// Simple Robot SVG Icon
const RobotIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-8 h-8 mr-2 inline-block text-blue-400">
    <path d="M12 8V4H8V8H6v8h12V8z" />
    <path d="M16 16v-4h4V8h-4V4h-4v4H8v4h4v4z" />
    <path d="M12 16h.01" />
    <path d="M12 20c-2.21 0-4-1.79-4-4h8c0 2.21-1.79 4-4 4z" />
    <path d="M4 16H2v-4h2M22 16h-2v-4h2" />
  </svg>
);

// Card component for displaying each agent report
const AgentReportCard = ({ title, report }: { title: string; report: string }) => (
  <div className="bg-gray-800 shadow-lg rounded-lg p-6 mb-6 border border-gray-700">
    <h2 className="text-xl font-semibold mb-3 text-blue-300">{title}</h2>
    <p className="text-gray-300 whitespace-pre-wrap">{report}</p>
  </div>
);

export default function AgentReportsPage() {
  const [reports, setReports] = useState<AgentOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReports() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/agent-reports');
        if (!response.ok) {
           const errorData: ApiError = await response.json();
           console.error("API Error:", errorData);
           throw new Error(errorData.details || errorData.error || `HTTP error! status: ${response.status}`);
        }
        const data: AgentOutput = await response.json();
        setReports(data);
      } catch (err: unknown) {
         console.error("Failed to fetch agent reports:", err);
         if (err instanceof Error) {
             setError(`Failed to load reports: ${err.message}`);
         } else {
             setError("An unknown error occurred while loading reports.");
         }
      } finally {
        setLoading(false);
      }
    }

    fetchReports();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8 text-white">
      <h1 className="text-3xl font-bold mb-6 flex items-center">
        <RobotIcon />
        Agent Reports
      </h1>

      {loading && <p className="text-center text-gray-400">Loading reports...</p>}
      {error && <p className="text-center text-red-500 bg-red-900/50 p-4 rounded border border-red-700">{error}</p>}

      {reports && (
        <div>
          <AgentReportCard title="Market Creation Agent Report" report={reports.marketCreationAgent} />
          <AgentReportCard title="Odds Manager Agent Report" report={reports.oddsManagerAgent} />
          <AgentReportCard title="Risk Manager Agent Report" report={reports.riskManagerAgent} />
          <AgentReportCard title="Game Status Agent Report" report={reports.gameStatusAgent} />
        </div>
      )}
    </div>
  );
} 