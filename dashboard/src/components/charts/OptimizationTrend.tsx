'use client';

import { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  type TooltipProps,
} from 'recharts';
import type { PlaybookEntry } from '@/lib/types';

// ---------------------------------------------------------------------------
// Dark theme constants
// ---------------------------------------------------------------------------
const GRID_STROKE = 'hsl(220, 15%, 20%)';
const TEXT_FILL = 'hsl(210, 20%, 95%)';
const MUTED_FILL = 'hsl(215, 15%, 70%)';
const TOOLTIP_BG = 'hsl(222, 40%, 10%)';
const TOOLTIP_BORDER = 'hsl(220, 20%, 18%)';

// Line colors
const ACCENT_COLOR = 'hsl(217, 91%, 60%)';   // Primary accent for cumulative learnings
const SECONDARY_COLOR = 'hsl(160, 84%, 39%)'; // Green for average confidence

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface OptimizationTrendProps {
  learnings: PlaybookEntry[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert YYYY-MM-DD to YYYY-MM for monthly bucketing. */
function toMonth(dateStr: string): string {
  return dateStr.slice(0, 7);
}

/** Format YYYY-MM into a readable label like "Jan 2025". */
function formatMonth(ym: string): string {
  const [year, month] = ym.split('-');
  const monthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  const idx = parseInt(month, 10) - 1;
  return `${monthNames[idx] ?? month} ${year}`;
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      style={{
        backgroundColor: TOOLTIP_BG,
        border: `1px solid ${TOOLTIP_BORDER}`,
        borderRadius: '8px',
        padding: '10px 14px',
        fontSize: '0.75rem',
      }}
    >
      <p style={{ color: TEXT_FILL, fontWeight: 600, marginBottom: 6 }}>{label}</p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey as string}
          style={{
            color: entry.color,
            margin: '3px 0',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <span>{entry.name}</span>
          <span style={{ fontWeight: 600 }}>
            {entry.dataKey === 'avgConfidence'
              ? Number(entry.value).toFixed(2)
              : entry.value}
          </span>
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function OptimizationTrend({ learnings }: OptimizationTrendProps) {
  const chartData = useMemo(() => {
    if (learnings.length === 0) return [];

    // Group learnings by first_observed month
    const byMonth = new Map<string, PlaybookEntry[]>();
    for (const l of learnings) {
      const month = toMonth(l.first_observed);
      const existing = byMonth.get(month);
      if (existing) {
        existing.push(l);
      } else {
        byMonth.set(month, [l]);
      }
    }

    // Sort months chronologically
    const sortedMonths = Array.from(byMonth.keys()).sort();

    // Build cumulative data
    let cumulative = 0;
    let totalConfidence = 0;

    return sortedMonths.map((month) => {
      const entries = byMonth.get(month)!;
      cumulative += entries.length;
      totalConfidence += entries.reduce((sum, e) => sum + e.confidence, 0);
      const avgConfidence = totalConfidence / cumulative;

      return {
        month: formatMonth(month),
        cumulativeLearnings: cumulative,
        avgConfidence: parseFloat(avgConfidence.toFixed(3)),
        newLearnings: entries.length,
      };
    });
  }, [learnings]);

  // Not enough data points guard
  if (chartData.length < 2) {
    return (
      <div
        className="flex items-center justify-center rounded-card border border-border bg-surface"
        style={{ height: 300 }}
      >
        <div className="text-center">
          <p className="text-muted text-sm">Not enough data yet</p>
          <p className="text-muted/60 mt-1 text-xs">
            At least 2 months of learnings required to show trends
          </p>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart
        data={chartData}
        margin={{ top: 16, right: 24, bottom: 8, left: 8 }}
      >
        <defs>
          <linearGradient id="areaLearnings" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACCENT_COLOR} stopOpacity={0.2} />
            <stop offset="100%" stopColor={ACCENT_COLOR} stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="areaConfidence" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={SECONDARY_COLOR} stopOpacity={0.15} />
            <stop offset="100%" stopColor={SECONDARY_COLOR} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid
          strokeDasharray="3 3"
          stroke={GRID_STROKE}
          strokeOpacity={0.5}
          vertical={false}
        />

        {/* X-axis: months */}
        <XAxis
          dataKey="month"
          tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
          axisLine={{ stroke: GRID_STROKE }}
          tickLine={false}
        />

        {/* Left Y-axis: cumulative learnings */}
        <YAxis
          yAxisId="left"
          tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          width={40}
          allowDecimals={false}
        />

        {/* Right Y-axis: average confidence (0-1) */}
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[0, 1]}
          tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={(v: number) => v.toFixed(1)}
        />

        <Tooltip content={<CustomTooltip />} />

        <Legend
          wrapperStyle={{ fontSize: '0.75rem', color: TEXT_FILL, paddingTop: 8 }}
          iconType="circle"
          iconSize={8}
        />

        {/* Area fills */}
        <Area
          yAxisId="left"
          type="monotone"
          dataKey="cumulativeLearnings"
          fill="url(#areaLearnings)"
          stroke="none"
          name="Cumulative Learnings"
        />
        <Area
          yAxisId="right"
          type="monotone"
          dataKey="avgConfidence"
          fill="url(#areaConfidence)"
          stroke="none"
          name="Avg Confidence"
        />

        {/* Lines on top */}
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="cumulativeLearnings"
          stroke={ACCENT_COLOR}
          strokeWidth={2.5}
          dot={{ fill: ACCENT_COLOR, r: 4, strokeWidth: 0 }}
          activeDot={{ r: 6, fill: ACCENT_COLOR, stroke: TEXT_FILL, strokeWidth: 2 }}
          name="Cumulative Learnings"
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="avgConfidence"
          stroke={SECONDARY_COLOR}
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={{ fill: SECONDARY_COLOR, r: 3, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: SECONDARY_COLOR, stroke: TEXT_FILL, strokeWidth: 2 }}
          name="Avg Confidence"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
