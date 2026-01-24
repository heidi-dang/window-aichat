import { WebContainer } from '@webcontainer/api';
import type { FileSystemTree } from '@webcontainer/api';
import * as api from '../api/routes';

type WebContainerProcess = { output: ReadableStream<string>; exit: Promise<number> };
type SpawnOptions = { cwd?: string };

class WebContainerService {
  private static instance: WebContainer | null = null;
  private static bootPromise: Promise<WebContainer> | null = null;
  private static webappMounted = false;
  private static webappDepsInstalled = false;

  static async getInstance(): Promise<WebContainer> {
    if (this.instance) return this.instance;
    
    if (!this.bootPromise) {
      this.bootPromise = WebContainer.boot();
    }
    
    this.instance = await this.bootPromise;
    return this.instance;
  }

  static async mount(files: FileSystemTree) {
    const instance = await this.getInstance();
    await instance.mount(files);
  }

  static async writeFile(path: string, content: string) {
    const instance = await this.getInstance();
    await instance.fs.writeFile(path, content);
  }

  static async readFile(path: string): Promise<string> {
    const instance = await this.getInstance();
    const content = await instance.fs.readFile(path, 'utf-8');
    return content;
  }

  static async runCommand(command: string, args: string[] = [], outputCallback?: (data: string) => void) {
    const instance = await this.getInstance();
    const spawn = instance.spawn as unknown as (cmd: string, argv?: string[], options?: SpawnOptions) => Promise<WebContainerProcess>;
    const process = await spawn(command, args);
    
    if (outputCallback) {
      process.output.pipeTo(new WritableStream({
        write(data) {
          outputCallback(data);
        }
      }));
    }

    return process.exit;
  }

  private static setTreeFile(tree: FileSystemTree, pathParts: string[], contents: string) {
    let cursor = tree as unknown as Record<string, unknown>;
    for (let i = 0; i < pathParts.length; i++) {
      const part = pathParts[i];
      const isLast = i === pathParts.length - 1;
      if (isLast) {
        cursor[part] = { file: { contents } } as unknown;
        return;
      }
      const current = cursor[part];
      if (!current || typeof current !== 'object' || !('directory' in current)) {
        cursor[part] = { directory: {} } as unknown;
      }
      const next = cursor[part] as { directory?: unknown };
      cursor = (next.directory ?? {}) as Record<string, unknown>;
    }
  }

  static async mountWebappFromBackend(outputCallback?: (data: string) => void) {
    if (this.webappMounted) return;
    outputCallback?.('Preparing WebContainer filesystem...\n');

    const entries = await api.listFiles();
    const webappFiles = entries.filter((e) => e.type === 'file' && e.path.replace(/\\/g, '/').startsWith('webapp/'));

    const tree: FileSystemTree = {};

    for (const entry of webappFiles) {
      const rel = entry.path.replace(/\\/g, '/');
      const parts = rel.split('/').filter(Boolean);
      if (parts.includes('node_modules')) continue;
      try {
        const data = await api.readFile(rel);
        this.setTreeFile(tree, parts, data.content);
      } catch {
        this.setTreeFile(tree, parts, '');
      }
    }

    await this.mount(tree);
    this.webappMounted = true;
    outputCallback?.('WebContainer filesystem ready.\n');
  }

  static async ensureWebappDependencies(outputCallback?: (data: string) => void) {
    if (this.webappDepsInstalled) return;
    outputCallback?.('Installing webapp dependencies...\n');
    const instance = await this.getInstance();
    const spawn = instance.spawn as unknown as (cmd: string, argv?: string[], options?: SpawnOptions) => Promise<WebContainerProcess>;
    const process = await spawn('npm', ['install'], { cwd: '/webapp' });
    if (outputCallback) {
      process.output.pipeTo(new WritableStream({
        write(data) {
          outputCallback(data);
        }
      }));
    }
    const code = await process.exit;
    if (code !== 0) {
      throw new Error(`npm install failed with exit code ${code}`);
    }
    this.webappDepsInstalled = true;
  }

  static async runWebappTests(outputCallback?: (data: string) => void) {
    await this.mountWebappFromBackend(outputCallback);
    await this.ensureWebappDependencies(outputCallback);
    outputCallback?.('Running webapp tests...\n');
    const instance = await this.getInstance();
    const spawn = instance.spawn as unknown as (cmd: string, argv?: string[], options?: SpawnOptions) => Promise<WebContainerProcess>;
    const process = await spawn('npm', ['test'], { cwd: '/webapp' });
    if (outputCallback) {
      process.output.pipeTo(new WritableStream({
        write(data) {
          outputCallback(data);
        }
      }));
    }
    const code = await process.exit;
    return code as number;
  }
}

export default WebContainerService;
