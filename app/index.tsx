import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { storage, STORAGE_KEYS } from '@/utils/storage';
import { colors, commonStyles } from '@/styles/theme';

export default function IndexScreen() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAppState();
  }, []);

  const checkAppState = async () => {
    try {
      const hasSeenOnboarding = await storage.getBool(STORAGE_KEYS.HAS_SEEN_ONBOARDING);
      const userToken = await storage.getItem(STORAGE_KEYS.USER_TOKEN);

      if (!hasSeenOnboarding) {
        router.replace('/(onboarding)');
      } else if (!userToken) {
        router.replace('/(auth)/login');
      } else {
        router.replace('/(main)/(tabs)/chat');
      }
    } catch (error) {
      console.error('Error checking app state:', error);
      router.replace('/(onboarding)');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={commonStyles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return null;
}