import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, rmSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const release = path.join(root, 'release');
const stage = path.join(release, 'stage');
const setupName = 'ReckonGrid-1.0.0-Setup.zip';
const workspaceName = 'ReckonGrid-1.0.0-Workspace.zip';

rmSync(stage, { recursive: true, force: true });
mkdirSync(path.join(stage, 'app'), { recursive: true });
cpSync(path.join(root, 'dist'), path.join(stage, 'app'), { recursive: true });
for (const file of ['ReckonGrid.ps1', 'install.ps1', 'install.sh', 'start.sh', 'Start-ReckonGrid.bat', 'LIESMICH.txt', 'icon.ico']) {
  cpSync(path.join(root, 'installer', file), path.join(stage, file));
}

const setupZip = path.join(release, setupName);
const workspaceZip = path.join(release, workspaceName);
rmSync(setupZip, { force: true });
rmSync(workspaceZip, { force: true });

execFileSync('zip', ['-r', '-q', setupZip, '.'], { cwd: stage });
execFileSync('zip', [
  '-r', '-q', workspaceZip, '.',
  '-x', 'node_modules/*', '-x', '.git/*', '-x', 'dist/*', '-x', 'release/*', '-x', '.vite/*', '-x', 'coverage/*',
], { cwd: root });
rmSync(stage, { recursive: true, force: true });

const mb = (file) => (statSync(file).size / 1024 / 1024).toFixed(2);
console.log(`${setupName} ${mb(setupZip)} MB`);
console.log(`${workspaceName} ${mb(workspaceZip)} MB`);
