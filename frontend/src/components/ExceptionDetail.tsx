import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Search, Brain, MousePointerClick, Scale, Package, Bell } from 'lucide-react';
import { airAPI, roadAPI, seaAPI } from '../services/api';

const APIS: Record<string, typeof airAPI> = { sea: seaAPI, road: roadAPI, air: airAPI };

const riskColor = (risk: string | undefined) => {
  switch (risk) {
    case 'high': return 'text-red-600';
    case 'medium': return 'text-amber-600';
    case 'low': return 'text-green-600';
    default: return 'text-gray-600';
  }
};

const statusLabel: Record<string, string> = {
  diagnosed: '已自动诊断',
  pending_approval: '待人工审批',
  escalated: '已升级',
  detected: '已检测',
};

function Step({ n, icon: Icon, title, subtitle, children }: { n: number; icon: any; title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold shrink-0">
          {n}
        </div>
        <Icon className="w-5 h-5 text-blue-600" />
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <p className="text-xs text-gray-500">{subtitle}</p>
        </div>
      </div>
      <div className="pl-11 space-y-2 text-sm">{children}</div>
    </div>
  );
}

function Field({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className={`text-right ${highlight ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>{value}</span>
    </div>
  );
}

const ExceptionDetail = () => {
  const { mode, exceptionId } = useParams();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState(false);
  const [siblingLines, setSiblingLines] = useState<any[] | null>(null);
  const [decisionMode, setDecisionMode] = useState<'approve' | 'reject' | 'modify'>('approve');
  const [chosenAction, setChosenAction] = useState('');
  const [decidedBy, setDecidedBy] = useState('');
  const [note, setNote] = useState('');
  const [deciding, setDeciding] = useState(false);
  const [decisionMsg, setDecisionMsg] = useState('');

  const reload = useCallback(() => {
    const api = APIS[mode ?? ''];
    if (!api || !exceptionId) return;
    api.getException(exceptionId)
      .then(setData)
      .catch(() => setError(true));
  }, [mode, exceptionId]);

  useEffect(() => { reload(); }, [reload]);

  const submitDecision = async () => {
    const api = APIS[mode ?? ''];
    if (!api || !exceptionId || !data) return;
    setDeciding(true);
    setDecisionMsg('');
    try {
      await api.decideException(exceptionId, {
        decided_by: decidedBy.trim() || 'Coordinator',
        decision: decisionMode,
        chosen_action: decisionMode === 'reject' ? null : (chosenAction || data.recommended_action),
        note: note.trim() || undefined,
      });
      setDecisionMsg('决策已记录，异常已标记为已解决');
      await reload();
    } catch {
      setDecisionMsg('决策提交失败，请重试');
    } finally {
      setDeciding(false);
    }
  };

  // 票级异常：加载同箱/同单/同主单的全部票做对比（海运/陆运用票号，空运用分运单号）
  const lineNumber = data?.cargo?.line_number;
  const hawbNumber = data?.cargo?.hawb_number;
  const refNumber = data?.cargo?.container_number ?? data?.cargo?.awb_number;
  const hasTicket = !!(lineNumber || hawbNumber);
  useEffect(() => {
    if (!data || !hasTicket || !refNumber || !mode) { setSiblingLines(null); return; }
    APIS[mode]?.getLines(refNumber)
      .then((d: any) => setSiblingLines(d.lines ?? d.house_waybills ?? []))
      .catch(() => setSiblingLines(null));
  }, [data, hasTicket, refNumber, mode]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 mb-4">加载异常详情失败</p>
          <Link to="/live" className="text-blue-600 hover:underline">返回实时面板</Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 恢复行动：新格式为带细节的对象数组（后端已按 最推荐→最不推荐 排序）；
  // 老格式为字符串数组，这里兜底归一化。
  const recoveryOptions: any[] = (() => {
    try {
      const raw = JSON.parse(data.recovery_options ?? '[]');
      if (!Array.isArray(raw)) return [];
      return raw.map((o: any) => typeof o === 'string'
        ? { action: o, label: o, description: undefined, impact_hours: undefined, cost: undefined, score: undefined, why: undefined, recommended: o === data.recommended_action }
        : o);
    } catch { return []; }
  })();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI 异常处理流水线</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {data.exception_id} · {data.exception_type}
            </p>
          </div>
          <Link to="/live" className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
            返回面板
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {/* 货物概要 */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <Package className="w-5 h-5 text-gray-500" />
            <div className="flex-1">
              <p className="font-medium text-gray-900">
                {data.cargo?.commodity_desc ?? '未知货物'}
                {(lineNumber || hawbNumber) && (
                  <span className="ml-2 inline-block px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 text-[10px] align-middle font-semibold">
                    {lineNumber ? '第 ' + lineNumber + ' 票' : hawbNumber}
                  </span>
                )}
              </p>
              <p className="text-xs text-gray-500">
                {data.cargo?.customer_name ?? '未知客户'}
                {data.cargo?.customer_tier ? ` · ${data.cargo.customer_tier} 客户` : ''}
                {data.cargo?.declared_value_nzd ? ` · 货值 $${data.cargo.declared_value_nzd.toLocaleString()}` : ''}
                {data.cargo?.service_level ? ` · ${data.cargo.service_level} 服务` : ''}
              </p>
              {data.cargo?.customer_email && (
                <p className="text-xs text-gray-500 mt-0.5">
                  联系人 {data.cargo.customer_contact} · {data.cargo.customer_email} · {data.cargo.customer_phone}
                </p>
              )}
              {data.cargo?.is_sla_breached && (
                <p className="text-xs text-red-600 mt-1">
                  SLA 违约（{data.cargo.breach_type === 'excused' ? '已豁免' : '未豁免'}）
                  {data.cargo.sla_penalty_nzd ? ` · 违约金 $${data.cargo.sla_penalty_nzd.toLocaleString()}` : ''}
                </p>
              )}
              {data.cargo?.breach_type === 'excused' && (
                <p className="text-xs text-amber-600 mt-1">SLA 豁免（天气/海关等排除项），不计 OTD 但已通知</p>
              )}
            </div>
            <div className="text-right">
              <p className={`text-lg font-bold ${riskColor(data.risk_level)}`}>
                {data.risk_level?.toUpperCase()}
              </p>
              <p className="text-xs text-gray-500">{statusLabel[data.status] ?? data.status}</p>
            </div>
          </div>
        </div>

        {/* 同箱/同单全部票（票级异常对比） */}
        {siblingLines && siblingLines.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Package className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">
                同一装载单元的全部票 <span className="text-xs text-gray-400 font-normal">（{siblingLines.length} 票，各自独立 SLA）</span>
              </h3>
            </div>
            <div className="space-y-1.5">
              {siblingLines.map((l: any) => {
                const label = l.line_number != null ? '票' + l.line_number : (l.hawb_number ?? '—');
                const isCurrent = (l.line_number ?? l.hawb_number ?? null) === (lineNumber ?? hawbNumber ?? null);
                const breached = !!l.is_sla_breached;
                return (
                  <div key={label + (l.customer_name ?? '')} className={'flex items-center justify-between px-3 py-1.5 rounded border ' + (isCurrent ? 'border-purple-300 bg-purple-50' : breached ? 'border-red-200 bg-red-50' : 'border-gray-200')}>
                    <span className="text-sm">
                      <span className="font-medium">{label}</span>
                      {isCurrent && <span className="ml-1.5 text-[10px] text-purple-600 font-semibold">← 本异常</span>}
                      <span className="text-gray-500 ml-1.5">{l.customer_name} ({l.customer_tier}) · {l.service_level} · 货值 {'$' + (l.declared_value_nzd ?? 0).toLocaleString()}</span>
                    </span>
                    <span className="text-xs shrink-0">
                      {breached
                        ? <span className="text-red-600 font-medium">违约{l.breach_type === 'excused' ? '(豁免)' : ''}{l.sla_penalty_nzd ? ' · 罚金 $' + l.sla_penalty_nzd.toLocaleString() : ''}</span>
                        : <span className="text-green-600">达标</span>}
                      {l.sla_deadline && <span className="text-gray-400 ml-2">截止 {l.sla_deadline.slice(5, 16).replace('T', ' ')}</span>}
                    </span>
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-gray-400 mt-2">票级粒度：同一箱/单里的每票货独立判定 SLA，只有违约的那一票产生本异常并通知其货主。</p>
          </div>
        )}

        {/* 步骤 1：检测 */}
        <Step n={1} icon={Search} title="Delay detected" subtitle="异常检测">
          <Field label="异常类型" value={<span className="font-semibold">{data.exception_type}</span>} highlight />
          <Field label="异常分类" value={data.exception_category ?? '—'} />
          <Field label="根因" value={data.root_cause ?? '—'} highlight />
          <Field label="根因类别" value={data.root_cause_category ?? '—'} />
          <Field label="检测时间" value={data.detected_at ? data.detected_at.slice(0, 19).replace('T', ' ') : '—'} />
          {data.trigger_event_id && <Field label="触发事件" value={data.trigger_event_id} />}
          <Field label="检测延迟（事件→检测）" value={data.detection_latency_minutes != null ? data.detection_latency_minutes + ' 分钟' : '—'} highlight={data.detection_latency_minutes != null && data.detection_latency_minutes > 15} />
          {data.anomaly_reason && <Field label="预测信号" value={data.anomaly_reason} />}
        </Step>

        {/* 步骤 2：AI 评估 */}
        <Step n={2} icon={Brain} title="AI Initial Assessment" subtitle="AI 初步评估">
          <Field label="AI 诊断" value={data.ai_diagnosis ?? '—'} highlight />
          <Field label="AI 置信度" value={data.ai_confidence ? `${(data.ai_confidence * 100).toFixed(0)}%` : '—'} />
          <Field label="语义分类" value={data.business_section ?? '—'} />
          <Field label="分类决策" value={data.classification_decision ?? '—'} />
          {data.is_ood && (
            <div className="bg-red-50 border border-red-200 rounded p-2 text-red-700 text-xs">
              分布外（OOD）：这是陌生异常模式，已升级人工并触发 LLM 二次诊断
            </div>
          )}
        </Step>

        {/* 步骤 3：AI 选行动（全部行动按推荐度排序，每项带细节） */}
        <Step n={3} icon={MousePointerClick} title="AI Selects Pre-approved Recovery Action" subtitle="AI 选择预批准恢复行动（最推荐 → 最不推荐）">
          {recoveryOptions.length > 0 ? (
            <div className="space-y-2">
              {recoveryOptions.map((o: any, i: number) => {
                const isRecommended = o.recommended === true || o.action === data.recommended_action;
                return (
                  <div key={o.action + '-' + i} className={'rounded-lg border p-3 ' + (isRecommended ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white')}>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={'shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ' + (isRecommended ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600')}>{i + 1}</span>
                        <span className="font-medium text-gray-900">{o.label ?? o.action}</span>
                        {isRecommended && <span className="shrink-0 px-1.5 py-0.5 rounded bg-blue-600 text-white text-[10px] font-semibold">AI 推荐</span>}
                      </div>
                      <code className="shrink-0 text-[10px] text-gray-400">{o.action}</code>
                    </div>
                    {o.description && <p className="text-xs text-gray-600 mt-1.5">{o.description}</p>}
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 mt-1.5">
                      {o.impact_hours != null && <span>预计挽回约 {o.impact_hours}h 延误</span>}
                      {o.cost != null && <span>成本 {'$' + o.cost.toLocaleString()}</span>}
                      {o.score != null && <span>综合得分 {Number(o.score).toFixed(1)}</span>}
                    </div>
                    {o.why && <p className={'text-xs mt-1.5 ' + (isRecommended ? 'text-blue-700' : 'text-gray-500')}>{o.why}</p>}
                  </div>
                );
              })}
            </div>
          ) : (
            <Field label="推荐行动" value={data.recommended_action ?? '—'} highlight />
          )}
          {data.recommendation_reason && (
            <p className="text-xs text-gray-500 bg-gray-50 rounded p-2 mt-1">推荐理由：{data.recommendation_reason}</p>
          )}
        </Step>

        {/* 步骤 4：风险与方案 */}
        <Step n={4} icon={Scale} title="Risk & Resolution" subtitle="风险与解决方案">
          <Field label="风险分数" value={<span className={`font-semibold ${riskColor(data.risk_level)}`}>{data.risk_score}/100</span>} highlight />
          <Field label="风险等级" value={data.risk_level} />
          <Field label="严重度" value={data.severity} />
          <Field label="恢复成本" value={data.recovery_cost != null ? `$${data.recovery_cost.toLocaleString()}` : '—'} />
          <Field label="预测下游影响" value={data.predicted_downstream_impact ?? '—'} highlight />
        </Step>

        {/* 步骤 5：协调员决策（P0 学习闭环） */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="w-5 h-5 text-indigo-600" />
            <h3 className="font-semibold text-gray-900">协调员决策 <span className="text-xs text-gray-400 font-normal">（审批结果会被 AI 学习，影响后续推荐排序）</span></h3>
          </div>

          {data.status === 'resolved' ? (
            <div className="space-y-2 text-sm">
              <div className="bg-green-50 border border-green-200 rounded p-3">
                <p className="text-green-800 font-medium">已解决</p>
                <p className="text-xs text-green-700 mt-1">
                  实际行动 {data.actual_action ?? '—'} · 实际成本 {data.actual_cost != null ? '$' + data.actual_cost.toLocaleString() : '—'} · 实际挽回 {data.actual_recovery_hours ?? '—'}h
                  {data.resolved_at ? ' · 解决时间 ' + data.resolved_at.slice(0, 19).replace('T', ' ') : ''}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={decidedBy}
                  onChange={(e) => setDecidedBy(e.target.value)}
                  placeholder="决策人（默认 Coordinator）"
                  className="text-sm px-3 py-1.5 rounded border border-gray-300 focus:border-indigo-400 focus:outline-none w-52"
                />
                <div className="flex gap-1.5">
                  {(['approve', 'modify', 'reject'] as const).map((k) => (
                    <button
                      key={k}
                      onClick={() => setDecisionMode(k)}
                      className={'px-3 py-1.5 rounded text-sm ' + (decisionMode === k ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200')}
                    >
                      {k === 'approve' ? '批准推荐' : k === 'modify' ? '修改后执行' : '驳回'}
                    </button>
                  ))}
                </div>
              </div>
              {decisionMode !== 'reject' && recoveryOptions.length > 0 && (
                <select
                  value={chosenAction || data.recommended_action || ''}
                  onChange={(e) => setChosenAction(e.target.value)}
                  className="text-sm px-3 py-1.5 rounded border border-gray-300 w-full max-w-md"
                >
                  {recoveryOptions.map((o: any) => (
                    <option key={o.action} value={o.action}>{o.label ?? o.action}（成本 {'$' + (o.cost ?? '—')} · 挽回 {o.impact_hours ?? '—'}h）</option>
                  ))}
                </select>
              )}
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="备注（为什么这么批，可选）"
                rows={2}
                className="text-sm px-3 py-2 rounded border border-gray-300 w-full focus:border-indigo-400 focus:outline-none"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={submitDecision}
                  disabled={deciding}
                  className="px-4 py-2 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {deciding ? '提交中…' : '记录决策并标记已解决'}
                </button>
                {decisionMsg && <span className="text-xs text-gray-600">{decisionMsg}</span>}
              </div>
            </div>
          )}

          {data.decisions?.length > 0 && (
            <div className="mt-4 space-y-1.5">
              <p className="text-xs text-gray-500 font-medium">决策历史（{data.decisions.length} 条）</p>
              {data.decisions.map((d: any) => (
                <div key={d.decision_id} className="flex items-center justify-between text-xs rounded border border-gray-200 bg-gray-50 px-3 py-1.5">
                  <span>
                    <span className={'font-medium ' + (d.decision === 'approve' ? 'text-green-700' : d.decision === 'modify' ? 'text-amber-700' : 'text-red-600')}>
                      {d.decision === 'approve' ? '批准' : d.decision === 'modify' ? '修改' : '驳回'}
                    </span>
                    <span className="text-gray-600 ml-2">{d.decided_by} · {d.chosen_action ?? '无行动'}</span>
                    {d.note && <span className="text-gray-400 ml-2">{'"' + d.note + '"'}</span>}
                  </span>
                  <span className="text-gray-400 shrink-0 ml-2">
                    {d.decision_latency_minutes != null ? d.decision_latency_minutes + 'min · ' : ''}{d.decided_at ? d.decided_at.slice(0, 19).replace('T', ' ') : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 客户通知 */}
        {data.notifications?.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Bell className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">客户通知</h3>
            </div>
            <div className="space-y-2">
              {data.notifications.map((n: any) => (
                <div key={n.notification_id} className="bg-blue-50 border border-blue-100 rounded p-3 text-sm text-gray-700">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-blue-200 text-blue-600">{n.channel === 'sms' ? '短信' : '邮件'}</span>
                    {n.recipient_email
                      ? <span className="text-[11px] text-gray-500">发至 {n.recipient} · {n.recipient_email}</span>
                      : <span className="text-[11px] text-gray-500">收件人 {n.recipient}</span>}
                  </div>
                  {n.message}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ExceptionDetail;
