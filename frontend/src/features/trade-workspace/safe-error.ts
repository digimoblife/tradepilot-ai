export type SafeErrorContext = "initial" | "wait" | "position";

const messages: Record<SafeErrorContext, string> = {
  initial: "Analisis gagal diproses. Silakan coba lagi.",
  wait: "Permintaan WAIT Update tidak dapat diproses. Silakan coba lagi.",
  position: "Permintaan Position Update tidak dapat diproses. Silakan coba lagi.",
};

export function safeErrorMessage(_error: unknown, context: SafeErrorContext): string {
  return messages[context];
}
