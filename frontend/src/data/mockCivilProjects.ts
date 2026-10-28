export interface CivilProject {
    id: string;
    project_code: string; // The 10-digit code
    title: string;
    zone: string;
}

export const MOCK_CIVIL_PROJECTS: CivilProject[] = [
    { id: '1', project_code: '1031044004', title: 'لکه گیری آسفالت سطح معابر', zone: 'منطقه ۳' },
    { id: '2', project_code: '1141096001', title: 'ایمن سازی رفیوژ میانی زیرگذر لاله و کنار گذر شمال شرق', zone: 'منطقه ۱۴' },
    { id: '3', project_code: '1081012035', title: 'تعریض خیابان شهید سردار خلیفه سلطانی', zone: 'منطقه ۸' },
    { id: '4', project_code: '1051062003', title: 'احداث فانوس نورانی بوستان سعدی', zone: 'منطقه ۵' },
    { id: '5', project_code: '1121063015', title: 'احداث پردیس خانواده محور انتظار خیابان بهارستان غربی', zone: 'منطقه ۱۲' },
    { id: '6', project_code: '1141068008', title: 'تکمیل ساختمان کلانتری محله حصه', zone: 'منطقه ۱۴' },
];
