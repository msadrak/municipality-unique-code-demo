// Transaction and data services

import { api } from './api';
import type {
    Zone,
    Department,
    Section,
    BudgetItem,
    FinancialEvent,
    CostCenter,
    ContinuousActivity,
    Transaction,
    TransactionCreateRequest,
    SpecialAction
} from '../types';

export const dataService = {
    // ==================== Organization Structure ====================

    /**
     * Get all zones (منطقه/معاونت)
     */
    async getZones(): Promise<Zone[]> {
        return api.get<Zone[]>('/zones/');
    },

    /**
     * Get departments by zone
     */
    async getDepartments(zoneId: number): Promise<Department[]> {
        return api.get<Department[]>('/departments/', { zone_id: zoneId });
    },

    /**
     * Get sections by department
     */
    async getSections(deptId: number): Promise<Section[]> {
        return api.get<Section[]>('/sections/', { dept_id: deptId });
    },

    // ==================== Budget & Financial ====================

    /**
     * Get budget items by zone
     */
    async getBudgetItems(zoneId: number): Promise<BudgetItem[]> {
        return api.get<BudgetItem[]>('/budget-items/', { zone_id: zoneId });
    },

    /**
     * Get all financial events
     */
    async getFinancialEvents(): Promise<FinancialEvent[]> {
        return api.get<FinancialEvent[]>('/financial-events/');
    },

    /**
     * Get all cost centers
     */
    async getCostCenters(): Promise<CostCenter[]> {
        return api.get<CostCenter[]>('/cost-centers/');
    },

    /**
     * Get all continuous activities
     */
    async getContinuousActivities(): Promise<ContinuousActivity[]> {
        return api.get<ContinuousActivity[]>('/continuous-activities/');
    },

    // ==================== Public Data ====================

    /**
     * Get special actions (public dashboard)
     */
    async getSpecialActions(limit: number = 100): Promise<SpecialAction[]> {
        return api.get<SpecialAction[]>('/special-actions/', { limit });
    },

    /**
     * Get account codes (unique codes list)
     */
    async getAccountCodes(limit: number = 100): Promise<any[]> {
        return api.get<any[]>('/account-codes/', { limit });
    },
};

export const transactionService = {
    /**
     * Create a new transaction
     */
    async create(data: TransactionCreateRequest): Promise<Transaction> {
        return api.post<Transaction>('/transactions/', data);
    },

    /**
     * Get user's own transactions
     */
    async getMyTransactions(params?: {
        status?: string;
        page?: number;
        limit?: number;
    }): Promise<{ transactions: Transaction[]; total: number }> {
        return api.get('/transactions/my', params);
    },

    /**
     * Get transaction by ID
     */
    async getById(id: number): Promise<Transaction> {
        return api.get<Transaction>(`/transactions/${id}`);
    },
};

export default { dataService, transactionService };
