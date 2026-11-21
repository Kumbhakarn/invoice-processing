import { create } from 'zustand';
import type { Field } from '../model/view-model';

type Snapshot = Record<string, unknown>;
interface UiState {
  selectedPath: string | null; hoveredPath: string | null; page: number; zoom: number; search: string;
  filter: 'all' | 'needs-review' | 'edited' | 'unavailable'; panelSizes: number[]; edits: Record<string, unknown>;
  past: Snapshot[]; future: Snapshot[]; activeCandidates: Record<string, number>;
  select: (path: string | null) => void; hover: (path: string | null) => void; edit: (field: Field, value: unknown) => void;
  revert: (field: Field) => void;
  undo: () => void; redo: () => void; setPage: (page: number) => void; setZoom: (zoom: number) => void;
  setSearch: (search: string) => void; setFilter: (filter: UiState['filter']) => void; setPanelSizes: (sizes: number[]) => void; cycleCandidate: (path: string, direction: number) => void;
  reset: () => void;
}
export const useUiStore = create<UiState>((set) => ({
  selectedPath: null, hoveredPath: null, page: 1, zoom: 1, search: '', filter: 'all', panelSizes: [54, 46], edits: {}, past: [], future: [], activeCandidates: {},
  select: (selectedPath) => set({ selectedPath }), hover: (hoveredPath) => set({ hoveredPath }),
  edit: (field, value) => set((s) => ({ past: [...s.past, s.edits], future: [], edits: { ...s.edits, [field.path]: value } })),
  revert: (field) => set((s) => { if (!(field.path in s.edits)) return s; const edits = { ...s.edits }; delete edits[field.path]; return { past: [...s.past, s.edits], future: [], edits }; }),
  undo: () => set((s) => { const previous = s.past.at(-1); return previous ? { past: s.past.slice(0, -1), future: [s.edits, ...s.future], edits: previous } : s; }),
  redo: () => set((s) => { const next = s.future[0]; return next ? { future: s.future.slice(1), past: [...s.past, s.edits], edits: next } : s; }),
  setPage: (page) => set({ page }), setZoom: (zoom) => set({ zoom: Math.max(0.5, Math.min(2.5, zoom)) }), setSearch: (search) => set({ search }), setFilter: (filter) => set({ filter }), setPanelSizes: (panelSizes) => set({ panelSizes }),
  cycleCandidate: (path, direction) => set((s) => ({ activeCandidates: { ...s.activeCandidates, [path]: Math.max(0, (s.activeCandidates[path] ?? 0) + direction) } })),
  reset: () => set({ selectedPath: null, hoveredPath: null, page: 1, zoom: 1, search: '', filter: 'all', edits: {}, past: [], future: [], activeCandidates: {} }),
}));
