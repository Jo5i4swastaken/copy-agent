'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  type TooltipProps,
} from 'recharts';

// ---------------------------------------------------------------------------
// Channel color map matching design tokens
// ---------------------------------------------------------------------------
const CHANNEL_COLORS: Record<string, string> = {
  email: 'hsl(217, 91%, 60%)',   // --channel-email (blue)
  sms:   'hsl(280, 68%, 60%)',   // --channel-sms   (purple)
  seo:   'hsl(160, 84%, 39%)',   // --channel-seo   (green)
  ad:    'hsl(38, 92%, 50%)',    // --channel-ad    (amber)
};

const FALLBACK_COLOR = 'hsl(215, 12%, 48%)';

// ---------------------------------------------------------------------------
// Dark theme constants
// ---------------------------------------------------------------------------
const TEXT_FILL = 'hsl(210, 20%, 95%)';
const MUTED_FILL = 'hsl(215, 15%, 70%)';
const TOOLTIP_BG = 'hsl(222, 40%, 10%)';
const TOOLTIP_BORDER = 'hsl(220, 20%, 18%)';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface ChannelBreakdownProps {
  data: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

  const entry = payload[0];
  const channel = entry.payload.channel as string;
  const color = CHANNEL_COLORS[channel] ?? FALLBACK_COLOR;

  return (
    <div
      style={{
        backgroundColor: TOOLTIP_BG,
        border: `1px solid ${TOOLTIP_BORDER}`,
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '0.75rem',
      }}
    >
      <p style={{ color, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {channel}
      </p>
      <p style={{ color: TEXT_FILL, marginTop: 2 }}>
        Count: <span style={{ fontWeight: 600 }}>{entry.value}</span>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function ChannelBreakdown({ data }: ChannelBreakdownProps) {
  const chartData = useMemo(() => {
    return Object.entries(data)
      .map(([channel, count]) => ({
        channel,
        count,
        color: CHANNEL_COLORS[channel] ?? FALLBACK_COLOR,
      }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  const totalCount = useMemo(
    () => chartData.reduce((sum, d) => sum + d.count, 0),
    [chartData],
  );

  if (chartData.length === 0 || totalCount === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-card border border-border bg-surface"
        style={{ height: 200 }}
      >
        <p className="text-muted text-sm">No channel data available</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Horizontal bar chart */}
      <ResponsiveContainer width="100%" height={chartData.length * 52 + 24}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 32, bottom: 4, left: 8 }}
          barCategoryGap="28%"
        >
          <XAxis
            type="number"
            tick={{ fill: MUTED_FILL, fontSize: 11, fontWeight: 500 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="channel"
            tick={{ fill: TEXT_FILL, fontSize: 12, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(220, 15%, 12%)' }} />
          <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={32}>
            {chartData.map((entry) => (
              <Cell key={entry.channel} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary labels beneath the chart */}
      <div className="flex flex-wrap items-center gap-4 px-2">
        {chartData.map((entry) => (
          <div key={entry.channel} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span style={{ color: MUTED_FILL, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {entry.channel}
            </span>
            <span style={{ color: TEXT_FILL, fontWeight: 600 }}>{entry.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
