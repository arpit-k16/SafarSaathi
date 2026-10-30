// Isolated build/dev verification using the already installed frontend packages.
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { mkdirSync } from 'node:fs';
const project = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { createServer, build } = await import(pathToFileURL(resolve(project, 'frontend/node_modules/vite/dist/node/index.js')));
const { default: react } = await import(pathToFileURL(resolve(project, 'frontend/node_modules/@vitejs/plugin-react/dist/index.js')));
const mode = process.argv[2] || 'dev';
const root = resolve(project, process.argv[3] || 'frontend');
const output = resolve(project, 'integration_docs/phase2_runtime', mode === 'baseline' ? 'baseline' : 'current');
mkdirSync(output, { recursive: true });
const config = { root, configFile: false, plugins: [react()], cacheDir: resolve(output, 'cache'),
  build: { outDir: resolve(output, 'dist'), emptyOutDir: false },
  server: { host: '127.0.0.1', port: mode === 'baseline' ? 5174 : 5173, strictPort: true } };
if (mode === 'build') await build(config);
else { const server = await createServer(config); await server.listen(); server.printUrls(); }
