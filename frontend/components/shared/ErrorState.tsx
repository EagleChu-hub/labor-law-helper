import { RefreshCw, Frown } from "lucide-react";

interface Props {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "發生錯誤，請稍後再試", onRetry }: Props) {
  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <Frown size={40} strokeWidth={1.5} className="text-muted" />
      <p className="text-muted">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 bg-navy text-white rounded-xl hover:bg-navy-800"
        >
          <RefreshCw size={15} /> 重試
        </button>
      )}
    </div>
  );
}
