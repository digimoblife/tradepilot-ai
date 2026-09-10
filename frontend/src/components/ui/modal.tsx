import type { ReactNode } from "react";

export interface ModalProps {
  /** Whether the modal is currently visible */
  open: boolean;
  /** Title displayed at the top of the modal */
  title: string;
  /** Called when the user clicks the backdrop or the cancel button */
  onClose: () => void;
  /** Modal body content (form fields, option lists, etc.) */
  children: ReactNode;
}

/**
 * Generic dialog overlay.
 * Wraps the fixed backdrop, centred card, and title — callers provide children.
 *
 * Usage:
 *   <Modal open={showBuyModal} title="🚀 Eksekusi BUY" onClose={() => setShowBuyModal(false)}>
 *     <form>…</form>
 *   </Modal>
 */
export function Modal({ open, title, onClose, children }: ModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-4"
      onClick={(e) => {
        // Close when clicking the backdrop (not the card itself)
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xl space-y-4">
        <h3 className="text-lg sm:text-xl font-bold text-slate-900">{title}</h3>
        {children}
      </div>
    </div>
  );
}
