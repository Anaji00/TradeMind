import { useEffect, useState } from "react";

/**
 * Returns a debounced value. The value will only update after `delay`
 * ms have passed without the input changing.
 */

export function useDebounce<T>(value: T, delay = 500): T {
    const [debounced, setDebounced] = useState<T>(value);

    useEffect(() => {
        const id = window.setTimeout(() => {
            setDebounced(value);

        }, delay);

        return () => {
            window.clearTimeout(id);
        };
    }, [value, delay]);

    return debounced;
}