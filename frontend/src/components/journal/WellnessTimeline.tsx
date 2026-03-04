import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { Card } from '../ui/Card';
import type { WellnessScore } from '../../types/WellnessScore';

interface WellnessTimelineProps {
  scores: WellnessScore[];
  selectedDate: string | null;
  onDateSelect: (date: string) => void;
}

function scoreColor(score: number): string {
  if (score >= 70) return '#10b981'; // green
  if (score >= 50) return '#f59e0b'; // amber
  return '#ef4444';                   // red
}

function formatDay(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500 text-white';
  if (score >= 60) return 'bg-amber-500 text-white';
  if (score >= 40) return 'bg-orange-500 text-white';
  return 'bg-red-500 text-white';
}

/** Compute 7-day moving average. */
function movingAverage(data: { date: string; score: number }[], window: number = 7) {
  return data.map((d, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = data.slice(start, i + 1);
    const avg = slice.reduce((sum, s) => sum + s.score, 0) / slice.length;
    return { date: d.date, score: avg };
  });
}

/** Compute key metrics from score data. */
function computeMetrics(scores: WellnessScore[]) {
  if (scores.length === 0) return null;
  const vals = scores.map((s) => s.score);
  const current = vals[0];
  const avg7 = vals.slice(0, 7).reduce((a, b) => a + b, 0) / Math.min(vals.length, 7);
  const avg30 = vals.reduce((a, b) => a + b, 0) / vals.length;
  const floor = Math.min(...vals);
  const ceiling = Math.max(...vals);
  const mean = avg30;
  const variance = vals.reduce((sum, v) => sum + (v - mean) ** 2, 0) / vals.length;
  const volatility = Math.sqrt(variance);

  // Trend: compare recent 7 vs previous 7
  let trend: 'up' | 'down' | 'stable' = 'stable';
  if (vals.length >= 14) {
    const r7 = vals.slice(0, 7).reduce((a, b) => a + b, 0) / 7;
    const p7 = vals.slice(7, 14).reduce((a, b) => a + b, 0) / 7;
    if (r7 - p7 > 3) trend = 'up';
    else if (p7 - r7 > 3) trend = 'down';
  }

  return { current, avg7, avg30, floor, ceiling, volatility, trend };
}

export function WellnessTimeline({ scores, selectedDate, onDateSelect }: WellnessTimelineProps) {
  const chartRef = useRef<SVGSVGElement>(null);
  const recent = scores.slice(0, 7).reverse();
  const metrics = computeMetrics(scores);

  // D3 area chart for 30-day trend
  useEffect(() => {
    if (!chartRef.current || scores.length <= 1) return;

    const svg = d3.select(chartRef.current);
    svg.selectAll('*').remove();

    const width = chartRef.current.clientWidth || 320;
    const height = 120;
    const margin = { top: 8, right: 8, bottom: 20, left: 30 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const data = scores
      .slice(0, 30)
      .reverse()
      .map((s) => ({ date: s.score_date, score: s.score }));

    const maData = movingAverage(data);

    const x = d3.scalePoint()
      .domain(data.map((d) => d.date))
      .range([0, innerW]);

    const y = d3.scaleLinear()
      .domain([0, 100])
      .range([innerH, 0]);

    const g = svg
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Area
    const area = d3.area<{ date: string; score: number }>()
      .x((d) => x(d.date)!)
      .y0(innerH)
      .y1((d) => y(d.score))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(data)
      .attr('d', area)
      .attr('fill', '#6366f1')
      .attr('fill-opacity', 0.1);

    // Score line
    const line = d3.line<{ date: string; score: number }>()
      .x((d) => x(d.date)!)
      .y((d) => y(d.score))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(data)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.4);

    // 7-day MA line
    g.append('path')
      .datum(maData)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 2);

    // Score dots
    g.selectAll('.dot')
      .data(data)
      .enter()
      .append('circle')
      .attr('cx', (d) => x(d.date)!)
      .attr('cy', (d) => y(d.score))
      .attr('r', 3)
      .attr('fill', (d) => scoreColor(d.score))
      .attr('stroke', 'white')
      .attr('stroke-width', 1);

    // X axis (every 7th date)
    const xAxis = d3.axisBottom(x).tickValues(
      data.filter((_d, i) => i % 7 === 0).map((d) => d.date),
    );
    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(xAxis)
      .selectAll('text')
      .attr('font-size', '9px')
      .attr('fill', '#9ca3af')
      .text((d) => formatDate(d as string));

    // Y axis
    g.append('g')
      .call(d3.axisLeft(y).ticks(3).tickFormat((d) => `${d}`))
      .selectAll('text')
      .attr('font-size', '9px')
      .attr('fill', '#9ca3af');

    // Remove axis lines
    g.selectAll('.domain').remove();
    g.selectAll('.tick line').attr('stroke', '#f3f4f6');

  }, [scores]);

  if (recent.length === 0) return null;

  return (
    <Card>
      {/* Last 7 day circles */}
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Last 7 Days</h3>
      <div className="flex items-end justify-between gap-1">
        {recent.map((ws) => {
          const isSelected = ws.score_date === selectedDate;
          return (
            <button
              key={ws.score_date}
              onClick={() => onDateSelect(ws.score_date)}
              className={`flex flex-col items-center flex-1 min-w-0 p-1 rounded-lg transition-colors ${
                isSelected ? 'bg-gray-100' : 'hover:bg-gray-50'
              }`}
            >
              <span className="text-[10px] text-gray-400 mb-1">{formatDay(ws.score_date)}</span>
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold ${getScoreColor(ws.score)} ${
                  isSelected ? 'ring-2 ring-primary-500 ring-offset-1' : ''
                }`}
              >
                {Math.round(ws.score)}
              </div>
              <span className="text-[10px] text-gray-400 mt-1">{formatDate(ws.score_date)}</span>
            </button>
          );
        })}
      </div>

      {/* Key metrics */}
      {metrics && (
        <div className="grid grid-cols-4 gap-2 mt-4 pt-3 border-t border-gray-100">
          <div className="text-center">
            <div className="text-xs text-gray-400">7d avg</div>
            <div className="text-sm font-semibold text-gray-700">{Math.round(metrics.avg7)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400">30d avg</div>
            <div className="text-sm font-semibold text-gray-700">{Math.round(metrics.avg30)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400">Floor</div>
            <div className="text-sm font-semibold text-gray-700">{Math.round(metrics.floor)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400">Trend</div>
            <div className="text-sm font-semibold">
              {metrics.trend === 'up' && <span className="text-emerald-500">{'\u2191'}</span>}
              {metrics.trend === 'down' && <span className="text-red-500">{'\u2193'}</span>}
              {metrics.trend === 'stable' && <span className="text-gray-400">{'\u2192'}</span>}
            </div>
          </div>
        </div>
      )}

      {/* D3 area chart for 30-day trend */}
      {scores.length > 7 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="text-xs text-gray-500">30-Day Trend</h4>
            <span className="flex items-center gap-1">
              <span className="w-3 border-t-2 border-indigo-500" />
              <span className="text-[9px] text-gray-400">7d avg</span>
            </span>
          </div>
          <svg ref={chartRef} className="w-full" style={{ height: 120 }} />
        </div>
      )}
    </Card>
  );
}
