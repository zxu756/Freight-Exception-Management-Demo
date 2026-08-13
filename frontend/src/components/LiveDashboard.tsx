import { useEffect, useState, useCallback } from 'react';
import { Ship, Truck, Plane, Pause, Play } from 'lucide-react';
import { airAPI, roadAPI, seaAPI } from '../services/api';
import type { TransportLiveData, TransportDashboardData } from '../types';

interface ModeData {
  live: TransportLiveData | null;
  dashboard: TransportDashboardData | null;
  kpi: Record<string, unknown> | null;
}

type ModeKey = 'air' | 'road' | 'sea';

const MODES: Record<ModeKey, { label: string; icon: typeof Ship; color: string; api: typeof airAPI }> = {
  sea: { label: '海运 Sea Freight', icon: Ship, color: 'text-blue-600', api: seaAPI },
  road: { label: '陆运 Road Freight', icon: Truck, color: 'text-amber-600', api: roadAPI },
  air: { label: '空运 Air Cargo', icon: Plane, color: 'text-sky-600', api: airAPI },
};

const riskColor = (risk: string) => {
  switch (risk) {
    case 'high': return 'bg-red-100 text-red-700';
    case 'medium': return 'bg-yellow-100 text-yellow-700';
    case 'low': return 'bg-green-100 text-green-700';
    default: return 'bg-gray-100 text-gray-600';
  }
};

const statusBarColors: Record<string, string> = {
  scheduled: 'bg-sky-400', loading: 'bg-indigo-400', in_transit: 'bg-blue-500',
  departed: 'bg-blue-500', boarding: 'bg-indigo-400', delayed: 'bg-amber-500',
  arrived: 'bg-emerald-500', landed: 'bg-emerald-500', cancelled: 'bg-gray-400',
  diverted: 'bg-red-400', EXPECTED: 'bg-sky-400', INPORT: 'bg-blue-500',
  DEPARTED: 'bg-emerald-500', at_sea: 'bg-sky-400', discharged: 'bg-blue-500',
};

