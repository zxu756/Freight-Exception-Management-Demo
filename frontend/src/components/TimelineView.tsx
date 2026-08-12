import { format } from 'date-fns';
import type { TimelineEvent } from '../types';

interface TimelineViewProps {
  timeline: TimelineEvent[];
}

const TimelineView = ({ timeline }: TimelineViewProps) => {
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'exception_detected':
        return '🚨';
      case 'ai_diagnosis':
        return '🤖';
      case 'decision_generated':
        return '💡';
      case 'human_approval':
        return '✅';
      case 'notification_sent':
        return '📧';
      case 'resolved':
        return '🎉';
      default:
        return '📍';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'current':
        return 'bg-blue-500 animate-pulse';
      case 'pending':
        return 'bg-gray-300';
      case 'alert':
        return 'bg-red-500';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Event Timeline</h2>

      {timeline.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No timeline events available</p>
      ) : (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>

          {/* Timeline events */}
          <div className="space-y-6">
            {timeline.map((event, index) => (
              <div key={index} className="relative flex items-start">
                {/* Icon */}
                <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-white border-2 border-gray-300">
                  <span className={`w-3 h-3 rounded-full ${getStatusColor(event.status)}`}></span>
                </div>

                {/* Content */}
                <div className="ml-4 flex-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <span className="text-lg mr-2">{getEventIcon(event.event_type)}</span>
                      <h3 className="text-sm font-semibold text-gray-900">{event.title}</h3>
                    </div>
                    <span className="text-xs text-gray-500">
                      {format(new Date(event.timestamp), 'HH:mm:ss')}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{event.description}</p>

                  {/* Additional metadata */}
                  {event.confidence && (
                    <div className="mt-2">
                      <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                        Confidence: {Math.round(event.confidence * 100)}%
                      </span>
                    </div>
                  )}

                  {event.severity && (
                    <div className="mt-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        event.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        event.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        Severity: {event.severity}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline summary */}
      {timeline.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Events: {timeline.length}</span>
            <span className="text-gray-600">
              Duration: {format(new Date(timeline[0].timestamp), 'HH:mm')} - {format(new Date(timeline[timeline.length - 1].timestamp), 'HH:mm')}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineView;
