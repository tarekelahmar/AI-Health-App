import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { LIFE_DOMAIN_KEYS, LIFE_DOMAIN_LABELS } from '../../types/LifeDomain';

interface LifeDomainRadarProps {
  current: Record<string, number>;
  comparison?: Record<string, number> | null; // e.g., 30-day-ago scores
  totalScore: number;
  size?: number;
}

const SCORE_MIN = 1;
const SCORE_MAX = 10;

function scoreColor(value: number): string {
  if (value < 4) return '#ef4444';   // red
  if (value < 7) return '#f59e0b';   // amber
  return '#10b981';                    // green
}

export function LifeDomainRadar({
  current,
  comparison = null,
  totalScore,
  size = 300,
}: LifeDomainRadarProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = 50;
    const radius = (size - margin * 2) / 2;
    const center = size / 2;
    const domains = LIFE_DOMAIN_KEYS;
    const n = domains.length;
    const angleSlice = (Math.PI * 2) / n;

    const g = svg.append('g').attr('transform', `translate(${center},${center})`);

    // Radial scale
    const rScale = d3.scaleLinear().domain([SCORE_MIN, SCORE_MAX]).range([0, radius]);

    // Draw concentric grid circles
    const levels = [2, 4, 6, 8, 10];
    levels.forEach((level) => {
      g.append('circle')
        .attr('r', rScale(level))
        .attr('fill', 'none')
        .attr('stroke', '#e5e7eb')
        .attr('stroke-width', level === 4 || level === 7 ? 1.5 : 0.5)
        .attr('stroke-dasharray', level % 2 === 0 ? 'none' : '2,2');
    });

    // Draw axis lines and labels
    domains.forEach((domain, i) => {
      const angle = angleSlice * i - Math.PI / 2;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;

      // Axis line
      g.append('line')
        .attr('x1', 0).attr('y1', 0)
        .attr('x2', x).attr('y2', y)
        .attr('stroke', '#d1d5db')
        .attr('stroke-width', 0.5);

      // Label
      const labelRadius = radius + 18;
      const lx = Math.cos(angle) * labelRadius;
      const ly = Math.sin(angle) * labelRadius;
      const score = current[domain] ?? 5;

      g.append('text')
        .attr('x', lx)
        .attr('y', ly)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', '9px')
        .attr('fill', scoreColor(score))
        .attr('font-weight', '600')
        .text(LIFE_DOMAIN_LABELS[domain] ?? domain);
    });

    // Line generator for radar polygon
    const radarLine = d3.lineRadial<number>()
      .radius((d) => rScale(d))
      .angle((_d, i) => i * angleSlice)
      .curve(d3.curveLinearClosed);

    // Draw comparison polygon (dashed, behind current)
    if (comparison) {
      const compData = domains.map((d) => comparison[d] ?? 5);
      g.append('path')
        .datum(compData)
        .attr('d', radarLine as any)
        .attr('fill', '#6366f1')
        .attr('fill-opacity', 0.05)
        .attr('stroke', '#6366f1')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,3')
        .attr('stroke-opacity', 0.5);
    }

    // Draw current polygon
    const currentData = domains.map((d) => current[d] ?? 5);
    g.append('path')
      .datum(currentData)
      .attr('d', radarLine as any)
      .attr('fill', '#6366f1')
      .attr('fill-opacity', 0.15)
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 2);

    // Draw score dots on current polygon
    domains.forEach((domain, i) => {
      const score = current[domain] ?? 5;
      const angle = angleSlice * i - Math.PI / 2;
      const x = Math.cos(angle) * rScale(score);
      const y = Math.sin(angle) * rScale(score);

      g.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 3.5)
        .attr('fill', scoreColor(score))
        .attr('stroke', 'white')
        .attr('stroke-width', 1.5);
    });

  }, [current, comparison, size]);

  return (
    <div className="flex flex-col items-center">
      <svg ref={svgRef} width={size} height={size} />
      <div className="text-center mt-1">
        <span className="text-2xl font-bold text-gray-800">{Math.round(totalScore)}</span>
        <span className="text-xs text-gray-400 ml-1">/ 100</span>
      </div>
      {comparison && (
        <div className="flex items-center gap-2 mt-1">
          <span className="w-4 border-t-2 border-dashed border-indigo-400" />
          <span className="text-[10px] text-gray-400">30 days ago</span>
        </div>
      )}
    </div>
  );
}
