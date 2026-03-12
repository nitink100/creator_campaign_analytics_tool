import React from 'react';

export default function ConfirmModal({ modal, onClose }) {
    if (!modal) return null;

    const { title, message, onConfirm, confirmText, danger, hideCancel } = modal;

    return (
        <div className="modal-overlay">
            <div className="modal confirm-modal">
                <h3>{title}</h3>
                <p className="confirm-msg">{message}</p>
                <div className="actions">
                    {!hideCancel && (
                        <button className="secondary-btn" onClick={onClose}>
                            Cancel
                        </button>
                    )}
                    <button 
                        className={`primary-btn ${danger ? 'danger-btn' : ''}`}
                        onClick={() => {
                            if (onConfirm) onConfirm();
                            onClose();
                        }}
                    >
                        {confirmText || 'Confirm'}
                    </button>
                </div>
            </div>
        </div>
    );
}
