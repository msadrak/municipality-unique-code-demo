export interface ContractData {
    contract_number: string;
    contract_date: string;
    guarantee_number: string;
    guarantee_bank: string;
    guarantee_amount: number;
    guarantee_expiry_date: string;
    contract_file_url: string;
    guarantee_file_url: string;
}

export async function fetchContractByNumber(
    contractNumber: string,
): Promise<ContractData> {
    await new Promise((resolve) => setTimeout(resolve, 1000));

    if (contractNumber === '04/14120/s' || contractNumber.includes('14120')) {
        return {
            contract_number: '04/14120/س',
            contract_date: '1404/11/13',
            guarantee_number: '18066904042007000006',
            guarantee_bank: 'تجارت - شعبه جی شرقی',
            guarantee_amount: 9159002711,
            guarantee_expiry_date: '1405/07/16',
            contract_file_url: '/dummy-files/contract-document.pdf',
            guarantee_file_url: '/dummy-files/guarantee-document.pdf',
        };
    }

    throw new Error('قراردادی با این شماره یافت نشد.');
}
