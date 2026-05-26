interface Props {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "發生錯誤，請稍後再試", onRetry }: Props) {
  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <div className="text-4xl">😔</div>
      <p className="text-gray-600">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="px-4 py-2 bg-teal-700 text-white rounded-lg hover:bg-teal-800">
          重試
        </button>
      )}
    </div>
  );
}
