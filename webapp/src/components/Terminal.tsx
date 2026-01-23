import { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';
import 'xterm/css/xterm.css';
import WebContainerService from '../utils/WebContainerService';

interface TerminalProps {
  onReady?: () => void;
}

const Terminal: React.FC<TerminalProps> = ({ onReady }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);

  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    // Initialize xterm
    const term = new XTerm({
      convertEol: true,
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
      }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;

    // Connect to WebContainer shell
    const startShell = async () => {
      try {
        const wc = await WebContainerService.getInstance();
        const shellProcess = await wc.spawn('jsh', {
          terminal: {
            cols: term.cols,
            rows: term.rows,
          },
        });

        // Pipe process output to terminal
        shellProcess.output.pipeTo(
          new WritableStream({
            write(data) {
              term.write(data);
            },
          })
        );

        // Pipe terminal input to process
        const input = shellProcess.input.getWriter();
        term.onData((data) => {
          input.write(data);
        });

        if (onReady) onReady();

        // Handle resize
        window.addEventListener('resize', () => {
          fitAddon.fit();
          shellProcess.resize({
            cols: term.cols,
            rows: term.rows,
          });
        });

      } catch (error) {
        term.write(`\r\n\x1b[31mFailed to start WebContainer shell: ${String(error)}\x1b[0m\r\n`);
        console.error('WebContainer boot error:', error);
      }
    };

    startShell();

    return () => {
      term.dispose();
      xtermRef.current = null;
    };
  }, [onReady]);

  return <div ref={terminalRef} style={{ width: '100%', height: '100%', minHeight: '200px' }} />;
};

export default Terminal;
