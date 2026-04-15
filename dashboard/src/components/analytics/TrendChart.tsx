"use client";

import React, { useMemo } from "react";

// ---------------------------------------------------------------------------
// TrendChart — Simple bar/line chart using inline SVG
// ---------------------------------------------------------------------------

interface TrendDataPoint {
  label: string;
  value: number;
}

interface TrendChartProps {
  data: TrendDataPoint[];
  title?: string;
  /** "bar" renders vertical bars, "line" renders a line with area fill. */
  variant?: "bar" | "line";
  height?: number;
  /** Color for the chart elements. Defaults to accent. */
  color?: string;
  /** Format function for tooltip values. */
  formatValue?: (value: number) => string;
}

const DEFAULT_HEIGHT = 120;

function defaultFormat(value: number): string {
  if (value < 1) return (value * 100).toFixed(1) + "%";
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  return value.toFixed(2);
}

/**
 * Renders a lightweight trend chart using inline SVG.
 * Supports bar and line chart variants without any external chart library.
 * Uses the dashboard's design tokens for colors.
 */
export function TrendChart({
  data,
  title,
  variant = "bar",
  height = DEFAULT_HEIGHT,
  color = "hsl(var(--accent))",
  formatValue = defaultFormat,
}: TrendChartProps) {
  const { maxValue, normalizedData } = useMemo(() => {
    if (data.length === 0) return { maxValue: 0, normalizedData: [] };
    const max = Math.max(...data.map((d) => d.value), 0.001);
    return {
      maxValue: max,
      normalizedData: data.map((d) => ({
        ...d,
        normalized: d.value / max,
      })),
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="rounded-card border border-border-subtle bg-surface p-5 flex flex-col items-center justify-center" style={{ minHeight: height + 60 }}>
        <p className="text-muted text-sm">No trend data available</p>
      </div>
    );
  }

  const padding = { top: 8, right: 8, bottom: 24, left: 8 };
  const chartWidth = 400;
  const chartHeight = height;
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  return (
    <div className="rounded-card border border-border-subtle bg-surface p-5">
      {title && (
        <h4 className="text-sm font-semibold text-foreground mb-3">{title}</h4>
      )}
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        className="w-full"
        style={{ height }}
        role="img"
        aria-label={title ?? "Trend chart"}
      >
        {variant === "bar" ? (
          <BarChart
            data={normalizedData}
            x={padding.left}
            y={padding.top}
            width={innerWidth}
            height={innerHeight}
            color={color}
          />
        ) : (
          <LineChart
            data={normalizedData}
            x={padding.left}
            y={padding.top}
            width={innerWidth}
            height={innerHeight}
            color={color}
          />
        )}

        {/* X-axis labels */}
        {normalizedData.map((d, i) => {
          const barWidth = innerWidth / normalizedData.length;
          const cx = padding.left + i * barWidth + barWidth / 2;
          return (
            <text
              key={i}
              x={cx}
              y={chartHeight - 4}
              textAnchor="middle"
              className="fill-muted"
              style={{ fontSize: "9px" }}
            >
              {d.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BarChart sub-component
// ---------------------------------------------------------------------------

function BarChart({
  data,
  x,
  y,
  width,
  height,
  color,
}: {
  data: { label: string; value: number; normalized: number }[];
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}) {
  const barWidth = width / data.length;
  const barPadding = Math.max(barWidth * 0.2, 2);

  return (
    <g>
      {data.map((d, i) => {
        const barX = x + i * barWidth + barPadding / 2;
        const barH = Math.max(d.normalized * height, 1);
        const barY = y + height - barH;
        const bw = barWidth - barPadding;

        return (
          <rect
            key={i}
            x={barX}
            y={barY}
            width={Math.max(bw, 1)}
            height={barH}
            rx={2}
            fill={color}
            opacity={0.8}
          >
            <title>
              {d.label}: {d.value}
            </title>
          </rect>
        );
      })}
    </g>
  );
}

// ---------------------------------------------------------------------------
// LineChart sub-component
// ---------------------------------------------------------------------------

function LineChart({
  data,
  x,
  y,
  width,
  height,
  color,
}: {
  data: { label: string; value: number; normalized: number }[];
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}) {
  if (data.length < 2) return null;

  const stepX = width / (data.length - 1);

  const points = data.map((d, i) => ({
    cx: x + i * stepX,
    cy: y + height - d.normalized * height,
  }));

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.cx} ${p.cy}`)
    .join(" ");

  const areaPath = `${linePath} L ${points[points.length - 1].cx} ${y + height} L ${points[0].cx} ${y + height} Z`;

  return (
    <g>
      {/* Area fill */}
      <path d={areaPath} fill={color} opacity={0.1} />
      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Data points */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.cx}
          cy={p.cy}
          r={3}
          fill={color}
          stroke="hsl(var(--surface))"
          strokeWidth={2}
        >
          <title>
            {data[i].label}: {data[i].value}
          </title>
        </circle>
      ))}
    </g>
  );
}
