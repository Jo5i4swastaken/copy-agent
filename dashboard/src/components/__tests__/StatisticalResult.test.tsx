import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatisticalResult } from "../ab-test/StatisticalResult";

describe("StatisticalResult", () => {
  it("renders p-value formatted to 4 decimals", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={[0.04, 0.2]}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("0.0030")).toBeInTheDocument();
  });

  it("shows 'Statistically significant' for p <= 0.05", () => {
    render(
      <StatisticalResult
        pValue={0.02}
        effectSize={0.1}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("Statistically significant")).toBeInTheDocument();
  });

  it("shows 'Marginally significant' for 0.05 < p <= 0.1", () => {
    render(
      <StatisticalResult
        pValue={0.08}
        effectSize={0.05}
        confidenceInterval={null}
        verdict="continue"
        winner={null}
      />,
    );

    expect(screen.getByText("Marginally significant")).toBeInTheDocument();
  });

  it("shows 'Not significant' for p > 0.1", () => {
    render(
      <StatisticalResult
        pValue={0.45}
        effectSize={0.01}
        confidenceInterval={null}
        verdict="inconclusive"
        winner={null}
      />,
    );

    expect(screen.getByText("Not significant")).toBeInTheDocument();
  });

  it("renders effect size with label", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("0.120")).toBeInTheDocument();
    expect(screen.getByText("Negligible")).toBeInTheDocument();
  });

  it("renders large effect size label", () => {
    render(
      <StatisticalResult
        pValue={0.001}
        effectSize={1.2}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("Large")).toBeInTheDocument();
  });

  it("renders confidence interval", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={[0.04, 0.2]}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("[0.040, 0.200]")).toBeInTheDocument();
    expect(screen.getByText("Entire CI above zero")).toBeInTheDocument();
  });

  it("notes when CI includes zero", () => {
    render(
      <StatisticalResult
        pValue={0.08}
        effectSize={0.05}
        confidenceInterval={[-0.01, 0.11]}
        verdict="continue"
        winner={null}
      />,
    );

    expect(screen.getByText("CI includes zero")).toBeInTheDocument();
  });

  it("renders '--' when values are null", () => {
    render(
      <StatisticalResult
        pValue={null}
        effectSize={null}
        confidenceInterval={null}
        verdict="insufficient"
        winner={null}
      />,
    );

    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("renders verdict badge", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("Treatment Wins")).toBeInTheDocument();
  });

  it("renders inconclusive badge", () => {
    render(
      <StatisticalResult
        pValue={0.45}
        effectSize={0.01}
        confidenceInterval={null}
        verdict="inconclusive"
        winner={null}
      />,
    );

    expect(screen.getByText("Inconclusive")).toBeInTheDocument();
  });

  it("renders winner name", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
      />,
    );

    expect(screen.getByText("treatment")).toBeInTheDocument();
  });

  it("renders reason when provided", () => {
    render(
      <StatisticalResult
        pValue={0.003}
        effectSize={0.12}
        confidenceInterval={null}
        verdict="treatment_wins"
        winner="treatment"
        reason="Treatment had significantly higher open rates"
      />,
    );

    expect(
      screen.getByText("Treatment had significantly higher open rates"),
    ).toBeInTheDocument();
  });
});
