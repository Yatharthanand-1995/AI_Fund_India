/**
 * Skeleton Loading Component
 *
 * Provides professional skeleton loading states for various UI elements.
 * Improves perceived performance and reduces user anxiety during data loading.
 */



export type SkeletonType = 'card' | 'table' | 'chart' | 'list' | 'text';

interface SkeletonLoaderProps {
  type: SkeletonType;
  count?: number;
  className?: string;
}

export function SkeletonLoader({ type, count = 1, className = '' }: SkeletonLoaderProps) {
  const skeletons = {
    card: (
      <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-48 p-6 ${className}`}>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-4"></div>
        <div className="space-y-3">
          <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded"></div>
          <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-5/6"></div>
          <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-4/6"></div>
        </div>
        <div className="mt-6 flex gap-4">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-24"></div>
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-24"></div>
        </div>
      </div>
    ),

    table: (
      <div className={`animate-pulse space-y-4 ${className}`}>
        {/* Table Header */}
        <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded-t-lg"></div>
        {/* Table Rows */}
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded"></div>
        ))}
      </div>
    ),

    chart: (
      <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-64 p-6 ${className}`}>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/4 mb-6"></div>
        <div className="flex items-end justify-between h-40 gap-2">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="bg-gray-300 dark:bg-gray-600 rounded w-full"
              style={{ height: `${Math.random() * 100}%` }}
            ></div>
          ))}
        </div>
      </div>
    ),

    list: (
      <div className={`animate-pulse space-y-3 ${className}`}>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-12 w-12 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
            <div className="flex-1 space-y-2">
              <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-3/4"></div>
              <div className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    ),

    text: (
      <div className={`animate-pulse space-y-2 ${className}`}>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-full"></div>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-5/6"></div>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-4/6"></div>
      </div>
    ),
  };

  return (
    <>
      {[...Array(count)].map((_, i) => (
        <div key={i}>{skeletons[type]}</div>
      ))}
    </>
  );
}

/**
 * Specific skeleton components for common use cases
 */

export function StockCardSkeleton() {
  return <SkeletonLoader type="card" />;
}

export function TopPicksTableSkeleton() {
  return <SkeletonLoader type="table" />;
}

export function ChartSkeleton() {
  return <SkeletonLoader type="chart" />;
}

export function WatchlistSkeleton() {
  return <SkeletonLoader type="list" />;
}
