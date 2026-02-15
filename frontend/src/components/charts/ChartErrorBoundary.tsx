/**
 * Chart Error Boundary
 *
 * Catches rendering errors in Recharts components and displays a compact
 * fallback instead of crashing the parent page.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  title?: string;
}

interface State {
  hasError: boolean;
}

class ChartErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Chart rendering error${this.props.title ? ` in ${this.props.title}` : ''}:`, error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] bg-gray-50 rounded-lg border border-gray-200 gap-3 p-6">
          <AlertTriangle className="w-8 h-8 text-amber-500" />
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">
              {this.props.title ? `${this.props.title} failed to render` : 'Chart failed to render'}
            </p>
            <p className="text-xs text-gray-500 mt-1">A chart rendering error occurred</p>
          </div>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChartErrorBoundary;
