import React from "react";

interface SpinnerProps {
    className?: string;
}

/**
 * Simple Tailwind-based spinner . reuse anywhere.
 */
const Spinner: React.FC<SpinnerProps> = ({ className = "" }) => {
    return (
        <div
            className={`h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
        />
    );
};

export default Spinner;
