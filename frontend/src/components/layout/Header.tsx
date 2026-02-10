import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  TrendingUp,
  BarChart3,
  Info,
  Activity,
  PieChart,
  Star,
  GitCompare,
  FlaskConical,
  Settings,
  Filter,
  Lightbulb,
  Menu,
  X
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { cn } from '@/lib/utils';

export default function Header() {
  const location = useLocation();
  const marketRegime = useStore((state) => state.marketRegime);
  const watchlistCount = useStore((state) => state.watchlist.length);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/ideas', label: 'Ideas', icon: TrendingUp },
    { path: '/suggestions', label: 'Suggestions', icon: Lightbulb },
    { path: '/screener', label: 'Screener', icon: Filter },
    { path: '/sectors', label: 'Sectors', icon: PieChart },
    { path: '/backtest', label: 'Backtest', icon: FlaskConical },
    { path: '/watchlist', label: 'Watchlist', icon: Star, badge: watchlistCount },
    { path: '/compare', label: 'Compare', icon: GitCompare },
    { path: '/analytics', label: 'Analytics', icon: Activity },
    { path: '/system', label: 'System', icon: Settings },
    { path: '/about', label: 'About', icon: Info },
  ];

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm relative">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2 flex-shrink-0">
            <TrendingUp className="h-8 w-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                AI Hedge Fund
              </h1>
              <p className="text-xs text-gray-500">Indian Stock Analysis</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center space-x-1 overflow-x-auto" aria-label="Main navigation">
            {navItems.map(({ path, label, icon: Icon, badge }) => (
              <Link
                key={path}
                to={path}
                aria-label={`${label}${badge !== undefined && badge > 0 ? ` (${badge} items)` : ''}`}
                aria-current={location.pathname === path ? 'page' : undefined}
                className={cn(
                  'flex items-center space-x-1 px-2 py-2 rounded-md text-sm font-medium transition-colors relative flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1',
                  location.pathname === path
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
                {badge !== undefined && badge > 0 && (
                  <span
                    className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center"
                    aria-label={`${badge} items`}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>

          {/* Right section: Market Regime + Mobile Menu Button */}
          <div className="flex items-center gap-3">
            {/* Market Regime Badge */}
            {marketRegime && (
              <div className="hidden sm:flex items-center space-x-2">
                <div className="text-right">
                  <div className="text-xs text-gray-500">Market</div>
                  <div className="text-sm font-semibold text-gray-900">
                    {marketRegime.trend}
                  </div>
                </div>
                <div className={cn(
                  'px-3 py-1 rounded-full text-xs font-medium border',
                  marketRegime.trend === 'BULL' && 'bg-green-100 text-green-700 border-green-300',
                  marketRegime.trend === 'BEAR' && 'bg-red-100 text-red-700 border-red-300',
                  marketRegime.trend === 'SIDEWAYS' && 'bg-gray-100 text-gray-700 border-gray-300'
                )}>
                  {marketRegime.volatility} VOL
                </div>
              </div>
            )}

            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-16 left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50">
          <nav className="flex flex-col py-2" aria-label="Mobile navigation">
            {navItems.map(({ path, label, icon: Icon, badge }) => (
              <Link
                key={path}
                to={path}
                aria-current={location.pathname === path ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors border-b border-gray-100 last:border-0',
                  location.pathname === path
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-50'
                )}
                onClick={() => setMobileMenuOpen(false)}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <span>{label}</span>
                {badge !== undefined && badge > 0 && (
                  <span className="ml-auto bg-blue-600 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
