export interface CivilCreditInfo {
  credit_form_number: string;
  project_code: string;
  budget_row_code: string;
  budget_row_title: string;
  estimated_amount: number;
}

export async function fetchCivilCreditByNumber(
  formNumber: string,
  currentProjectCode: string,
): Promise<CivilCreditInfo> {
  await new Promise((resolve) => setTimeout(resolve, 1000));

  if (formNumber === '404150248') {
    return {
      credit_form_number: formNumber,
      project_code: currentProjectCode,
      budget_row_code: '150248',
      budget_row_title: 'ساماندهی معابر اصلی محله',
      estimated_amount: 183180054207,
    };
  }

  throw new Error(
    'فرم تامین اعتباری با این شماره یافت نشد یا متعلق به این پروژه نیست.',
  );
}
