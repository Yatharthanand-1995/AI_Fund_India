import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface EquityCurveChartProps {
  data: Array<{
    date: string;
    value: number;
    benchmark_value: number;
  }>;
}

export default function EquityCurveChart({ data }: EquityCurveChartProps) {
  // Transform data for Recharts
  const chartData = data.map(d => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Strategy: d.value.toFixed(2),
    Benchmark: d.benchmark_value.toFixed(2)
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
        />
        <YAxis
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          label={{ value: 'Cumulative Return (%)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px'
          }}
          formatter={(value: any) => [`${parseFloat(value).toFixed(2)}%`, '']}
        />
        <Legend
          wrapperStyle={{ fontSize: '12px' }}
          iconType="line"
        />
        <Line
          type="monotone"
          dataKey="Strategy"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          name="AI Strategy"
        />
        <Line
          type="monotone"
          dataKey="Benchmark"
          stroke="#9ca3af"
          strokeWidth={2}
          dot={false}
          strokeDasharray="5 5"
          name="NIFTY 50"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
