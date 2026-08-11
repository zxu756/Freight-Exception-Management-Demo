import type { ExceptionStats } from '../types';

interface MetricsPanelProps {
  stats: ExceptionStats;
}

const MetricsPanel = ({ stats }: MetricsPanelProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* Total Exceptions */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Total Exceptions</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {stats.total_exceptions}
            </p>
          </div>
          <div className="bg-blue-100 rounded-full p-3">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <div className="mt-4 flex items-center text-sm">
          <span className="text-green-600 font-medium">{stats.by_status.resolved} resolved</span>
          <span className="text-gray-400 mx-2">•</span>
          <span className="text-yellow-600 font-medium">{stats.by_status.pending_approval} pending</span>
        </div>
      </div>

      {/* Average Resolution Time */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Avg Resolution Time</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {stats.metrics.avg_resolution_time_minutes}
              <span className="text-lg text-gray-600 ml-1">min</span>
            </p>
          </div>
          <div className="bg-green-100 rounded-full p-3">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <div className="mt-4 text-sm text-gray-600">
          ⚡ 73-87% faster than manual
        </div>
      </div>

      {/* Auto-Resolved */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Auto-Resolved</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {stats.metrics.auto_resolved_percentage}%
            </p>
          </div>
          <div className="bg-purple-100 rounded-full p-3">
            <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <div className="mt-4 text-sm text-gray-600">
          {stats.metrics.auto_resolved_count} of {stats.total_exceptions} cases
        </div>
      </div>

      {/* Risk Distribution */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-medium text-gray-600">Risk Distribution</p>
          </div>
          <div className="bg-orange-100 rounded-full p-3">
            <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 flex items-center">
              <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
              Low
            </span>
            <span className="font-medium text-gray-900">{stats.by_risk_level.low}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 flex items-center">
              <span className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></span>
              Medium
            </span>
            <span className="font-medium text-gray-900">{stats.by_risk_level.medium}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 flex items-center">
              <span className="w-3 h-3 bg-red-500 rounded-full mr-2"></span>
              High
            </span>
            <span className="font-medium text-gray-900">{stats.by_risk_level.high}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsPanel;
