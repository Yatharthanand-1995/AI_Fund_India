import { Brain, TrendingUp, BarChart3, Shield, Users, MessageSquare, Activity } from 'lucide-react';

export default function About() {
  const agents = [
    {
      name: 'Fundamentals Agent',
      weight: '36%',
      icon: TrendingUp,
      description: 'Analyzes ROE, P/E, P/B ratios, growth metrics, and debt levels. Adjusted for Indian market benchmarks.',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      name: 'Momentum Agent',
      weight: '27%',
      icon: Activity,
      description: 'Technical analysis with RSI, MACD, moving averages, and relative strength vs NIFTY 50.',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      name: 'Quality Agent',
      weight: '18%',
      icon: Shield,
      description: 'Evaluates volatility, drawdowns, and consistency. Focuses on stable, resilient businesses.',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      name: 'Sentiment Agent',
      weight: '9%',
      icon: MessageSquare,
      description: 'Tracks analyst recommendations, target prices, and coverage. Measures market expectations.',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      name: 'Institutional Flow Agent',
      weight: '10%',
      icon: Users,
      description: 'Monitors institutional activity through OBV, MFI, CMF, and volume patterns. Follows smart money.',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
    },
  ];

  const features = [
    {
      title: 'Adaptive Weights',
      description: 'Agent weights automatically adjust based on market regime (Bull/Bear/Sideways × High/Normal/Low volatility).',
    },
    {
      title: 'Market Regime Detection',
      description: 'Analyzes NIFTY 50 to determine current market conditions and adapts strategy accordingly.',
    },
    {
      title: 'LLM Narratives',
      description: 'AI-generated investment thesis using Gemini/GPT-4/Claude with key strengths, risks, and summary.',
    },
    {
      title: 'Indian Market Focus',
      description: 'Benchmarks and thresholds specifically tuned for Indian stocks (NSE/BSE).',
    },
    {
      title: 'Hybrid Data Sources',
      description: 'NSEpy primary with Yahoo Finance fallback for maximum reliability.',
    },
    {
      title: 'Real-time Analysis',
      description: 'On-demand analysis with intelligent caching for performance.',
    },
  ];

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="text-center space-y-4">
        <Brain className="h-16 w-16 text-primary-600 mx-auto" />
        <h1 className="text-4xl font-bold text-gray-900">
          AI Hedge Fund
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          AI-powered stock analysis system for Indian markets using 5 specialized agents
          with adaptive weights and LLM-generated narratives
        </p>
      </div>

      {/* How It Works */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">How It Works</h2>
        <div className="space-y-4 text-gray-600">
          <p>
            The AI Hedge Fund system analyzes stocks using a multi-agent approach. Each agent
            specializes in a different aspect of analysis:
          </p>
          <ol className="list-decimal list-inside space-y-2 ml-4">
            <li>Data is fetched from NSEpy (primary) or Yahoo Finance (fallback)</li>
            <li>Market regime is detected based on NIFTY 50 analysis</li>
            <li>Agent weights are adjusted based on current market conditions</li>
            <li>All 5 agents analyze the stock independently</li>
            <li>Scores are combined using weighted average</li>
            <li>Recommendation is generated (STRONG BUY to SELL)</li>
            <li>LLM creates investment narrative with thesis, strengths, and risks</li>
          </ol>
        </div>
      </div>

      {/* Agents */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">The 5 AI Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className="bg-white rounded-lg shadow-md border border-gray-200 p-6 hover:shadow-lg transition-shadow"
            >
              <div className={`${agent.bgColor} rounded-full w-12 h-12 flex items-center justify-center mb-4`}>
                <agent.icon className={`h-6 w-6 ${agent.color}`} />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {agent.name}
              </h3>
              <div className="text-sm font-medium text-primary-600 mb-3">
                Weight: {agent.weight}
              </div>
              <p className="text-sm text-gray-600">
                {agent.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="bg-white rounded-lg shadow-md border border-gray-200 p-6"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-600">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Recommendation Scale</h2>
        <div className="space-y-3">
          {[
            { label: 'STRONG BUY', range: '80-100', color: 'bg-green-100 text-green-700 border-green-300' },
            { label: 'BUY', range: '60-79', color: 'bg-green-50 text-green-600 border-green-200' },
            { label: 'WEAK BUY', range: '52-59', color: 'bg-blue-50 text-blue-600 border-blue-200' },
            { label: 'HOLD', range: '48-51', color: 'bg-gray-50 text-gray-600 border-gray-200' },
            { label: 'WEAK SELL', range: '42-47', color: 'bg-orange-50 text-orange-600 border-orange-200' },
            { label: 'SELL', range: '0-41', color: 'bg-red-50 text-red-600 border-red-200' },
          ].map((rec) => (
            <div key={rec.label} className="flex items-center justify-between">
              <div className={`px-4 py-2 rounded-lg border font-medium ${rec.color}`}>
                {rec.label}
              </div>
              <div className="text-sm text-gray-600">
                Score: {rec.range}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tech Stack */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-100 p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Technology Stack</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="font-semibold text-gray-900 mb-2">Backend</div>
            <ul className="space-y-1 text-gray-600">
              <li>• Python 3.11+</li>
              <li>• FastAPI</li>
              <li>• Pandas/NumPy</li>
              <li>• TA-Lib</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-gray-900 mb-2">Data</div>
            <ul className="space-y-1 text-gray-600">
              <li>• NSEpy</li>
              <li>• yfinance</li>
              <li>• Circuit Breaker</li>
              <li>• Multi-layer Cache</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-gray-900 mb-2">AI/LLM</div>
            <ul className="space-y-1 text-gray-600">
              <li>• Gemini 1.5</li>
              <li>• GPT-4</li>
              <li>• Claude 3</li>
              <li>• Rule-based Fallback</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-gray-900 mb-2">Frontend</div>
            <ul className="space-y-1 text-gray-600">
              <li>• React 18</li>
              <li>• TypeScript</li>
              <li>• Tailwind CSS</li>
              <li>• Vite</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="font-semibold text-yellow-900 mb-2">Disclaimer</h3>
        <p className="text-sm text-yellow-800">
          This tool is for informational and educational purposes only. It does not constitute
          financial advice. Always do your own research and consult with a qualified financial
          advisor before making investment decisions. Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}
