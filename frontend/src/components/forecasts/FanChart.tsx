import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { HistoricalPoint, PredictionPoint } from '../../types/Forecast';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface FanChartProps {
  historical: HistoricalPoint[];
  predictions: PredictionPoint[];
  metricLabel: string;
  color?: string;
}

export function FanChart({
  historical,
  predictions,
  metricLabel,
  color = '#0d9488',
}: FanChartProps) {
  if (historical.length === 0 && predictions.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center text-sm text-gray-400">
        No forecast data available
      </div>
    );
  }

  // Build combined labels
  const histLabels = historical.map((p) =>
    new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  );
  const predLabels = predictions.map((p) =>
    new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  );
  const allLabels = [...histLabels, ...predLabels];

  // Historical values (null-padded for prediction segment)
  const histValues = [...historical.map((p) => p.value), ...predictions.map(() => null)];

  // Predicted values (null-padded for historical segment, with overlap at last historical point)
  const predValues = [
    ...historical.slice(0, -1).map(() => null),
    historical.length > 0 ? historical[historical.length - 1].value : null,
    ...predictions.map((p) => p.predicted),
  ];

  // CI bands (null for historical, values for predictions, with start at last historical)
  const makeBand = (accessor: (p: PredictionPoint) => number) => [
    ...historical.slice(0, -1).map(() => null),
    historical.length > 0 ? historical[historical.length - 1].value : null,
    ...predictions.map(accessor),
  ];

  const ci95High = makeBand((p) => p.ci_95_high);
  const ci95Low = makeBand((p) => p.ci_95_low);
  const ci80High = makeBand((p) => p.ci_80_high);
  const ci80Low = makeBand((p) => p.ci_80_low);

  const data = {
    labels: allLabels,
    datasets: [
      // 95% CI upper bound (for filling to lower)
      {
        label: '95% CI',
        data: ci95High,
        borderColor: 'transparent',
        backgroundColor: `${color}0d`,
        fill: '+4', // fill between this and ci95Low (dataset index offset)
        pointRadius: 0,
        pointHitRadius: 0,
      },
      // 80% CI upper bound
      {
        label: '80% CI',
        data: ci80High,
        borderColor: 'transparent',
        backgroundColor: `${color}1a`,
        fill: '+2', // fill between this and ci80Low
        pointRadius: 0,
        pointHitRadius: 0,
      },
      // Predicted line
      {
        label: 'Forecast',
        data: predValues,
        borderColor: color,
        borderDash: [6, 4],
        borderWidth: 2,
        pointRadius: 0,
        pointHitRadius: 8,
        fill: false,
        spanGaps: true,
      },
      // 80% CI lower bound
      {
        label: '80% CI low',
        data: ci80Low,
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        pointRadius: 0,
        pointHitRadius: 0,
        fill: false,
      },
      // 95% CI lower bound
      {
        label: '95% CI low',
        data: ci95Low,
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        pointRadius: 0,
        pointHitRadius: 0,
        fill: false,
      },
      // Historical line (drawn on top)
      {
        label: metricLabel,
        data: histValues,
        borderColor: color,
        borderWidth: 2,
        pointRadius: 2,
        pointBackgroundColor: color,
        pointHitRadius: 8,
        fill: false,
        spanGaps: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          pointStyle: 'line' as const,
          padding: 12,
          font: { size: 10 },
          filter: (item: any) => {
            // Only show meaningful legend entries
            return ['Forecast', metricLabel].includes(item.text);
          },
        },
      },
      tooltip: {
        enabled: true,
        callbacks: {
          label: (ctx: any) => {
            if (ctx.raw === null) return '';
            return `${ctx.dataset.label}: ${ctx.raw.toFixed(1)}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { size: 10 },
          maxRotation: 45,
        },
      },
      y: {
        beginAtZero: false,
        grid: { color: '#f3f4f6' },
        ticks: {
          font: { size: 10 },
          precision: 1,
        },
      },
    },
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div style={{ height: 280 }}>
        <Line data={data} options={options} />
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-400">
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5" style={{ backgroundColor: color }} />
          <span>Historical</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 border-t-2 border-dashed" style={{ borderColor: color }} />
          <span>Forecast</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: `${color}1a` }} />
          <span>80% CI</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: `${color}0d` }} />
          <span>95% CI</span>
        </div>
      </div>
    </div>
  );
}
