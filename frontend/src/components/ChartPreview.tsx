import Plot from "react-plotly.js";

type Props = {
  figure: { data: unknown[]; layout: object } | null;
  error: string | null;
  loading: boolean;
};

export function ChartPreview({ figure, error, loading }: Props) {
  if (loading) return <div className="preview-msg">Running...</div>;
  if (error) return <div className="preview-msg error">{error}</div>;
  if (!figure) return <div className="preview-msg dim">Chart preview will appear here.</div>;
  return (
    <Plot
      data={figure.data as Plotly.Data[]}
      layout={{ ...figure.layout, autosize: true, margin: { l: 50, r: 20, t: 30, b: 50 } }}
      style={{ width: "100%", height: "100%" }}
      useResizeHandler
      config={{ displaylogo: false, responsive: true }}
    />
  );
}
