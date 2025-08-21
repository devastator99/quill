import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator, Text } from 'react-native';
import { useRouter } from 'expo-router';
import { storage, STORAGE_KEYS } from '@/utils/storage';
import { colors, commonStyles } from '@/styles/theme';

export default function IndexScreen() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [redirect, setRedirect] = useState<string | null>(null);

  useEffect(() => {
    checkAppState();
  }, []);

  const checkAppState = async () => {
    try {
      const hasSeenOnboarding = await storage.getBool(STORAGE_KEYS.HAS_SEEN_ONBOARDING);
      const userToken = await storage.getItem(STORAGE_KEYS.USER_TOKEN);

      if (!hasSeenOnboarding) {
        // console.log('Redirecting to onboarding');
        setRedirect('/(onboarding)');
        router.replace('/(onboarding)');
      } else if (!userToken) {
        // console.log('Redirecting to login');
        setRedirect('/(auth)/login');
        router.replace('/(auth)/login');
      } else {
        // console.log('Redirecting to books');
        setRedirect('/(main)/(drawer)/books');
        router.replace('/(main)/(drawer)/books');
      }
    } catch (err) {
      // console.error('Error checking app state:', err);
      setError('Error checking app state: ' + (err instanceof Error ? err.message : String(err)));
      setRedirect('/(onboarding)');
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

  if (error) {
    return (
      <View style={commonStyles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <View style={{ marginTop: 20 }}>
          <Text style={{ color: 'red', textAlign: 'center' }}>{error}</Text>
        </View>
      </View>
    );
  }

  if (redirect) {
    return (
      <View style={commonStyles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <View style={{ marginTop: 20 }}>
          <Text style={{ color: colors.primary, textAlign: 'center' }}>Redirecting to: {redirect}</Text>
        </View>
      </View>
    );
  }

  return null;
}


