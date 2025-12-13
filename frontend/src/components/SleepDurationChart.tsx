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

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

type Props = {
  series: MetricSeriesResponse;
};

export function SleepDurationChart({ series }: Props) {
  const labels = series.points.map((p) =>
    new Date(p.timestamp).toLocaleDateString()
  );

  const values = series.points.map((p) => p.value);

  const baselineMean = series.baseline.mean;
  const baselineUpper = baselineMean + series.baseline.std;
  const baselineLower = baselineMean - series.baseline.std;

  const data = {
    labels,
    datasets: [
      {
        label: "Sleep Duration",
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

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <h3 className="font-semibold mb-2">Sleep Duration</h3>
      <Line data={data} />
    </div>
  );
}

