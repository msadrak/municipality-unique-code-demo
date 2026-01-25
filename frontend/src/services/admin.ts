// Admin-specific services

import { api } from './api';
import type { Transaction, AdminTransactionsResponse } from '../types';

export const adminService = {
    /**
     * Get all transactions for admin review
     */
    async getTransactions(params?: {
        status?: string;
        search?: string;
        page?: number;
        limit?: number;
    }): Promise<AdminTransactionsResponse> {
        return api.get<AdminTransactionsResponse>('/admin/transactions', params);
    },

    /**
     * Get transaction details for review
     */
    async getTransactionDetail(id: number): Promise<Transaction> {
        return api.get<Transaction>(`/admin/transactions/${id}`);
    },

    /**
     * Approve a transaction
     */
    async approveTransaction(id: number): Promise<Transaction> {
        return api.post<Transaction>(`/admin/transactions/${id}/approve`);
    },

    /**
     * Reject a transaction with reason
     */
    async rejectTransaction(id: number, reason: string): Promise<Transaction> {
        return api.post<Transaction>(`/admin/transactions/${id}/reject`, { reason });
    },

    /**
     * Get dashboard statistics
     */
    async getStats(): Promise<{
        total: number;
        pending: number;
        approved: number;
        rejected: number;
        paid: number;
    }> {
        const response = await this.getTransactions({ limit: 1 });
        return response.stats;
    },
};

export default adminService;
