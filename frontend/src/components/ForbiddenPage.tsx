import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldX, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';

/**
 * ForbiddenPage - 403 Forbidden error page
 * Shown when user tries to access a resource they don't have permission for
 */
export function ForbiddenPage() {
    const navigate = useNavigate();

    return (
        <div dir="rtl" className="min-h-screen flex items-center justify-center bg-background p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
                        <ShieldX className="h-8 w-8 text-destructive" />
                    </div>
                    <CardTitle className="text-2xl">دسترسی غیرمجاز</CardTitle>
                    <CardDescription>
                        شما مجوز دسترسی به این صفحه را ندارید
                    </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                    <p className="text-sm text-muted-foreground text-center">
                        لطفاً با مدیر سیستم تماس بگیرید یا به صفحه اصلی بازگردید.
                    </p>
                    <Button onClick={() => navigate(-1)} variant="outline" className="w-full">
                        <ArrowRight className="ml-2 h-4 w-4" />
                        بازگشت به صفحه قبل
                    </Button>
                    <Button onClick={() => navigate('/')} className="w-full">
                        رفتن به صفحه اصلی
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}

export default ForbiddenPage;
