import { Component, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * FIX-010: ErrorBoundary to catch runtime errors and prevent full app crash.
 * Shows fallback UI when a child component throws.
 */
export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false, error: null };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('[ErrorBoundary] Caught error:', error, errorInfo);
    }

    handleReload = () => {
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-8">
                    <div className="max-w-md text-center">
                        <div className="text-6xl mb-4">💥</div>
                        <h1 className="text-2xl font-bold text-white mb-2">
                            Что-то пошло не так
                        </h1>
                        <p className="text-zinc-400 mb-6">
                            Произошла непредвиденная ошибка. Попробуйте перезагрузить страницу.
                        </p>
                        {this.state.error && (
                            <details className="mb-6 text-left">
                                <summary className="text-zinc-500 cursor-pointer hover:text-zinc-300 text-sm">
                                    Техническая информация
                                </summary>
                                <pre className="mt-2 p-3 bg-zinc-900 rounded-lg text-xs text-red-400 overflow-auto">
                                    {this.state.error.message}
                                </pre>
                            </details>
                        )}
                        <button
                            onClick={this.handleReload}
                            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors"
                        >
                            Перезагрузить
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
