import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const host = 'http://127.0.0.1:4173';
const server = spawn(process.execPath, ['./node_modules/vite/bin/vite.js', '--force', '--host', '127.0.0.1', '--port', '4173', '--strictPort'], {
  env: { ...process.env, VITE_USE_MOCK: 'true' }, stdio: 'inherit',
});
let testProcess;
let exitCode = 1;

try {
  let ready = false;
  for (let attempt = 0; attempt < 200; attempt += 1) {
    if (server.exitCode !== null) throw new Error('Vite exited before becoming ready.');
    try { const response = await fetch(host); if (response.ok) { ready = true; break; } } catch { /* Vite is still starting. */ }
    await sleep(150);
  }
  if (!ready) throw new Error('Timed out waiting for the mock Vite server.');
  testProcess = spawn(process.execPath, ['./node_modules/@playwright/test/cli.js', 'test', ...process.argv.slice(2)], {
    env: { ...process.env, VITE_USE_MOCK: 'true' }, stdio: 'inherit',
  });
  exitCode = await new Promise((resolve, reject) => {
    testProcess.once('error', reject);
    testProcess.once('close', (code, signal) => resolve(signal ? 1 : code ?? 1));
  });
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Could not run the mock browser tests.');
} finally {
  server.kill();
  await Promise.race([new Promise((resolve) => server.once('close', resolve)), sleep(3000)]);
}

process.exitCode = exitCode;
