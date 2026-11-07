import { useEffect, useRef } from 'react';

export default function ConfirmationDialog({
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive = false,
  returnFocusRef,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const onCancelRef = useRef(onCancel);
  const returnFocusRefHolder = useRef(returnFocusRef);

  useEffect(() => {
    onCancelRef.current = onCancel;
  }, [onCancel]);

  useEffect(() => {
    returnFocusRefHolder.current = returnFocusRef;
  }, [returnFocusRef]);

  useEffect(() => {
    const previousActiveElement = returnFocusRefHolder.current?.current || document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        onCancelRef.current();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusable = [...dialogRef.current.querySelectorAll('button:not([disabled])')];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown, true);
      previousActiveElement?.focus?.();
    };
  }, []);

  return (
    <div
      className="confirmation-overlay"
      onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}
    >
      <section
        ref={dialogRef}
        className="confirmation-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmation-title"
        aria-describedby="confirmation-description"
        tabIndex={-1}
      >
        <button ref={closeRef} type="button" className="confirmation-close" onClick={onCancel} aria-label="Close dialog">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
        <h2 id="confirmation-title" className="confirmation-title">{title}</h2>
        <p id="confirmation-description" className="confirmation-description">{description}</p>
        <div className="confirmation-actions acts">
          <button type="button" className="confirmation-cancel" onClick={onCancel}>{cancelLabel}</button>
          <button
            type="button"
            className={`confirmation-confirm${destructive ? ' is-destructive' : ''}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
