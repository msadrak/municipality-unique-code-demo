import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ChevronsUpDown, Loader2, Plus, User } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Button } from '../ui/button';
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from '../ui/command';
import { cn } from '../ui/utils';
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

/** Maximum items to render in the DOM at once. */
const RENDER_LIMIT = 50;
/** Backend page size for bulk-loading. */
const BULK_PAGE_SIZE = 100;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ContractorSelect({ value, onChange }: ContractorSelectProps) {
    const [open, setOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [allContractors, setAllContractors] = useState<ContractorListItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);

    /* ── Load ALL contractors on first open ─────────────────────────── */

    const loadAll = useCallback(async () => {
        if (loaded || loading) return;
        setLoading(true);
        setError(null);

        try {
            // First request to get total count
            const first = await fetchContractors({ limit: BULK_PAGE_SIZE, page: 1 });
            const total = first.total;
            const all: ContractorListItem[] = [...(first.items ?? [])];

            // Fetch remaining pages in parallel
            if (total > BULK_PAGE_SIZE) {
                const totalPages = Math.ceil(total / BULK_PAGE_SIZE);
                const pagePromises = [];
                for (let p = 2; p <= totalPages; p++) {
                    pagePromises.push(fetchContractors({ limit: BULK_PAGE_SIZE, page: p }));
                }
                const pages = await Promise.all(pagePromises);
                for (const page of pages) {
                    all.push(...(page.items ?? []));
                }
            }

            setAllContractors(all);
            setLoaded(true);
        } catch (err) {
            setError('خطا در دریافت لیست پیمانکاران');
            console.error('[ContractorSelect] Bulk load error:', err);
        } finally {
            setLoading(false);
        }
    }, [loaded, loading]);

    // Trigger load when popover opens
    useEffect(() => {
        if (open && !loaded) {
            loadAll();
        }
    }, [open, loaded, loadAll]);

    /* ── Client-side filtering + slice ─────────────────────────────── */

    const filteredContractors = useMemo(() => {
        if (!searchTerm.trim()) return allContractors.slice(0, RENDER_LIMIT);

        const q = searchTerm.toLowerCase().trim();
        return allContractors
            .filter(
                (c) =>
                    c.company_name.toLowerCase().includes(q) ||
                    c.national_id.includes(q) ||
                    (c.ceo_name && c.ceo_name.toLowerCase().includes(q)),
            )
            .slice(0, RENDER_LIMIT);
    }, [allContractors, searchTerm]);

    /* ── Lookup map for selection ───────────────────────────────────── */

    const contractorMap = useMemo(() => {
        const map = new Map<string, ContractorListItem>();
        for (const c of allContractors) {
            map.set(`${c.company_name} ${c.national_id}`, c);
        }
        return map;
    }, [allContractors]);

    /* ── Handle selection ───────────────────────────────────────────── */

    const handleSelect = (selectedValue: string) => {
        const contractor = contractorMap.get(selectedValue);
        if (contractor) {
            onChange(contractor);
        }
        setOpen(false);
        setSearchTerm('');
    };

    const currentValue = value ? `${value.company_name} ${value.national_id}` : '';

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

            <PopoverContent
                className="w-[--radix-popover-trigger-width] min-w-[360px] p-0"
                align="start"
                sideOffset={4}
            >
                <Command shouldFilter={false}>
                    <CommandInput
                        placeholder="جستجو بر اساس نام یا کد ملی..."
                        value={searchTerm}
                        onValueChange={setSearchTerm}
                    />

                    <CommandList className="max-h-[300px] overflow-y-auto overflow-x-hidden">
                        {/* Loading */}
                        {loading && (
                            <div className="flex items-center justify-center gap-2 py-6">
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                    در حال بارگذاری لیست پیمانکاران...
                                </span>
                            </div>
                        )}

                        {/* Error */}
                        {error && !loading && (
                            <div className="py-6 text-center text-sm text-red-500">{error}</div>
                        )}

                        {/* Empty */}
                        {!loading && !error && filteredContractors.length === 0 && (
                            <CommandEmpty className="text-muted-foreground flex flex-col items-center gap-3 py-8">
                                <span>
                                    {searchTerm.trim()
                                        ? 'پیمانکاری با این مشخصات یافت نشد'
                                        : 'هیچ پیمانکاری در سامانه ثبت نشده است'}
                                </span>
                                <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                                    <Link to="/contractor-auth">
                                        <Plus className="h-3.5 w-3.5" />
                                        ثبت پیمانکار جدید
                                    </Link>
                                </Button>
                            </CommandEmpty>
                        )}

                        {/* Results */}
                        {!loading && !error && filteredContractors.length > 0 && (
                            <CommandGroup>
                                {filteredContractors.map((contractor) => {
                                    const itemValue = `${contractor.company_name} ${contractor.national_id}`;
                                    const isSelected = value?.id === contractor.id;

                                    return (
                                        <CommandItem
                                            key={contractor.id}
                                            value={itemValue}
                                            onSelect={handleSelect}
                                            className="flex items-center gap-3 py-3 cursor-pointer"
                                        >
                                            <Check
                                                className={cn(
                                                    'h-4 w-4 flex-shrink-0',
                                                    isSelected
                                                        ? 'opacity-100 text-green-600'
                                                        : 'opacity-0',
                                                )}
                                            />
                                            <div className="flex-1 min-w-0 space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-sm truncate">
                                                        {contractor.company_name}
                                                    </span>
                                                    {contractor.is_verified && (
                                                        <Badge
                                                            variant="secondary"
                                                            className="text-[10px] px-1.5"
                                                        >
                                                            تایید شده
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span dir="ltr" className="font-mono">
                                                        کد ملی: {contractor.national_id}
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

                        {/* Result count hint */}
                        {!loading && !error && allContractors.length > RENDER_LIMIT && (
                            <div className="py-2 text-center text-xs text-muted-foreground border-t">
                                {searchTerm.trim()
                                    ? `${filteredContractors.length} نتیجه نمایش داده شده`
                                    : `${RENDER_LIMIT} از ${allContractors.length} پیمانکار نمایش داده شده — برای یافتن دقیق، جستجو کنید`}
                            </div>
                        )}
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
}

export default ContractorSelect;
