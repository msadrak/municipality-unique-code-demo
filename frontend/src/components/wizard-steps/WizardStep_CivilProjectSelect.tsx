import React, { useState, useMemo } from 'react';
import { Search, MapPin, Hash } from 'lucide-react';
import { Badge } from '../ui/badge';
import { MOCK_CIVIL_PROJECTS, type CivilProject } from '../../data/mockCivilProjects';
import type { TransactionFormData } from '../TransactionWizard';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
    onNext: () => void;
};

export function WizardStep_CivilProjectSelect({ formData, updateFormData, onNext }: Props) {
    const [searchQuery, setSearchQuery] = useState('');

    // Normalize digits: convert Persian/Arabic numerals to ASCII for matching
    const normalizeDigits = (str: string): string =>
        str.replace(/[۰-۹]/g, (d) => String.fromCharCode(d.charCodeAt(0) - 0x06F0 + 48))
            .replace(/[٠-٩]/g, (d) => String.fromCharCode(d.charCodeAt(0) - 0x0660 + 48));

    const filteredProjects = useMemo(() => {
        if (!searchQuery.trim()) return MOCK_CIVIL_PROJECTS;

        const normalizedQuery = normalizeDigits(searchQuery.trim().toLowerCase());
        return MOCK_CIVIL_PROJECTS.filter((p) => {
            const normalizedCode = normalizeDigits(p.project_code);
            const normalizedTitle = p.title.toLowerCase();
            return normalizedCode.includes(normalizedQuery) || normalizedTitle.includes(normalizedQuery);
        });
    }, [searchQuery]);

    const handleSelect = (project: CivilProject) => {
        updateFormData({
            civilProjectId: project.id,
            civilProjectCode: project.project_code,
            civilProjectTitle: project.title,
            civilProjectZone: project.zone,
        });
        // Auto-advance to next step
        onNext();
    };

    const selectedId = formData.civilProjectId;

    return (
        <div className="space-y-5">
            {/* Header */}
            <div>
                <h3 className="text-lg font-semibold">انتخاب پروژه عمرانی</h3>
                <p className="text-sm text-muted-foreground mt-1">
                    پروژه مورد نظر را از لیست زیر انتخاب کنید یا با استفاده از جستجو، پروژه را پیدا کنید.
                </p>
            </div>

            {/* Search Input */}
            <div className="relative">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none" />
                <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="جستجو بر اساس کد پروژه (مثال: ۱۰۳۱۰۴۴۰۰۴) یا نام پروژه..."
                    className="w-full rounded-lg border border-border bg-background pr-10 pl-4 py-3 text-sm
                     placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2
                     focus:ring-primary/40 focus:border-primary transition-colors"
                    dir="rtl"
                />
            </div>

            {/* Project Cards Grid */}
            {filteredProjects.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                    <Search className="h-10 w-10 mx-auto mb-3 opacity-40" />
                    <p className="text-sm">پروژه‌ای با این عبارت یافت نشد.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[420px] overflow-y-auto pr-1">
                    {filteredProjects.map((project) => {
                        const isSelected = selectedId === project.id;

                        return (
                            <button
                                key={project.id}
                                onClick={() => handleSelect(project)}
                                className={`
                  text-right p-4 rounded-xl border-2 transition-all duration-150
                  hover:shadow-md hover:border-primary/50 group cursor-pointer
                  ${isSelected
                                        ? 'border-primary bg-primary/10 shadow-lg ring-2 ring-primary/20'
                                        : 'border-border bg-card hover:bg-accent/50'
                                    }
                `}
                            >
                                {/* Project Title */}
                                <p className={`font-medium text-sm leading-relaxed mb-3 line-clamp-2 ${isSelected ? 'text-primary' : 'text-foreground'
                                    }`}>
                                    {project.title}
                                </p>

                                {/* Footer: Code + Zone */}
                                <div className="flex items-center justify-between gap-2">
                                    <Badge
                                        variant={isSelected ? 'default' : 'secondary'}
                                        className="font-mono-num text-xs tracking-wide"
                                    >
                                        <Hash className="h-3 w-3" />
                                        {project.project_code}
                                    </Badge>

                                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                        <MapPin className="h-3 w-3" />
                                        {project.zone}
                                    </span>
                                </div>
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
