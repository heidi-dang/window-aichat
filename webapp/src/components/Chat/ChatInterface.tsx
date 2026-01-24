import React, { useRef, useEffect, useState } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { cn } from '../../lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  sender: string;
  text: string;
  timestamp: string;
}

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  input: string;
  setInput: (val: string) => void;
  onSend: () => void;
  onCancel?: () => void;
  onRegenerate?: () => void;
  canRegenerate?: boolean;
  contextPack?: {
    id: string;
    totalScore: number;
    items: Array<{
      title: string;
      score: number;
      reason: Record<string, unknown>;
      source: { type: string; ref?: string };
    }>;
  } | null;
  selectedModel: string;
  setSelectedModel: (val: string) => void;
  className?: string;
}

export const ChatInterface = React.memo(function ChatInterface({
  messages,
  isLoading,
  input,
  setInput,
  onSend,
  onCancel,
  onRegenerate,
  canRegenerate,
  contextPack,
  selectedModel,
  setSelectedModel,
  className
}: ChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showContext, setShowContext] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className={cn("flex flex-col h-full bg-card border-l border-border", className)}>
      <div className="p-4 border-b border-border flex items-center justify-between bg-muted/10">
        <h3 className="font-semibold text-sm">AI Assistant</h3>
        <div className="flex items-center gap-2">
          {contextPack && (
            <button
              onClick={() => setShowContext((v) => !v)}
              className="text-xs bg-background border border-border rounded px-2 py-1 hover:bg-muted/40"
            >
              Context
            </button>
          )}
          {onCancel && isLoading && (
            <button
              onClick={onCancel}
              className="text-xs bg-background border border-border rounded px-2 py-1 hover:bg-muted/40"
            >
              Cancel
            </button>
          )}
          {onRegenerate && canRegenerate && !isLoading && (
            <button
              onClick={onRegenerate}
              className="text-xs bg-background border border-border rounded px-2 py-1 hover:bg-muted/40"
            >
              Regenerate
            </button>
          )}
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="text-xs bg-background border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="gemini">Gemini</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </div>
      </div>

      {showContext && contextPack && (
        <div className="border-b border-border bg-background/50 px-4 py-3">
          <div className="text-[11px] text-muted-foreground mb-2">
            Context pack {contextPack.id} • Score {contextPack.totalScore.toFixed(2)}
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {contextPack.items.map((item, i) => (
              <div key={`${contextPack.id}-${i}`} className="text-xs border border-border rounded p-2 bg-muted/30">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium truncate">{item.title}</div>
                  <div className="text-[10px] opacity-70 shrink-0">{item.score.toFixed(2)}</div>
                </div>
                <div className="text-[10px] text-muted-foreground mt-1 truncate">
                  {item.source.type}{item.source.ref ? `: ${item.source.ref}` : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.sender === 'You';
          const isStreamingPlaceholder = !isUser && isLoading && idx === messages.length - 1 && !msg.text.trim();
          const shouldRenderMarkdown = !isUser && msg.sender !== 'System' && !isStreamingPlaceholder;
          return (
            <div key={idx} className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                isUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
              )}>
                {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              <div className={cn(
                "max-w-[85%] rounded-lg p-3 text-sm leading-relaxed",
                isUser 
                  ? "bg-primary text-primary-foreground rounded-tr-none" 
                  : "bg-muted text-muted-foreground rounded-tl-none"
              )}>
                <div className="flex items-center justify-between gap-4 mb-1 opacity-70 text-[10px]">
                  <span>{msg.sender}</span>
                  <span>{msg.timestamp}</span>
                </div>
                {isStreamingPlaceholder ? (
                  <div className="flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.2s]" />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.1s]" />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-current animate-bounce" />
                  </div>
                ) : shouldRenderMarkdown ? (
                  <div className="prose prose-invert max-w-none prose-pre:bg-black/30 prose-pre:border prose-pre:border-border prose-pre:rounded-md prose-code:before:content-[''] prose-code:after:content-['']">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{msg.text}</div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-border bg-background">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="w-full bg-muted/50 border border-border rounded-lg pl-3 pr-10 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none min-h-[44px] max-h-[120px]"
            rows={1}
          />
          <button 
            onClick={onSend}
            disabled={isLoading || !input.trim()}
            className="absolute right-2 bottom-2 p-1.5 bg-primary text-primary-foreground rounded-md hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <div className="text-[10px] text-muted-foreground mt-2 text-center">
          Shift+Enter for new line
        </div>
      </div>
    </div>
  );
});
