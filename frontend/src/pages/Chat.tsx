import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Bot, User, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type ChatMessage } from "@/integrations/api/client";
import { toast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";

export default function Chat() {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [optimisticMsgs, setOptimisticMsgs] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: messages = [] } = useQuery({
    queryKey: ["chat-messages"],
    queryFn: api.getChatMessages,
  });

  const allMessages = [...messages, ...optimisticMsgs];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allMessages, pending]);

  const send = async () => {
    const text = input.trim();
    if (!text || pending) return;
    setInput("");
    setPending(true);

    const tempUserMsg: ChatMessage = {
      id: `tmp-${Date.now()}`,
      user_id: "",
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setOptimisticMsgs([tempUserMsg]);

    try {
      const { user_message, assistant_message } = await api.sendChatMessage(text);
      setOptimisticMsgs([]);
      await queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
      // Also invalidate financial data since agent may have written transactions
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["budget-goals"] });
    } catch (err: any) {
      setOptimisticMsgs([]);
      toast({ variant: "destructive", title: "Erro", description: err.message });
    } finally {
      setPending(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="glass border-b border-border px-4 py-3 flex items-center gap-3">
        <div className="h-9 w-9 rounded-full gradient-primary flex items-center justify-center">
          <Bot className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="font-semibold text-sm">Chat IA Financeiro</h1>
          <p className="text-xs text-muted-foreground">Pergunte sobre seus gastos ou registre transações</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {allMessages.length === 0 && !pending && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center animate-fade-in">
            <div className="h-16 w-16 rounded-full gradient-primary flex items-center justify-center animate-pulse-glow">
              <Bot className="h-8 w-8 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">Olá! Sou seu assistente financeiro</h2>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                Me diga seus gastos, pergunte sobre seus saldos ou defina metas. Posso ajudar com tudo isso!
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-left max-w-sm">
              {[
                "Gastei R$50 no mercado hoje",
                "Quanto gastei esse mês?",
                "Recebi meu salário de R$3000",
                "Qual minha situação financeira?",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="glass rounded-lg px-3 py-2 hover:border-primary/40 transition-colors text-left"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {allMessages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {pending && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full gradient-primary flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="glass rounded-xl px-4 py-3 flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Analisando</span>
              <span className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="glass border-t border-border px-4 py-3">
        <div className="flex gap-2 items-end max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Digite sua mensagem... (Enter para enviar)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring min-h-[40px] max-h-32"
            style={{ scrollbarWidth: "thin" }}
          />
          <Button
            size="icon"
            onClick={send}
            disabled={!input.trim() || pending}
            className="shrink-0 h-10 w-10 rounded-xl"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
          isUser ? "bg-primary" : "gradient-primary",
        )}
      >
        {isUser ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-white" />}
      </div>
      <div
        className={cn(
          "max-w-[75%] rounded-xl px-4 py-3 text-sm animate-fade-in",
          isUser ? "bg-primary text-primary-foreground" : "glass",
        )}
      >
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <ReactMarkdown
            className="prose prose-sm prose-invert max-w-none"
            components={{
              p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="ml-4 list-disc space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="ml-4 list-decimal space-y-0.5">{children}</ol>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            }}
          >
            {msg.content}
          </ReactMarkdown>
        )}
        <p className="text-[10px] text-muted-foreground mt-1.5">
          {new Date(msg.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}
