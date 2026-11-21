import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './features/app/App';
import { Workspace } from './features/app/Workspace';
import { isMockMode } from './api/client';
import { installMocks } from './mocks/mock-api';
import './styles.css';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 }, mutations: { retry: false } } });
if (isMockMode()) installMocks();
export function Bootstrap() { return <QueryClientProvider client={queryClient}><ErrorBoundary><div className="min-h-screen bg-paper text-ink" id="app-shell"><App renderWorkspace={(props) => <Workspace {...props}/>} /></div></ErrorBoundary></QueryClientProvider>; }
class ErrorBoundary extends React.Component<React.PropsWithChildren, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main role="alert" className="mx-auto max-w-lg p-10 text-center"><h1 className="text-xl font-semibold">Something went wrong</h1><p className="mt-2 text-sm text-slate-600">The review workspace could not load. Refresh the page to try again.</p><button className="mt-5 rounded-lg bg-forest px-4 py-2 text-white" onClick={() => location.reload()}>Refresh</button></main> : this.props.children; }
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Bootstrap /></React.StrictMode>);
