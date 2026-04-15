'use client';

import { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
} from 'recharts';
import type { PlaybookEntry } from '@/lib/types';

// ---------------------------------------------------------------------------
// Confidence level definitions matching design tokens
// ---------------------------------------------------------------------------
const CONFIDENCE_LEVELS = [
  { key: 'low', label: 'Low', threshold: (c: number) => c < 0.4, color: 'hsl(20, 90%, 55%)' },
  { key: 'medium', label: 'Medium', threshold: (c: number) => c >= 0.4 && c <= 0.7, color: 'hsl(45, 90%, 50%)' },
  { key: 'high', label: 'High', threshold: (c: number) => c > 0.7, color: 'hsl(160, 84%, 39%)' },
] as const;

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
interface ConfidenceChartProps {
  learnings: PlaybookEntry[];
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

  const entry = payload[0];
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
      <p style={{ color: entry.payload.fill, fontWeight: 600 }}>
        {entry.name}: {entry.value}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom center label rendered as SVG text
// ---------------------------------------------------------------------------
function CenterLabel({ total }: { total: number }) {
  return (
    <g>
      <text
        x="50%"
        y="46%"
        textAnchor="middle"
        dominantBaseline="central"
        fill={TEXT_FILL}
        fontSize={28}
        fontWeight={700}
      >
        {total}
      </text>
      <text
        x="50%"
        y="58%"
        textAnchor="middle"
        dominantBaseline="central"
        fill={MUTED_FILL}
        fontSize={11}
        fontWeight={500}
      >
        learnings
      </text>
    </g>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function ConfidenceChart({ learnings }: ConfidenceChartProps) {
  const { data, total } = useMemo(() => {
    const counts = CONFIDENCE_LEVELS.map((level) => ({
      name: level.label,
      value: learnings.filter((l) => level.threshold(l.confidence)).length,
      fill: level.color,
      key: level.key,
    }));
    return {
      data: counts.filter((d) => d.value > 0),
      total: learnings.length,
    };
  }, [learnings]);

  if (learnings.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-card border border-border bg-surface"
        style={{ height: 300 }}
      >
        <p className="text-muted text-sm">No playbook learnings yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="80%"
            paddingAngle={3}
            dataKey="value"
            stroke="none"
            animationDuration={600}
            animationEasing="ease-out"
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <CenterLabel total={total} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center gap-6">
        {CONFIDENCE_LEVELS.map((level) => {
          const count = learnings.filter((l) => level.threshold(l.confidence)).length;
          return (
            <div key={level.key} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: level.color }}
              />
              <span style={{ color: MUTED_FILL }}>{level.label}</span>
              <span style={{ color: TEXT_FILL, fontWeight: 600 }}>{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
