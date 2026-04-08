import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { ArrowUp, Compass, Sparkles, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { TopBar } from '../components/TopBar';
import { sendMessage, type ChatResponse } from '../lib/api';
import { generateSessionId } from '../lib/utils';
import { toast } from '../components/Toast';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatResponse['sources'];
  suggestion?: string | null;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => generateSessionId());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const res = await sendMessage(question, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          suggestion: res.suggestion,
        },
      ]);
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to get response', 'error');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const suggestions = [
    'What is the onboarding process?',
    'Summarize our services',
    'What decisions have we made?',
  ];

  return (
    <>
      <TopBar title="Chat" />
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Messages area */}
        <section className="flex-1 pt-8 pb-8 px-6">
          <div className="max-w-[780px] mx-auto space-y-8">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-6">
                <div className="w-16 h-16 rounded-2xl bg-surface-high flex items-center justify-center shadow-2xl">
                  <Sparkles size={28} className="text-primary" />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight text-on-surface mb-2">
                    What would you like to know about your company?
                  </h2>
                  <p className="text-on-surface-muted max-w-md mx-auto text-sm leading-relaxed">
                    Access your indexed knowledge base through natural language.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-3">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setInput(s);
                        textareaRef.current?.focus();
                      }}
                      className="bg-secondary-container/20 text-secondary border border-secondary/20 px-4 py-2 rounded-full text-xs font-label hover:bg-secondary-container/40 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) =>
              msg.role === 'user' ? (
                <div key={i} className="flex flex-col items-end gap-1">
                  <div className="bg-primary-container/10 border border-primary/20 px-4 py-3 rounded-xl rounded-tr-none max-w-[80%]">
                    <p className="text-sm text-on-surface leading-relaxed">{msg.content}</p>
                  </div>
                </div>
              ) : (
                <div key={i} className="flex flex-col items-start gap-3">
                  <div className="flex items-center gap-2 ml-1">
                    <div className="w-6 h-6 rounded bg-primary-container flex items-center justify-center">
                      <Compass size={12} className="text-white" />
                    </div>
                    <span className="text-[10px] font-label font-medium uppercase tracking-widest text-on-surface-muted">
                      Compass Intelligence
                    </span>
                  </div>
                  <div className="bg-surface border border-outline/10 p-5 rounded-xl rounded-tl-none max-w-[90%]">
                    <div className="chat-prose text-sm leading-relaxed text-on-surface-dim">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-5 pt-4 border-t border-outline/5">
                        <p className="text-[10px] font-label uppercase tracking-wider text-on-surface-muted mb-3">
                          Retrieved Sources
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {msg.sources.map((src, j) => (
                            <div
                              key={j}
                              className="flex items-center gap-1.5 px-2 py-1 bg-surface-highest rounded text-[11px] text-on-surface-dim border border-outline/10"
                            >
                              <FileText size={12} />
                              {src.doc_name}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {msg.suggestion && (
                      <div className="mt-5 p-3 border border-secondary/20 bg-secondary-container/5 rounded-lg">
                        <p className="text-[10px] font-label text-secondary uppercase mb-1">
                          Suggestion
                        </p>
                        <p className="text-xs text-on-surface">{msg.suggestion}</p>
                      </div>
                    )}
                  </div>
                </div>
              )
            )}

            {loading && (
              <div className="flex items-start gap-3">
                <div className="flex items-center gap-2 ml-1">
                  <div className="w-6 h-6 rounded bg-primary-container flex items-center justify-center">
                    <Compass size={12} className="text-white" />
                  </div>
                </div>
                <div className="bg-surface border border-outline/10 px-5 py-4 rounded-xl rounded-tl-none">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse [animation-delay:0.2s]" />
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </section>

        {/* Input area */}
        <section className="sticky bottom-0 p-6 backdrop-blur-xl bg-void/80 border-t border-outline/10">
          <div className="max-w-[780px] mx-auto">
            <div className="bg-surface rounded-xl shadow-2xl border border-outline/20 focus-within:border-primary/40 transition-colors duration-300">
              <div className="p-2 flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message Compass..."
                  rows={1}
                  className="flex-grow bg-transparent border-none focus:outline-none text-on-surface text-sm py-2 px-3 resize-none placeholder:text-on-surface-muted/50"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-95 ${
                    input.trim()
                      ? 'bg-primary text-background shadow-lg shadow-primary/20 hover:scale-105'
                      : 'bg-surface-high text-on-surface-muted cursor-not-allowed'
                  }`}
                >
                  <ArrowUp size={18} />
                </button>
              </div>
            </div>
            <div className="mt-3 flex justify-between items-center px-1">
              <div className="flex items-center gap-4">
                <p className="font-label text-[10px] text-on-surface-muted/60 tracking-wider">
                  SESSION: <span className="text-on-surface-dim font-medium">{sessionId}</span>
                </p>
                <p className="font-label text-[10px] text-on-surface-muted/60 tracking-wider">
                  MESSAGES: <span className="text-on-surface-dim font-medium">{messages.length}</span>
                </p>
              </div>
              <p className="font-label text-[10px] text-on-surface-muted/40">
                SHIFT + ENTER FOR NEW LINE
              </p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
