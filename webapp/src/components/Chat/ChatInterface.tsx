import React, { useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

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
  selectedModel,
  setSelectedModel,
  className
}: ChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        <select 
          value={selectedModel} 
          onChange={(e) => setSelectedModel(e.target.value)}
          className="text-xs bg-background border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="gemini">Gemini</option>
          <option value="deepseek">DeepSeek</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.sender === 'You';
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
                <div className="whitespace-pre-wrap">{msg.text}</div>
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="flex gap-3">
             <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                <Loader2 className="w-5 h-5 animate-spin" />
             </div>
             <div className="bg-muted text-muted-foreground rounded-lg rounded-tl-none p-3 text-sm">
                Thinking...
             </div>
          </div>
        )}
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