function TransportPanel({ mode, data }: { mode: ModeKey; data: ModeData }) {
  const meta = MODES[mode];
  const Icon = meta.icon;
  const { live, dashboard } = data;

  const statusTotal = Object.values(live?.by_status ?? {}).reduce((a, b) => a + b, 0) || 1;
  const exceptions = dashboard?.exceptions ?? { open: 0, high_risk: 0, pending_approval: 0, by_type: {}, by_risk_level: {} };
  const riskLevels = exceptions.by_risk_level ?? {};
  const riskTotal = Object.values(riskLevels).reduce((a, b) => a + b, 0) || 1;
  const openExceptions = live?.open_exceptions ?? [];
  const recentEvents = (live?.recent_events ?? []).slice(0, 12);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Icon className={`w-6 h-6 ${meta.color}`} />
          <div>
            <h2 className="font-semibold text-gray-900">{meta.label}</h2>
            <div className="flex items-center gap-2 mt-0.5 text-xs">
              <span className={`inline-flex items-center gap-1 ${live?.simulator.running ? 'text-green-600' : 'text-gray-400'}`}>
                <span className={`w-2 h-2 rounded-full ${live?.simulator.running ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
                {live?.simulator.running ? (live.simulator.paused ? 'paused' : 'live') : 'stopped'}
              </span>
              <span className="text-gray-400">·</span>
              <span className="text-gray-500">{live?.simulator.speed}x</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => meta.api.control(live?.simulator.paused ? 'resume' : 'pause')}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          title={live?.simulator.paused ? 'Resume' : 'Pause'}
        >
          {live?.simulator.paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
        </button>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-3 gap-px bg-gray-100">
        <div className="bg-white px-4 py-3">
          <p className="text-xs text-gray-500">任务/船期</p>
          <p className="text-2xl font-bold text-gray-900">{live?.tasks_total ?? 0}</p>
        </div>
        <div className="bg-white px-4 py-3">
          <p className="text-xs text-gray-500">未关闭异常</p>
          <p className="text-2xl font-bold text-red-600">{exceptions.open}</p>
        </div>
        <div className="bg-white px-4 py-3">
          <p className="text-xs text-gray-500">高风险</p>
          <p className="text-2xl font-bold text-orange-600">{exceptions.high_risk}</p>
        </div>
      </div>

      {/* KPI (Kratos Task 12) */}
      {data.kpi && (data.kpi as Record<string, unknown>).total ? (
        <div className="grid grid-cols-3 gap-px bg-gray-100 border-t border-gray-100">
          <div className="bg-white px-4 py-2">
            <p className="text-[10px] text-gray-500">自动处理率</p>
            <p className="text-sm font-semibold text-gray-900">
              {Math.round(((data.kpi as Record<string, unknown>).automation_rate as number) * 100)}%
            </p>
          </div>
          <div className="bg-white px-4 py-2">
            <p className="text-[10px] text-gray-500">升级率</p>
            <p className="text-sm font-semibold text-gray-900">
              {Math.round(((data.kpi as Record<string, unknown>).escalation_rate as number) * 100)}%
            </p>
          </div>
          <div className="bg-white px-4 py-2">
            <p className="text-[10px] text-gray-500">SLA 违约率</p>
            <p className="text-sm font-semibold text-gray-900">
              {Math.round(((data.kpi as Record<string, unknown>).sla_breach_rate as number) * 100)}%
            </p>
          </div>
        </div>
      ) : null}

      <div className="px-5 py-4 space-y-4 flex-1">
        {/* Status distribution */}
        {Object.keys(live?.by_status ?? {}).length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-500">状态分布</span>
            </div>
            <div className="flex h-2 rounded-full overflow-hidden bg-gray-100">
              {Object.entries(live!.by_status).map(([status, count]) => (
                <div
                  key={status}
                  className={statusBarColors[status] ?? 'bg-gray-300'}
                  style={{ width: `${(count / statusTotal) * 100}%` }}
                  title={`${status}: ${count}`}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {Object.entries(live!.by_status).slice(0, 6).map(([status, count]) => (
                <span key={status} className="inline-flex items-center gap-1 text-xs text-gray-600">
                  <span className={`w-2 h-2 rounded-full ${statusBarColors[status] ?? 'bg-gray-300'}`} />
                  {status} {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Risk level distribution */}
        {Object.keys(riskLevels).length > 0 && (
          <div>
            <span className="text-xs font-medium text-gray-500">风险等级</span>
            <div className="mt-2 flex h-2 rounded-full overflow-hidden bg-gray-100">
              <div className="bg-green-400" style={{ width: `${((riskLevels.low ?? 0) / riskTotal) * 100}%` }} />
              <div className="bg-yellow-400" style={{ width: `${((riskLevels.medium ?? 0) / riskTotal) * 100}%` }} />
              <div className="bg-red-400" style={{ width: `${((riskLevels.high ?? 0) / riskTotal) * 100}%` }} />
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs">
              <span className="flex items-center gap-1 text-gray-600">
                <span className="w-2 h-2 rounded-full bg-green-400" /> low {riskLevels.low ?? 0}
              </span>
              <span className="flex items-center gap-1 text-gray-600">
                <span className="w-2 h-2 rounded-full bg-yellow-400" /> medium {riskLevels.medium ?? 0}
              </span>
              <span className="flex items-center gap-1 text-gray-600">
                <span className="w-2 h-2 rounded-full bg-red-400" /> high {riskLevels.high ?? 0}
              </span>
            </div>
          </div>
        )}

        {/* Exception type distribution */}
        {Object.keys(exceptions.by_type).length > 0 && (
          <div>
            <span className="text-xs font-medium text-gray-500">异常类型</span>
            <div className="mt-2 space-y-1.5">
              {Object.entries(exceptions.by_type)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-xs">
                    <span className="text-gray-600 truncate">{type}</span>
                    <span className="font-medium text-gray-800">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Open exceptions */}
        <div>
          <span className="text-xs font-medium text-gray-500">未关闭异常</span>
          <div className="mt-2 space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {openExceptions.slice(0, 8).map((exc) => {
              const section = (exc.exception_category as string) ?? (exc.business_section as string) ?? exc.exception_type;
              const aiMismatch = exc.exception_category && exc.business_section && exc.exception_category !== exc.business_section;
              return (
                <div key={exc.exception_id} className="flex items-start gap-2 text-xs border-b border-gray-50 pb-1.5">
                  <span className={`px-1.5 py-0.5 rounded ${riskColor(exc.risk_level)} shrink-0`}>
                    {exc.risk_level}
                  </span>
                  <div className="min-w-0">
                    <span className="font-medium text-gray-800">{section}</span>
                    {aiMismatch && (
                      <span className="ml-1 px-1 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px]">AI≠规则</span>
                    )}
                    {exc.exception_type === 'predicted_anomaly' && (
                      <span className="ml-1 px-1 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px]">预测</span>
                    )}
                    {exc.is_ood && (
                      <span className="ml-1 px-1 py-0.5 bg-red-100 text-red-700 rounded text-[10px]">新类型</span>
                    )}
                    {exc.classification_decision === 'human_review' && (
                      <span className="ml-1 px-1 py-0.5 bg-purple-100 text-purple-700 rounded text-[10px]">复核</span>
                    )}
                    <span className="text-gray-400 mx-1">·</span>
                    <span className="text-gray-500 truncate">{exc.root_cause ?? ''}</span>
                  </div>
                </div>
              );
            })}
            {openExceptions.length === 0 && (
              <p className="text-xs text-gray-400">暂无未关闭异常</p>
            )}
          </div>
        </div>

        {/* Recent events */}
        <div>
          <span className="text-xs font-medium text-gray-500">最近事件</span>
          <div className="mt-2 space-y-1 max-h-32 overflow-y-auto pr-1 font-mono">
            {recentEvents.map((ev, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-gray-500">
                <span className="text-gray-300">{ev.timestamp?.slice(11, 19)}</span>
                <span className="font-medium text-gray-700">{ev.event_code}</span>
                <span className="truncate">{ev.event_desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const LiveDashboard = () => {
  const [data, setData] = useState<Record<ModeKey, ModeData>>({
    air: { live: null, dashboard: null, kpi: null },
    road: { live: null, dashboard: null, kpi: null },
    sea: { live: null, dashboard: null, kpi: null },
  });
  const [error, setError] = useState(false);
  const [clock, setClock] = useState('');

  const load = useCallback(async () => {
    try {
      const [airLive, airDash, airKpi, roadLive, roadDash, roadKpi, seaLive, seaDash, seaKpi] = await Promise.all([
        airAPI.getLive(), airAPI.getDashboard(), airAPI.getKpi(),
        roadAPI.getLive(), roadAPI.getDashboard(), roadAPI.getKpi(),
        seaAPI.getLive(), seaAPI.getDashboard(), seaAPI.getKpi(),
      ]);
      setData({
        air: { live: airLive, dashboard: airDash, kpi: airKpi },
        road: { live: roadLive, dashboard: roadDash, kpi: roadKpi },
        sea: { live: seaLive, dashboard: seaDash, kpi: seaKpi },
      });
      setClock(seaLive.simulator.sim_now);
      setError(false);
    } catch (e) {
      setError(true);
      console.error('Error loading live data:', e);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">实时货运网络监控</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              海 · 陆 · 空实时模拟器 (每 3 秒刷新)
              {clock && <span className="ml-2 font-mono text-xs">sim {clock.slice(11, 19)}</span>}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {error && <span className="text-xs text-red-600">后端连接失败</span>}
            <a href="/" className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
              返回案例面板
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          <TransportPanel mode="sea" data={data.sea} />
          <TransportPanel mode="road" data={data.road} />
          <TransportPanel mode="air" data={data.air} />
        </div>
      </main>
    </div>
  );
};

export default LiveDashboard;
