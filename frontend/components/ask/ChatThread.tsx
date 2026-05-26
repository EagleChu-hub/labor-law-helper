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
                ? "bg-teal-700 text-white rounded-br-none"
                : "bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm"
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
    </div>
  );
}
