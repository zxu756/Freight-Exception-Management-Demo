import { useNavigate } from 'react-router-dom';
import type { DemoCase } from '../types';

interface CaseCardProps {
  caseData: DemoCase;
}

const CaseCard = ({ caseData }: CaseCardProps) => {
  const navigate = useNavigate();

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'low':
        return '🟢';
      case 'medium':
        return '🟡';
      case 'high':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; label: string }> = {
      resolved: { color: 'bg-green-500', label: 'Resolved' },
      pending_approval: { color: 'bg-yellow-500', label: 'Pending Approval' },
      escalated: { color: 'bg-red-500', label: 'Escalated' },
      detected: { color: 'bg-blue-500', label: 'Detected' },
      diagnosed: { color: 'bg-purple-500', label: 'Diagnosed' },
    };

    const config = statusConfig[status] || { color: 'bg-gray-500', label: status };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${config.color}`}>
        {config.label}
      </span>
    );
  };

  const handleClick = () => {
    navigate(`/case/${caseData.case_number}`);
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-white rounded-lg shadow-md border-2 hover:shadow-lg transition-shadow cursor-pointer ${getRiskColor(caseData.risk_level)} border-opacity-30`}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center">
            <span className="text-2xl mr-2">{getRiskIcon(caseData.risk_level)}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Case {caseData.case_number}: {caseData.risk_level.charAt(0).toUpperCase() + caseData.risk_level.slice(1)} Risk
              </h3>
              <p className="text-sm text-gray-600">{caseData.shipment_id}</p>
            </div>
          </div>
          {getStatusBadge(caseData.status)}
        </div>

        {/* Customer Info */}
        <div className="mb-4">
          <p className="text-sm text-gray-600">Customer</p>
          <p className="font-medium text-gray-900">{caseData.customer}</p>
        </div>

        {/* Exception Info */}
        <div className="mb-4">
          <p className="text-sm text-gray-600">Exception Type</p>
          <p className="font-medium text-gray-900 capitalize">
            {caseData.exception_type.replace('_', ' ')}
          </p>
        </div>

        {/* Cargo Value */}
        <div className="mb-4">
          <p className="text-sm text-gray-600">Cargo Value</p>
          <p className="font-medium text-gray-900">
            ${caseData.cargo_value.toLocaleString()}
          </p>
        </div>

        {/* Severity Badge */}
        <div className="mb-4">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${
            caseData.severity === 'critical' ? 'bg-red-100 text-red-800' :
            caseData.severity === 'high' ? 'bg-orange-100 text-orange-800' :
            caseData.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-green-100 text-green-800'
          }`}>
            Severity: {caseData.severity}
          </span>
        </div>

        {/* Processing Info */}
        {caseData.resolution_time_minutes ? (
          <div className="pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">Resolution Time</p>
            <p className="font-medium text-green-600">
              {caseData.resolution_time_minutes} minutes
            </p>
          </div>
        ) : caseData.assigned_to ? (
          <div className="pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">Assigned To</p>
            <p className="font-medium text-blue-600">{caseData.assigned_to}</p>
          </div>
        ) : null}

        {/* Approval Badge */}
        {caseData.requires_approval && (
          <div className="mt-4 flex items-center text-sm text-amber-600">
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Requires Human Approval
          </div>
        )}

        {/* View Details Button */}
        <button className="mt-4 w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded transition-colors">
          View Details →
        </button>
      </div>
    </div>
  );
};

export default CaseCard;
