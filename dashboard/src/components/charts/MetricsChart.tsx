'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  type TooltipProps,
} from 'recharts';
import type { MetricEntry } from '@/lib/types';

// ---------------------------------------------------------------------------
// Variant color palette — consistent across all metric charts
// ---------------------------------------------------------------------------
const VARIANT_COLORS = [
  'hsl(217, 91%, 60%)',  // blue (accent)
  'hsl(280, 68%, 60%)',  // purple
  'hsl(160, 84%, 39%)',  // green
  'hsl(38, 92%, 50%)',   // amber
  'hsl(0, 84%, 60%)',    // red
  'hsl(199, 89%, 48%)',  // sky
  'hsl(330, 80%, 60%)',  // pink
  'hsl(45, 90%, 50%)',   // yellow
];

// ---------------------------------------------------------------------------
// Dark theme constants
// ---------------------------------------------------------------------------
const GRID_STROKE = 'hsl(220, 15%, 20%)';
const TEXT_FILL = 'hsl(210, 20%, 95%)';
const MUTED_FILL = 'hsl(215, 15%, 70%)';
const TOOLTIP_BG = 'hsl(222, 40%, 10%)';
const TOOLTIP_BORDER = 'hsl(220, 20%, 18%)';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface MetricsChartProps {
  metrics: MetricEntry[];
  variants: string[];
  metricType?: string;
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
          key={entry.name}
          style={{
            color: entry.color,
            margin: '3px 0',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <span>{entry.name}</span>
          <span style={{ fontWeight: 600 }}>{Number(entry.value).toFixed(4)}</span>
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function MetricsChart({ metrics, variants, metricType }: MetricsChartProps) {
  // Build chart data: one bar group per metric type, one bar per variant
  const { chartData, metricTypes } = useMemo(() => {
    // Filter to the specified metric type if provided
    const filtered = metricType
      ? metrics.filter((m) => m.metric_type === metricType)
      : metrics;

    // Collect all metric types present
    const types = Array.from(new Set(filtered.map((m) => m.metric_type)));

    // For each metric type, compute the average value per variant
    const data = types.map((type) => {
      const row: Record<string, string | number> = { metric_type: type };
      for (const variant of variants) {
        const entries = filtered.filter(
          (m) => m.metric_type === type && m.variant_id === variant,
        );
        if (entries.length > 0) {
          row[variant] = entries.reduce((sum, e) => sum + e.value, 0) / entries.length;
        }
      }
      return row;
    });

    return { chartData: data, metricTypes: types };
  }, [metrics, variants, metricType]);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-card border border-border bg-surface"
        style={{ height: 300 }}
      >
        <p className="text-muted text-sm">No metric data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={chartData}
        margin={{ top: 16, right: 24, bottom: 8, left: 8 }}
        barCategoryGap="20%"
        barGap={4}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={GRID_STROKE}
          strokeOpacity={0.5}
          vertical={false}
        />
        <XAxis
          dataKey="metric_type"
          tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
          axisLine={{ stroke: GRID_STROKE }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(220, 15%, 15%)' }} />
        <Legend
          wrapperStyle={{ fontSize: '0.75rem', color: TEXT_FILL, paddingTop: 8 }}
          iconType="circle"
          iconSize={8}
        />
        {variants.map((variant, idx) => (
          <Bar
            key={variant}
            dataKey={variant}
            name={variant}
            fill={VARIANT_COLORS[idx % VARIANT_COLORS.length]}
            radius={[4, 4, 0, 0]}
            maxBarSize={48}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
