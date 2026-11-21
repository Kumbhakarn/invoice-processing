import type { Config } from 'tailwindcss';

export default {
  darkMode: ['class'], content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { ink: '#1c2422', paper: '#f5f5f3', forest: '#176b55', mint: '#e3f2eb', amber: '#9b6814' }, fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] }, boxShadow: { panel: '0 2px 12px rgba(20, 36, 30, .06)' } } },
  plugins: [],
} satisfies Config;
