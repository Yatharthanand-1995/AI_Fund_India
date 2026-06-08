import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  TrendingUp,
  BarChart3,
  Activity,
  Star,
  FlaskConical,
  Zap,
  Menu,
  X,
  Bell,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { cn } from '@/lib/utils';
import { useAlerts } from '@/hooks/useAlerts';
import { useWatchlist } from '@/hooks/useWatchlist';

export default function Header() {
  const location = useLocation();
  const marketRegime = useStore((state) => state.marketRegime);
  // Read alerts from the singleton store (polled once in App.tsx)
  const storeAlerts = useStore((state) => state.alerts);
  const unreadCount = useStore((state) => state.unreadAlertCount);
  const { watchlist } = useWatchlist();
  const watchlistCount = watchlist.length;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const alertPanelRef = useRef<HTMLDivElement>(null);

  // markRead/markAllRead still needed — use the hook only for those actions (no polling)
  const { alerts: _unused, markRead, markAllRead } = useAlerts(0);
  const alerts = storeAlerts;

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (alertPanelRef.current && !alertPanelRef.current.contains(e.target as Node)) {
        setAlertsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/research', label: 'Research', icon: TrendingUp },
    { path: '/portfolio', label: 'Portfolio', icon: Zap },
    { path: '/watchlist', label: 'Watchlist', icon: Star, badge: watchlistCount },
    { path: '/analytics', label: 'Analytics', icon: Activity },
    { path: '/backtest', label: 'Backtest', icon: FlaskConical },
  ];

  const severityColor = (severity: string) => {
    if (severity === 'critical') return 'text-red-600';
    if (severity === 'warning') return 'text-yellow-600';
    return 'text-blue-600';
  };

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

          {/* Right section: Market Regime + Alerts + Mobile Menu Button */}
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

            {/* Alert Bell */}
            <div className="relative" ref={alertPanelRef}>
              <button
                onClick={() => setAlertsOpen(prev => !prev)}
                aria-label={`Alerts${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
                className="relative p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center font-bold">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Alerts dropdown */}
              {alertsOpen && (
                <div className="absolute right-0 top-10 w-80 bg-white border border-gray-200 rounded-lg shadow-xl z-50 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                    <span className="text-sm font-semibold text-gray-900">
                      Alerts {unreadCount > 0 && <span className="text-red-500">({unreadCount} new)</span>}
                    </span>
                    {unreadCount > 0 && (
                      <button
                        onClick={() => markAllRead()}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
                    {alerts.length === 0 ? (
                      <p className="px-4 py-6 text-sm text-gray-500 text-center">No alerts</p>
                    ) : (
                      alerts.map(alert => (
                        <div
                          key={alert.id}
                          className={cn(
                            'px-4 py-3 flex items-start gap-2 cursor-pointer hover:bg-gray-50',
                            !alert.is_read && 'bg-blue-50'
                          )}
                          onClick={() => !alert.is_read && markRead(alert.id)}
                        >
                          <Bell className={cn('h-4 w-4 mt-0.5 flex-shrink-0', severityColor(alert.severity))} />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-gray-800">{alert.symbol}</p>
                            <p className="text-xs text-gray-600 leading-snug">{alert.message}</p>
                            <p className="text-xs text-gray-400 mt-0.5">
                              {new Date(alert.triggered_at).toLocaleString('en-IN', {
                                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                              })}
                            </p>
                          </div>
                          {!alert.is_read && (
                            <span className="h-2 w-2 rounded-full bg-blue-500 mt-1 flex-shrink-0" />
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

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
