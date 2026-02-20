import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Check, ChevronsUpDown, Loader2, Search, User } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from '../ui/command';
import { Badge } from '../ui/badge';
import { fetchContractors, type ContractorListItem } from '../../services/contracts';

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

type ContractorSelectProps = {
    /** Currently selected contractor (controlled). */
    value: ContractorListItem | null;
    /** Fires when the user picks a contractor. */
    onChange: (contractor: ContractorListItem) => void;
};

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const DEBOUNCE_MS = 300;
const PAGE_LIMIT = 50;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ContractorSelect({ value, onChange }: ContractorSelectProps) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<ContractorListItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [initialLoaded, setInitialLoaded] = useState(false);

    // Ref to track the latest request and ignore stale responses
    const latestRequestRef = useRef(0);

    /* ── Debounced fetch ────────────────────────────────────────────── */

    const fetchResults = useCallback(async (searchTerm: string) => {
        const requestId = ++latestRequestRef.current;
        setLoading(true);
        setError(null);

        try {
            const response = await fetchContractors({
                search: searchTerm || undefined,
                limit: PAGE_LIMIT,
            });

            // Ignore stale responses
            if (requestId !== latestRequestRef.current) return;

            setResults(response.items ?? []);
        } catch (err) {
            if (requestId !== latestRequestRef.current) return;
            setError('خطا در دریافت لیست پیمانکاران');
            console.error('[ContractorSelect] Fetch error:', err);
        } finally {
            if (requestId === latestRequestRef.current) {
                setLoading(false);
            }
        }
    }, []);

    // Load initial results when popover opens for the first time
    useEffect(() => {
        if (open && !initialLoaded) {
            fetchResults('');
            setInitialLoaded(true);
        }
    }, [open, initialLoaded, fetchResults]);

    // Debounced search when query changes
    useEffect(() => {
        if (!open) return;

        const timer = setTimeout(() => {
            fetchResults(query);
        }, DEBOUNCE_MS);

        return () => clearTimeout(timer);
    }, [query, open, fetchResults]);

    /* ── Handle selection ───────────────────────────────────────────── */

    const handleSelect = (contractor: ContractorListItem) => {
        onChange(contractor);
        setOpen(false);
        setQuery('');
    };

    /* ── Render ─────────────────────────────────────────────────────── */

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <button
                    type="button"
                    role="combobox"
                    aria-expanded={open}
                    className="w-full inline-flex items-center justify-between text-right h-auto min-h-[44px] bg-white border rounded-md px-4 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                    {value ? (
                        <div className="flex items-center gap-2 min-w-0">
                            <User className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                            <span className="truncate font-medium">{value.company_name}</span>
                            <Badge variant="secondary" className="text-xs flex-shrink-0">
                                {value.national_id}
                            </Badge>
                        </div>
                    ) : (
                        <span className="text-muted-foreground">انتخاب پیمانکار...</span>
                    )}
                    <ChevronsUpDown className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                </button>
            </PopoverTrigger>

            <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                <Command shouldFilter={false}>
                    <CommandInput
                        placeholder="جستجو بر اساس نام یا کد ملی..."
                        value={query}
                        onValueChange={setQuery}
                    />

                    <CommandList className="max-h-[320px]">
                        {/* Loading state */}
                        {loading && (
                            <div className="flex items-center justify-center gap-2 py-6">
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">در حال جستجو...</span>
                            </div>
                        )}

                        {/* Error state */}
                        {error && !loading && (
                            <div className="py-6 text-center text-sm text-red-500">
                                {error}
                            </div>
                        )}

                        {/* Empty state */}
                        {!loading && !error && results.length === 0 && (
                            <CommandEmpty>
                                {query.trim()
                                    ? 'پیمانکاری یافت نشد'
                                    : 'برای جستجو تایپ کنید...'}
                            </CommandEmpty>
                        )}

                        {/* Results */}
                        {!loading && !error && results.length > 0 && (
                            <CommandGroup>
                                {results.map((contractor) => {
                                    const isSelected = value?.id === contractor.id;
                                    return (
                                        <CommandItem
                                            key={contractor.id}
                                            value={String(contractor.id)}
                                            onSelect={() => handleSelect(contractor)}
                                            className="flex items-center gap-3 py-3 cursor-pointer"
                                        >
                                            <Check
                                                className={`h-4 w-4 flex-shrink-0 ${isSelected ? 'opacity-100 text-green-600' : 'opacity-0'
                                                    }`}
                                            />
                                            <div className="flex-1 min-w-0 space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-sm truncate">
                                                        {contractor.company_name}
                                                    </span>
                                                    {contractor.is_verified && (
                                                        <Badge variant="secondary" className="text-[10px] px-1.5">
                                                            تایید شده
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span dir="ltr" className="font-mono">
                                                        {contractor.national_id}
                                                    </span>
                                                    {contractor.ceo_name && (
                                                        <span>• {contractor.ceo_name}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </CommandItem>
                                    );
                                })}
                            </CommandGroup>
                        )}
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
}

export default ContractorSelect;
