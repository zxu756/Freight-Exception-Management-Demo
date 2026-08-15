import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Globe, Pause, Play, Gauge, Ship, Route, ArrowLeft, RefreshCw } from 'lucide-react';
import { worldAPI } from '../services/api';

const CONDITION_EMOJI: Record<string, string> = {
  clear: '☀️', cloudy: '⛅', showers: '🌦️', rain: '🌧️', heavy_rain: '🌧️',
  storm: '⛈️', fog: '🌫️', snow: '🌨️', windy: '💨',
};

const QUICK = [
  { key: 'fog', label: '大雾', emoji: '🌫️' },
  { key: 'storm', label: '暴风雨', emoji: '⛈️' },
  { key: 'snow', label: '降雪', emoji: '🌨️' },
  { key: 'heavy_rain', label: '大雨', emoji: '🌧️' },
  { key: 'clear', label: '晴', emoji: '☀️' },
];

const MODE_LABEL: Record<string, string> = { sea: '海', road: '陆', air: '空' };

const WorldControl = () => {
  const [clock, setClock] = useState<{ now: string; speed: number; paused: boolean }>({ now: '', speed: 60, paused: false });
  const [regions, setRegions] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [shipments, setShipments] = useState<any[]>([]);
  const [shipCount, setShipCount] = useState(0);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [c, w, s, sh, pr] = await Promise.all([
        worldAPI.getClock(), worldAPI.getWeather(), worldAPI.getState(), worldAPI.getShipments(), worldAPI.getPredictions(),
      ]);
      setClock(c); setRegions(w.regions ?? []); setEvents(s.active_events ?? []);
      setShipments(sh.shipments ?? []); setShipCount(sh.count ?? 0);
      setPredictions(pr.predictions ?? []); setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try { await fn(); } finally { await load(); setBusy(false); }
  };

  const control = (action: string, extra?: Record<string, unknown>) =>
    act(() => worldAPI.controlClock({ action, ...extra }));

  const setWeather = (target: string, condition: string) =>
    act(() => worldAPI.setWeatherOverride({ target, condition, intensity: 1, hours: 6 }));

  const clearWeather = () => act(() => worldAPI.clearWeather());

  const jump = (hours: number) => {
    const d = new Date(clock.now);
    d.setHours(d.getHours() + hours);
    const pad = (n: number) => String(n).padStart(2, '0');
    const iso = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    control('set_time', { time: iso });
  };

  const fmt = (iso: string) => (iso ? new Date(iso).toLocaleString('zh-CN', { hour12: false }) : '—');

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-slate-900 text-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <Globe className="w-7 h-7 text-sky-400" />
              <div>
                <h1 className="text-lg font-bold leading-tight">世界控制台 · God Panel</h1>
                <p className="text-xs text-slate-400">新西兰物流数字孪生 · 统一世界内核</p>
              </div>
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              <div className="text-right">
                <div className="font-mono text-sm text-sky-300">{fmt(clock.now)}</div>
                <div className="text-[11px] text-slate-400 flex items-center gap-1 justify-end">
                  <Gauge className="w-3 h-3" /> {clock.speed}x {clock.paused ? '· 已暂停' : ''}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => control(clock.paused ? 'resume' : 'pause')}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-sky-500 hover:bg-sky-600 text-sm font-medium"
                >
                  {clock.paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  {clock.paused ? '继续' : '暂停'}
                </button>
                {[1, 60, 600, 3600].map((s) => (
                  <button
                    key={s}
                    onClick={() => control('set_speed', { speed: s })}
                    className={'px-2.5 py-1.5 rounded text-sm ' + (clock.speed === s ? 'bg-sky-600' : 'bg-slate-700 hover:bg-slate-600')}
                  >
                    {s}x
                  </button>
                ))}
                <button onClick={() => jump(6)} className="px-2.5 py-1.5 rounded text-sm bg-slate-700 hover:bg-slate-600" title="快进 6 小时">+6h</button>
                <button onClick={() => jump(24)} className="px-2.5 py-1.5 rounded text-sm bg-slate-700 hover:bg-slate-600" title="快进 24 小时">+24h</button>
                <Link to="/live" className="flex items-center gap-1 px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 text-sm">
                  <ArrowLeft className="w-4 h-4" /> 实时看板
                </Link>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
            无法连接世界内核 API（后端可能未运行）。
          </div>
        )}

        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-xl">🌍</span> 区域天气 · 上帝操控
            </h2>
            <button onClick={clearWeather} disabled={busy} className="flex items-center gap-1 text-xs px-3 py-1.5 rounded border border-gray-300 hover:bg-gray-50 text-gray-600">
              <RefreshCw className="w-3.5 h-3.5" /> 清除所有覆盖
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
            {regions.map((r) => (
              <div key={r.region} className="rounded-lg border border-gray-200 p-3 bg-gray-50">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-800">{r.name}</span>
                  <span className="text-2xl leading-none">{CONDITION_EMOJI[r.condition] ?? '🌤️'}</span>
                </div>
                <p className="text-[11px] text-gray-500 leading-tight">
                  {r.condition_label} · {r.temperature_c}°C
                </p>
                <p className="text-[11px] text-gray-400 leading-tight mb-2">
                  风 {r.wind_knots}kt · 能见度 {r.visibility_km}km
                </p>
                <div className="flex gap-1">
                  {QUICK.map((q) => (
                    <button
                      key={q.key}
                      onClick={() => setWeather(r.region, q.key)}
                      disabled={busy}
                      title={'设为' + q.label}
                      className="flex-1 py-1 rounded bg-white border border-gray-200 hover:border-sky-400 hover:bg-sky-50 text-sm"
                    >
                      {q.emoji}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-3">点天气图标即可把该区域强制设为指定天气 6 小时，天气会通过因果引擎传导到空/陆/海延误。</p>
        </section>

        {/* 预测影响（缓冲期内预报） */}
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <span className="text-xl">🔮</span> 预测影响
            <span className="text-xs text-gray-400">({predictions.filter((p) => p.status === 'predicted').length} 待应验 / {predictions.length} 总)</span>
          </h2>
          {predictions.length === 0 && <p className="text-sm text-gray-400">暂无预测（天气事件处于缓冲期时会预报受影响班次）</p>}
          <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
            {predictions.map((p, i) => (
              <div key={i} className={'rounded-lg border px-3 py-2 text-xs ' + (p.status === 'predicted' ? 'border-sky-200 bg-sky-50' : 'border-amber-200 bg-amber-50')}>
                <div className="text-gray-700">{p.description}</div>
                <div className="mt-0.5 text-[10px] text-gray-400">
                  {p.mode} · {p.reference} · {p.status === 'predicted' ? '预测中' : '已应验'}
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <span className="text-xl">🚨</span> 活跃环境事件 <span className="text-xs text-gray-400">({events.length})</span>
            </h2>
            {events.length === 0 && <p className="text-sm text-gray-400">当前无活跃事件</p>}
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {events.map((e, i) => (
                <div key={i} className="flex items-start gap-2 text-sm rounded-lg border border-amber-100 bg-amber-50 px-3 py-2">
                  <span className="shrink-0 inline-flex items-center justify-center w-5 h-5 rounded bg-slate-700 text-white text-[10px] font-bold">
                    {MODE_LABEL[e.mode] ?? e.mode}
                  </span>
                  <div className="min-w-0">
                    <div className="text-xs text-gray-700 leading-snug">{e.description}</div>
                    <div className="text-[10px] text-gray-400">{e.location} · {e.event_type} · {e.severity}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <span className="text-xl">🔗</span> 多式联运货物链 <span className="text-xs text-gray-400">({shipCount})</span>
            </h2>
            {shipments.length === 0 && <p className="text-sm text-gray-400">暂无跨模式货物链</p>}
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {shipments.map((s) => (
                <div key={s.shipment_id} className="rounded-lg border border-gray-200 px-3 py-2">
                  <div className="font-mono text-[11px] text-gray-400 mb-1">{s.shipment_id}</div>
                  <div className="flex items-center flex-wrap gap-1.5 text-xs">
                    {s.legs.map((l: any, i: number) => (
                      <span key={i} className="flex items-center gap-1.5">
                        <span className={'inline-flex items-center gap-1 px-2 py-0.5 rounded ' + (l.mode === 'road' ? 'bg-amber-100 text-amber-800' : 'bg-sky-100 text-sky-800')}>
                          {l.mode === 'road' ? <Route className="w-3 h-3" /> : <Ship className="w-3 h-3" />}
                          {l.reference}
                        </span>
                        {i < s.legs.length - 1 && <span className="text-gray-400">→</span>}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default WorldControl;
