import { WebContainer } from '@webcontainer/api';
import type { FileSystemTree } from '@webcontainer/api';

class WebContainerService {
  private static instance: WebContainer | null = null;
  private static bootPromise: Promise<WebContainer> | null = null;

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
    const process = await instance.spawn(command, args);
    
    if (outputCallback) {
      process.output.pipeTo(new WritableStream({
        write(data) {
          outputCallback(data);
        }
      }));
    }

    return process.exit;
  }
}

export default WebContainerService;
