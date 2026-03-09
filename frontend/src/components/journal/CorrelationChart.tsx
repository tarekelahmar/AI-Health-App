import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { Card } from '../ui/Card';
import type { JournalPatternData } from '../../types/JournalFactors';

interface CorrelationChartProps {
  patterns: JournalPatternData[];
  minEntries?: number;
}

type BarData = {
  label: string;
  lift: number;
  type: string;
};

export function CorrelationChart({ patterns, minEntries = 15 }: CorrelationChartProps) {
  const chartRef = useRef<SVGSVGElement>(null);

  // Convert patterns to lift/drop bars
  const bars: BarData[] = patterns
    .filter((p) => p.n_observations >= 5)
    .map((p) => ({
      label: p.pattern_name,
      lift: +(p.mean_with - p.mean_without).toFixed(1),
      type: p.pattern_type,
    }))
    .sort((a, b) => b.lift - a.lift);

  useEffect(() => {
    if (!chartRef.current || bars.length === 0) return;

    const svg = d3.select(chartRef.current);
    svg.selectAll('*').remove();

    const width = chartRef.current.clientWidth || 320;
    const barHeight = 28;
    const height = bars.length * barHeight + 30;
    const margin = { top: 4, right: 40, bottom: 4, left: 120 };
    const innerW = width - margin.left - margin.right;
    const innerH = bars.length * barHeight;

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const maxAbs = d3.max(bars, (d) => Math.abs(d.lift)) || 3;

    const x = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([0, innerW]).nice();
    const y = d3.scaleBand<string>().domain(bars.map((d) => d.label)).range([0, innerH]).padding(0.3);

    // Zero line
    g.append('line')
      .attr('x1', x(0)).attr('x2', x(0))
      .attr('y1', 0).attr('y2', innerH)
      .attr('stroke', '#d1d5db')
      .attr('stroke-width', 1);

    // Bars
    g.selectAll('.bar')
      .data(bars)
      .enter()
      .append('rect')
      .attr('x', (d) => (d.lift >= 0 ? x(0) : x(d.lift)))
      .attr('y', (d) => y(d.label)!)
      .attr('width', (d) => Math.abs(x(d.lift) - x(0)))
      .attr('height', y.bandwidth())
      .attr('rx', 3)
      .attr('fill', (d) => (d.lift >= 0 ? '#10b981' : '#ef4444'))
      .attr('fill-opacity', 0.8);

    // Labels (left)
    g.selectAll('.label')
      .data(bars)
      .enter()
      .append('text')
      .attr('x', -6)
      .attr('y', (d) => y(d.label)! + y.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#6b7280')
      .text((d) => d.label);

    // Value labels (on bars)
    g.selectAll('.value')
      .data(bars)
      .enter()
      .append('text')
      .attr('x', (d) => (d.lift >= 0 ? x(d.lift) + 4 : x(d.lift) - 4))
      .attr('y', (d) => y(d.label)! + y.bandwidth() / 2)
      .attr('text-anchor', (d) => (d.lift >= 0 ? 'start' : 'end'))
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('fill', (d) => (d.lift >= 0 ? '#059669' : '#dc2626'))
      .text((d) => (d.lift >= 0 ? `+${d.lift}` : `${d.lift}`));

  }, [bars]);

  if (bars.length === 0) {
    return (
      <Card>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Factor Correlations</h3>
        <p className="text-xs text-gray-400 text-center py-4">
          Need more entries to show correlations. Keep journaling!
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Factor Correlations</h3>
      <p className="text-[10px] text-gray-400 mb-3">
        Average score lift/drop when each factor is present
      </p>
      <svg ref={chartRef} className="w-full" />
    </Card>
  );
}
