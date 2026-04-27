import api from './api';

export interface NotificationItem {
  id: number;
  user_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

export async function fetchUnreadNotifications(): Promise<NotificationItem[]> {
  return api.get<NotificationItem[]>('/api/notifications');
}

export async function markNotificationRead(notificationId: number): Promise<NotificationItem> {
  return api.patch<NotificationItem>(`/api/notifications/${notificationId}/read`, {});
}
