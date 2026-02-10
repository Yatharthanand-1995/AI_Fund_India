import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface DrawdownChartProps {
  data: Array<{
    date: string;
    value: number;
    benchmark_value: number;
  }>;
}

export default function DrawdownChart({ data }: DrawdownChartProps) {
  // Calculate drawdown from equity curve
  const calculateDrawdown = (values: number[]) => {
    const drawdowns: number[] = [];
    let peak = values[0];

    for (const value of values) {
      if (value > peak) {
        peak = value;
      }
      const drawdown = ((value - peak) / peak) * 100;
      drawdowns.push(drawdown);
    }

    return drawdowns;
  };

  const strategyValues = data.map(d => d.value);
  const benchmarkValues = data.map(d => d.benchmark_value);

  const strategyDrawdowns = calculateDrawdown(strategyValues);
  const benchmarkDrawdowns = calculateDrawdown(benchmarkValues);

  const chartData = data.map((d, idx) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Strategy: strategyDrawdowns[idx].toFixed(2),
    Benchmark: benchmarkDrawdowns[idx].toFixed(2)
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
        />
        <YAxis
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          label={{ value: 'Drawdown (%)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
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
        <Area
          type="monotone"
          dataKey="Strategy"
          stroke="#ef4444"
          fill="#fecaca"
          fillOpacity={0.6}
          name="AI Strategy"
        />
        <Area
          type="monotone"
          dataKey="Benchmark"
          stroke="#9ca3af"
          fill="#e5e7eb"
          fillOpacity={0.4}
          name="NIFTY 50"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
