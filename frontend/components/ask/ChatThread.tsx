import type { ChatMessage } from "@/types";

interface Props {
  messages: ChatMessage[];
}

export function ChatThread({ messages }: Props) {
  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
              msg.role === "user"
                ? "bg-navy text-white rounded-br-none"
                : "bg-card border border-line text-ink rounded-bl-none shadow-sm"
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
    </div>
  );
}
