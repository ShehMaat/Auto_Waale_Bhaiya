export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  // Safe filtering: ensure we never display stack traces or raw SQL.
  const safeMessage = message.includes("Traceback") || message.includes("SELECT") || message.includes("500") 
    ? "An unexpected system error occurred. Please try again later."
    : message;

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-red-50 border border-red-200 rounded-lg max-w-2xl mx-auto my-8 text-center">
      <svg className="w-10 h-10 text-red-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <h3 className="text-lg font-semibold text-red-800">Something went wrong</h3>
      <p className="mt-2 text-sm text-red-600 mb-6">{safeMessage}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-800 font-medium rounded-md transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
