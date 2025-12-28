import { create } from 'zustand';
import { api } from '../services/api';
import { DashboardInitResponse, AllowedActivity, SubsystemInfo, UserContext } from '../types/dashboard';

interface TransactionState {
    // Dashboard data from /portal/dashboard/init
    dashboardData: DashboardInitResponse | null;
    isLoading: boolean;
    error: string | null;

    // Selected activity for the wizard
    selectedActivity: AllowedActivity | null;

    // Wizard visibility
    showWizard: boolean;

    // Actions
    fetchDashboardInit: () => Promise<void>;
    setActivity: (activity: AllowedActivity | null) => void;
    startWizard: (activity: AllowedActivity) => void;
    closeWizard: () => void;
    reset: () => void;
}

// Selectors for optimized component re-renders
export const selectUserContext = (state: TransactionState) => state.dashboardData?.user_context;
export const selectSubsystem = (state: TransactionState) => state.dashboardData?.subsystem;
export const selectActivities = (state: TransactionState) => state.dashboardData?.allowed_activities ?? [];
export const selectHasSubsystem = (state: TransactionState) => state.dashboardData?.has_subsystem ?? false;
export const selectMessage = (state: TransactionState) => state.dashboardData?.message;

export const useTransactionStore = create<TransactionState>((set, get) => ({
    // Initial state
    dashboardData: null,
    isLoading: false,
    error: null,
    selectedActivity: null,
    showWizard: false,

    // Fetch dashboard initialization data
    fetchDashboardInit: async () => {
        set({ isLoading: true, error: null });
        try {
            const data = await api.get<DashboardInitResponse>('/portal/dashboard/init');
            set({ dashboardData: data, isLoading: false });
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'خطا در بارگذاری داشبورد';
            set({ error: errorMessage, isLoading: false });
        }
    },

    // Set the selected activity
    setActivity: (activity) => {
        set({ selectedActivity: activity });
    },

    // Start wizard with an activity
    startWizard: (activity) => {
        set({ selectedActivity: activity, showWizard: true });
    },

    // Close wizard
    closeWizard: () => {
        set({ showWizard: false, selectedActivity: null });
    },

    // Reset all state
    reset: () => {
        set({
            dashboardData: null,
            isLoading: false,
            error: null,
            selectedActivity: null,
            showWizard: false,
        });
    },
}));

export default useTransactionStore;
