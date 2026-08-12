import { useState } from 'react';
import { format } from 'date-fns';
import { exceptionAPI } from '../services/api';
import type { Exception, Decision, Shipment } from '../types';

interface ApprovalInterfaceProps {
  exception: Exception;
  decision: Decision;
  shipment: Shipment;
  onApproval: () => void;
}

const ApprovalInterface = ({ exception, decision, shipment, onApproval }: ApprovalInterfaceProps) => {
  const [selectedOption, setSelectedOption] = useState(decision.recommended_option || 'B');
  const [notes, setNotes] = useState('');
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    try {
      setApproving(true);
      setError(null);

      await exceptionAPI.approve(
        exception.exception_id,
        selectedOption,
        notes || 'Approved',
        'Demo User'
      );

      onApproval();
    } catch (err) {
      setError('Failed to approve decision');
      console.error('Approval error:', err);
    } finally {
      setApproving(false);
    }
  };

  const getOptionBadge = (optionId: string) => {
    if (optionId === decision.recommended_option) {
      return (
        <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
          ⭐ AI Recommended
        </span>
      );
    }
    return null;
  };

  const getSLAImpactColor = (impact: string) => {
    if (impact.includes('breach')) return 'text-red-600';
    if (impact.includes('minor')) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg border-2 border-blue-200">
      {/* Header */}
      <div className="bg-blue-50 px-6 py-4 border-b border-blue-200">
        <div className="flex items-center">
          <svg className="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="text-lg font-semibold text-gray-900">Approval Required</h2>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Please review AI recommendations and approve a solution
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* AI Reasoning */}
        {decision.recommendation_reasoning && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">AI Recommendation Reasoning</h3>
            <p className="text-sm text-blue-800">{decision.recommendation_reasoning}</p>
          </div>
        )}

        {/* Options Table */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Solution Options</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Select</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Option</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">New ETA</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SLA Impact</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {decision.options.map((option) => (
                  <tr
                    key={option.option_id}
                    className={`hover:bg-gray-50 cursor-pointer ${
                      selectedOption === option.option_id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setSelectedOption(option.option_id)}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="radio"
                        checked={selectedOption === option.option_id}
                        onChange={() => setSelectedOption(option.option_id)}
                        className="w-4 h-4 text-blue-600"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center">
                        <span className="font-semibold text-gray-900">{option.option_id}</span>
                        {getOptionBadge(option.option_id)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{option.description}</td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-medium ${option.cost === 0 ? 'text-green-600' : 'text-gray-900'}`}>
                        ${option.cost.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {format(new Date(option.new_eta), 'MMM dd HH:mm')}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-medium ${getSLAImpactColor(option.sla_impact)}`}>
                        {option.sla_impact.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded ${
                        option.risk === 'low' ? 'bg-green-100 text-green-800' :
                        option.risk === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {option.risk}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Cost-Benefit Analysis */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Cost-Benefit Analysis</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Cargo Value</p>
              <p className="font-semibold text-gray-900">${shipment.cargo_value.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-600">Customer Tier</p>
              <p className="font-semibold text-gray-900 capitalize">{shipment.customer_tier}</p>
            </div>
            <div>
              <p className="text-gray-600">Selected Cost</p>
              <p className="font-semibold text-gray-900">
                ${decision.options.find(o => o.option_id === selectedOption)?.cost.toLocaleString() || 0}
                <span className="text-xs text-gray-500 ml-1">
                  ({((decision.options.find(o => o.option_id === selectedOption)?.cost || 0) / shipment.cargo_value * 100).toFixed(1)}% of value)
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Approval Notes (Optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Add any notes about your decision..."
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4 pt-4 border-t border-gray-200">
          <button
            onClick={() => setSelectedOption(decision.recommended_option || 'A')}
            className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
          >
            Reset to AI Recommendation
          </button>
          <button
            onClick={handleApprove}
            disabled={approving}
            className={`px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors ${
              approving ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {approving ? 'Approving...' : `Approve Option ${selectedOption}`}
          </button>
        </div>

        {/* Info Box */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-yellow-800">
                <strong>Important:</strong> This decision will be executed immediately upon approval.
                The customer will be notified and logistics resources will be allocated.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApprovalInterface;
