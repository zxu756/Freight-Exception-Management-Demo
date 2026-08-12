import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { exceptionAPI, shipmentAPI, decisionAPI } from '../services/api';
import type { Exception, Shipment, Decision, TimelineEvent } from '../types';
import TimelineView from './TimelineView';
import ApprovalInterface from './ApprovalInterface';

const CaseDetail = () => {
  const { caseNumber } = useParams<{ caseNumber: string }>();
  const navigate = useNavigate();

  const [exception, setException] = useState<Exception | null>(null);
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Map case number to shipment ID
  const caseMap: Record<string, string> = {
    '1': 'SF-2024-09001',
    '2': 'SF-2024-09002',
    '3': 'SF-2024-09003',
  };

  useEffect(() => {
    loadCaseData();
  }, [caseNumber]);

  const loadCaseData = async () => {
    try {
      setLoading(true);
      const shipmentId = caseMap[caseNumber || ''];

      if (!shipmentId) {
        setError('Case not found');
        return;
      }

      // Load shipment
      const shipmentData = await shipmentAPI.getById(shipmentId);
      setShipment(shipmentData);

      // Load exceptions
      const exceptionsData = await exceptionAPI.getAll();
      const exceptionData = exceptionsData.find(e => e.shipment_id === shipmentId);

      if (exceptionData) {
        setException(exceptionData);

        // Load timeline
        const timelineData = await exceptionAPI.getTimeline(exceptionData.exception_id);
        setTimeline(timelineData.timeline);

        // Load decision if exists
        try {
          const decisionData = await decisionAPI.get(exceptionData.exception_id);
          setDecision(decisionData);
        } catch (err) {
          // Decision might not exist yet
          console.log('No decision found yet');
        }
      }

      setError(null);
    } catch (err) {
      setError('Failed to load case data');
      console.error('Error loading case:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async () => {
    // Reload data after approval
    await loadCaseData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading case details...</p>
        </div>
      </div>
    );
  }

  if (error || !exception || !shipment) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Case not found'}</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-600 bg-green-50 border-green-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'high': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/')}
                className="mr-4 text-gray-600 hover:text-gray-900"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Case {caseNumber}: {exception.exception_type.replace('_', ' ').toUpperCase()}
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  {exception.exception_id} • {shipment.shipment_id}
                </p>
              </div>
            </div>
            <div className={`px-4 py-2 rounded-lg border-2 font-semibold ${getRiskColor(exception.risk_level)}`}>
              {exception.risk_level.toUpperCase()} RISK
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Exception Summary */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Exception Summary</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Customer</p>
                  <p className="font-medium text-gray-900">{shipment.customer_name}</p>
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    {shipment.customer_tier}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Cargo Value</p>
                  <p className="font-medium text-gray-900">${shipment.cargo_value.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Route</p>
                  <p className="font-medium text-gray-900">{shipment.origin} → {shipment.destination}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Transport Mode</p>
                  <p className="font-medium text-gray-900 capitalize">{shipment.transport_mode}</p>
                </div>
              </div>
            </div>

            {/* AI Diagnosis */}
            {exception.ai_diagnosis && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-blue-900">
                      AI Diagnosis
                      {exception.ai_confidence && (
                        <span className="ml-2 text-blue-700">
                          ({Math.round(exception.ai_confidence * 100)}% confidence)
                        </span>
                      )}
                    </h3>
                    <p className="mt-2 text-sm text-blue-800">{exception.ai_diagnosis}</p>
                    {exception.root_cause && (
                      <p className="mt-2 text-sm text-blue-700">
                        <strong>Root Cause:</strong> {exception.root_cause}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Approval Interface for Case 2 */}
            {caseNumber === '2' && exception.status === 'pending_approval' && decision && (
              <ApprovalInterface
                exception={exception}
                decision={decision}
                shipment={shipment}
                onApproval={handleApproval}
              />
            )}

            {/* Timeline */}
            <TimelineView timeline={timeline} />
          </div>

          {/* Right Column - Status */}
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Status</h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600">Current Status</p>
                  <p className="font-medium text-gray-900 capitalize">{exception.status.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Severity</p>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                    exception.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    exception.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    exception.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {exception.severity}
                  </span>
                </div>
                {exception.assigned_to && (
                  <div>
                    <p className="text-sm text-gray-600">Assigned To</p>
                    <p className="font-medium text-gray-900">{exception.assigned_to}</p>
                  </div>
                )}
                {exception.resolution_time_minutes && (
                  <div>
                    <p className="text-sm text-gray-600">Resolution Time</p>
                    <p className="font-medium text-green-600">{exception.resolution_time_minutes} minutes</p>
                  </div>
                )}
              </div>
            </div>

            {/* Cargo Details */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cargo Details</h3>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Description</p>
                  <p className="text-sm text-gray-900">{shipment.cargo_description}</p>
                </div>
                {shipment.container_id && (
                  <div>
                    <p className="text-sm text-gray-600">Container ID</p>
                    <p className="text-sm text-gray-900 font-mono">{shipment.container_id}</p>
                  </div>
                )}
                {shipment.vehicle_id && (
                  <div>
                    <p className="text-sm text-gray-600">Vehicle ID</p>
                    <p className="text-sm text-gray-900 font-mono">{shipment.vehicle_id}</p>
                  </div>
                )}
                {shipment.special_requirements && (
                  <div>
                    <p className="text-sm text-gray-600">Special Requirements</p>
                    <p className="text-sm text-gray-900">{shipment.special_requirements}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CaseDetail;
