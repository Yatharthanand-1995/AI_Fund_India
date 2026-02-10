import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface AgentPerformance {
  agent_name: string;
  correlation_with_returns: number;
  avg_score: number;
  current_weight: number;
  optimal_weight: number;
  weight_change: number;
  predictive_power: string;
}

interface AgentAttributionChartProps {
  data: AgentPerformance[];
}

export default function AgentAttributionChart({ data }: AgentAttributionChartProps) {
  // Transform and sort data by correlation
  const chartData = [...data]
    .sort((a, b) => Math.abs(b.correlation_with_returns) - Math.abs(a.correlation_with_returns))
    .map(d => ({
      name: d.agent_name.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      correlation: (d.correlation_with_returns * 100).toFixed(1),
      power: d.predictive_power
    }));

  const getColor = (power: string) => {
    switch (power) {
      case 'Strong': return '#10b981';
      case 'Moderate': return '#f59e0b';
      case 'Weak': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            type="number"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Correlation with Returns (%)', position: 'insideBottom', offset: -5, style: { fontSize: '12px' } }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            width={150}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '12px'
            }}
            formatter={(value: any) => [`${parseFloat(value).toFixed(1)}%`, 'Correlation']}
          />
          <Bar dataKey="correlation" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.power)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="text-gray-700">Strong (|r| &gt; 0.4)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <span className="text-gray-700">Moderate (|r| &gt; 0.2)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span className="text-gray-700">Weak (|r| ≤ 0.2)</span>
        </div>
      </div>

      <p className="text-xs text-gray-500 text-center mt-2">
        Positive correlation means higher agent scores predicted better forward returns
      </p>
    </div>
  );
}
