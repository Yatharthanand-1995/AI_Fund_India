import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Card from '@/components/ui/Card';
import { Info } from 'lucide-react';

interface WatchlistItem {
  symbol: string;
  latest_score?: number;
  latest_recommendation?: string;
  added_at: string;
  notes?: string;
}

interface PortfolioScoreHistoryProps {
  watchlist: WatchlistItem[];
}

export default function PortfolioScoreHistory({}: PortfolioScoreHistoryProps) {
  // For now, we'll create a placeholder since we don't have historical data yet
  // In a real implementation, this would fetch historical score data from the API

  const hasData = false; // Set to true when historical data is available

  if (!hasData) {
    return (
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Portfolio Score History
          </h2>
          <div className="text-center py-12 text-gray-500">
            <Info className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p className="mb-2">Score history tracking coming soon</p>
            <p className="text-sm text-gray-400">
              Historical portfolio performance data will be displayed here once available
            </p>
          </div>
        </div>
      </Card>
    );
  }

  // Example data structure for when historical data is available
  const exampleData = [
    { date: '2024-01', avgScore: 75, stockCount: 8 },
    { date: '2024-02', avgScore: 78, stockCount: 10 },
    { date: '2024-03', avgScore: 82, stockCount: 10 },
  ];

  return (
    <Card>
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Portfolio Score History
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={exampleData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              domain={[0, 100]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line
              type="monotone"
              dataKey="avgScore"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
              name="Average Score"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
