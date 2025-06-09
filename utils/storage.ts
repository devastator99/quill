import AsyncStorage from '@react-native-async-storage/async-storage';

export const STORAGE_KEYS = {
  HAS_SEEN_ONBOARDING: 'has_seen_onboarding',
  USER_TOKEN: 'user_token',
  USER_DATA: 'user_data',
};

export const storage = {
  async setItem(key: string, value: string) {
    try {
      await AsyncStorage.setItem(key, value);
    } catch (error) {
      console.error('Storage setItem error:', error);
    }
  },

  async getItem(key: string): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(key);
    } catch (error) {
      console.error('Storage getItem error:', error);
      return null;
    }
  },

  async removeItem(key: string) {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error('Storage removeItem error:', error);
    }
  },

  async setBool(key: string, value: boolean) {
    await this.setItem(key, JSON.stringify(value));
  },

  async getBool(key: string): Promise<boolean> {
    const value = await this.getItem(key);
    return value ? JSON.parse(value) : false;
  },
};