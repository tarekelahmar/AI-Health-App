import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler);

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillColor?: string;
  showBaseline?: boolean;
  baselineValue?: number;
}

export function Sparkline({
  data,
  width = 120,
  height = 36,
  color = '#0d9488',
  fillColor,
  showBaseline = false,
  baselineValue,
}: SparklineProps) {
  if (!data || data.length === 0) {
    return <div style={{ width, height }} className="bg-gray-50 rounded" />;
  }

  const labels = data.map((_, i) => i.toString());

  const datasets: any[] = [
    {
      data,
      borderColor: color,
      backgroundColor: fillColor || `${color}1a`,
      borderWidth: 1.5,
      tension: 0.3,
      fill: !!fillColor,
      pointRadius: 0,
      pointHitRadius: 0,
    },
  ];

  if (showBaseline && baselineValue !== undefined) {
    datasets.push({
      data: labels.map(() => baselineValue),
      borderColor: '#9ca3af',
      borderWidth: 1,
      borderDash: [3, 3],
      pointRadius: 0,
      pointHitRadius: 0,
      fill: false,
    });
  }

  const chartData = { labels, datasets };

  const options = {
    responsive: false,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
    },
    scales: {
      x: { display: false },
      y: { display: false },
    },
    elements: {
      point: { radius: 0 },
    },
  };

  return (
    <div style={{ width, height }}>
      <Line data={chartData} options={options} width={width} height={height} />
    </div>
  );
}
