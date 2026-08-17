import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

// 全局错误边界：渲染出错时显示可见错误信息，而不是白屏
class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f9fafb', fontFamily: 'system-ui, sans-serif' }}>
          <div style={{ maxWidth: 640, background: '#fff', border: '1px solid #fecaca', borderRadius: 12, padding: 24, margin: 16 }}>
            <h2 style={{ color: '#b91c1c', margin: '0 0 8px', fontSize: 18 }}>页面渲染出错</h2>
            <p style={{ color: '#7f1d1d', fontSize: 14, wordBreak: 'break-all' }}>{String(this.state.error?.message ?? this.state.error)}</p>
            <button
              onClick={() => { this.setState({ error: null }); }}
              style={{ marginTop: 12, padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
            >
              重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;