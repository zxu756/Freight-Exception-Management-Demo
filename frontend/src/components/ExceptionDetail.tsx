import { useEffect, useState } from 'react';
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

  useEffect(() => {
    const api = APIS[mode ?? ''];
    if (!api || !exceptionId) return;
    api.getException(exceptionId)
      .then(setData)
      .catch(() => setError(true));
  }, [mode, exceptionId]);

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

  const recoveryOptions = (() => {
    try { return JSON.parse(data.recovery_options ?? '[]'); } catch { return []; }
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
              <p className="font-medium text-gray-900">{data.cargo?.commodity_desc ?? '未知货物'}</p>
              <p className="text-xs text-gray-500">
                {data.cargo?.customer_name ?? '未知客户'}
                {data.cargo?.customer_tier ? ` · ${data.cargo.customer_tier} 客户` : ''}
                {data.cargo?.declared_value_nzd ? ` · 货值 $${data.cargo.declared_value_nzd.toLocaleString()}` : ''}
              </p>
            </div>
            <div className="text-right">
              <p className={`text-lg font-bold ${riskColor(data.risk_level)}`}>
                {data.risk_level?.toUpperCase()}
              </p>
              <p className="text-xs text-gray-500">{statusLabel[data.status] ?? data.status}</p>
            </div>
          </div>
        </div>

        {/* 步骤 1：检测 */}
        <Step n={1} icon={Search} title="Delay detected" subtitle="异常检测">
          <Field label="异常类型" value={<span className="font-semibold">{data.exception_type}</span>} highlight />
          <Field label="异常分类" value={data.exception_category ?? '—'} />
          <Field label="根因" value={data.root_cause ?? '—'} highlight />
          <Field label="根因类别" value={data.root_cause_category ?? '—'} />
          <Field label="检测时间" value={data.detected_at ? data.detected_at.slice(0, 19).replace('T', ' ') : '—'} />
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

        {/* 步骤 3：AI 选行动 */}
        <Step n={3} icon={MousePointerClick} title="AI Selects Pre-approved Recovery Action" subtitle="AI 选择预批准恢复行动">
          <Field label="推荐行动" value={<span className="font-semibold text-blue-700">{data.recommended_action ?? '—'}</span>} highlight />
          <Field label="推荐理由" value={data.recommendation_reason ?? '—'} />
          {recoveryOptions.length > 0 && (
            <div className="pt-1">
              <p className="text-gray-500 mb-1">备选方案</p>
              <div className="flex flex-wrap gap-1.5">
                {recoveryOptions.map((a: string) => (
                  <span key={a} className={`px-2 py-0.5 rounded text-xs ${a === data.recommended_action ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                    {a}
                  </span>
                ))}
              </div>
            </div>
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
