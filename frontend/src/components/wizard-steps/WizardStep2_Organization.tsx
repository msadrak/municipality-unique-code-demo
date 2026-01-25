import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { TransactionFormData } from '../TransactionWizard';
import { MapPin, Building2, Briefcase, Loader2 } from 'lucide-react';
import { fetchZones, fetchOrgChildren, FigmaOrgUnit } from '../../services/adapters';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep2_Organization({ formData, updateFormData }: Props) {
  const [zones, setZones] = useState<FigmaOrgUnit[]>([]);
  const [availableDepartments, setAvailableDepartments] = useState<FigmaOrgUnit[]>([]);
  const [availableSections, setAvailableSections] = useState<FigmaOrgUnit[]>([]);
  const [loading, setLoading] = useState(true);

  // Load zones from API on component mount
  useEffect(() => {
    const loadZones = async () => {
      try {
        const data = await fetchZones();
        setZones(data);
      } catch (error) {
        console.error('Error loading zones:', error);
      } finally {
        setLoading(false);
      }
    };
    loadZones();
  }, []);

  const handleZoneChange = async (zoneId: string) => {
    const zone = zones.find(z => z.id === parseInt(zoneId));
    if (zone) {
      updateFormData({
        zoneId: zone.id,
        zoneName: zone.name,
        zoneCode: zone.code,
        departmentId: undefined,
        departmentName: undefined,
        departmentCode: undefined,
        sectionId: undefined,
        sectionName: undefined,
        sectionCode: undefined,
      });

      // Load departments for selected zone
      try {
        const data = await fetchOrgChildren(zone.id);
        setAvailableDepartments(data);
      } catch (error) {
        console.error('Error loading departments:', error);
      }
      setAvailableSections([]);
    }
  };

  const handleDepartmentChange = async (deptId: string) => {
    const dept = availableDepartments.find(d => d.id === parseInt(deptId));
    if (dept) {
      updateFormData({
        departmentId: dept.id,
        departmentName: dept.name,
        departmentCode: dept.code,
        sectionId: undefined,
        sectionName: undefined,
        sectionCode: undefined,
      });

      // Load sections for selected department
      try {
        const data = await fetchOrgChildren(dept.id);
        setAvailableSections(data);
      } catch (error) {
        console.error('Error loading sections:', error);
      }
    }
  };

  const handleSectionChange = (sectionId: string) => {
    const section = availableSections.find(s => s.id === parseInt(sectionId));
    if (section) {
      updateFormData({
        sectionId: section.id,
        sectionName: section.name,
        sectionCode: section.code,
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="mr-2">در حال بارگذاری...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3>انتخاب واحد سازمانی</h3>
        <p className="text-sm text-muted-foreground mt-1">
          مسیر سلسله‌مراتبی سازمانی را از منطقه تا قسمت مشخص کنید
        </p>
      </div>

      {/* Progressive Disclosure - Each Selection Unlocks Next Level */}

      {/* Zone/Deputy Selection */}
      <div className="space-y-3">
        <Label htmlFor="zone">منطقه / معاونت</Label>
        <div className="relative">
          <MapPin className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
          <Select
            value={formData.zoneId?.toString()}
            onValueChange={handleZoneChange}
          >
            <SelectTrigger id="zone" className="pr-10">
              <SelectValue placeholder="انتخاب منطقه یا معاونت" />
            </SelectTrigger>
            <SelectContent>
              {zones.map(zone => (
                <SelectItem key={zone.id} value={zone.id.toString()}>
                  {zone.name} (کد: {zone.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Department - Hidden Until Zone Selected */}
      {formData.zoneId && availableDepartments.length > 0 && (
        <div className="space-y-3 animate-in fade-in duration-300">
          <Label htmlFor="department">اداره</Label>
          <div className="relative">
            <Building2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
            <Select
              value={formData.departmentId?.toString()}
              onValueChange={handleDepartmentChange}
            >
              <SelectTrigger id="department" className="pr-10">
                <SelectValue placeholder="انتخاب اداره" />
              </SelectTrigger>
              <SelectContent>
                {availableDepartments.map(dept => (
                  <SelectItem key={dept.id} value={dept.id.toString()}>
                    {dept.name} (کد: {dept.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Section - Hidden Until Department Selected */}
      {formData.departmentId && availableSections.length > 0 && (
        <div className="space-y-3 animate-in fade-in duration-300">
          <Label htmlFor="section">قسمت</Label>
          <div className="relative">
            <Briefcase className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
            <Select
              value={formData.sectionId?.toString()}
              onValueChange={handleSectionChange}
            >
              <SelectTrigger id="section" className="pr-10">
                <SelectValue placeholder="انتخاب قسمت" />
              </SelectTrigger>
              <SelectContent>
                {availableSections.map(section => (
                  <SelectItem key={section.id} value={section.id.toString()}>
                    {section.name} (کد: {section.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Organizational Path Summary */}
      {formData.zoneId && (
        <div className="bg-accent p-4 rounded-lg border border-border space-y-2">
          <p className="text-sm text-muted-foreground">مسیر سازمانی انتخاب شده:</p>
          <div className="flex items-center gap-2 text-sm flex-wrap">
            <span className="bg-primary/10 text-primary px-2 py-1 rounded">
              {formData.zoneName}
            </span>
            {formData.departmentName && (
              <>
                <span className="text-muted-foreground">←</span>
                <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                  {formData.departmentName}
                </span>
              </>
            )}
            {formData.sectionName && (
              <>
                <span className="text-muted-foreground">←</span>
                <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                  {formData.sectionName}
                </span>
              </>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            کد سازمانی: {formData.zoneCode}-{formData.departmentCode || '??'}-{formData.sectionCode || '???'}
          </p>
        </div>
      )}
    </div>
  );
}
