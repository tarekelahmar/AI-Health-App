import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { MetricSeriesResponse } from "../types/MetricSeries";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export function MetricChart({ series, title }: { series: MetricSeriesResponse; title: string }) {
  if (!series.points || series.points.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h3 className="font-semibold mb-2">{title}</h3>
        <p className="text-sm text-gray-500">No data available for this metric yet.</p>
      </div>
    );
  }

  const labels = series.points.map((p) => new Date(p.timestamp).toLocaleDateString());
  const values = series.points.map((p) => p.value);

  const baselineMean = series.baseline.mean;
  const baselineUpper = baselineMean + series.baseline.std;
  const baselineLower = baselineMean - series.baseline.std;

  const data = {
    labels,
    datasets: [
      {
        label: title,
        data: values,
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.1)",
        tension: 0.2,
      },
      {
        label: "Baseline Mean",
        data: labels.map(() => baselineMean),
        borderColor: "#16a34a",
        borderDash: [6, 6],
        pointRadius: 0,
      },
      {
        label: "+1 Std",
        data: labels.map(() => baselineUpper),
        borderColor: "#22c55e",
        borderDash: [2, 4],
        pointRadius: 0,
      },
      {
        label: "-1 Std",
        data: labels.map(() => baselineLower),
        borderColor: "#22c55e",
        borderDash: [2, 4],
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 2,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
      tooltip: {
        enabled: true,
      },
    },
    scales: {
      y: {
        beginAtZero: false,
        ticks: {
          precision: 1,
        },
      },
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 0,
        },
      },
    },
  };

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <h3 className="font-semibold mb-2">{title}</h3>
      <div className="h-64 w-full">
        <Line data={data} options={options} />
      </div>
      <div className="text-xs text-gray-500 mt-2">
        {series.points.length} data points • Baseline: {baselineMean.toFixed(1)} ± {series.baseline.std.toFixed(1)}
      </div>
    </div>
  );
}

