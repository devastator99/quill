import { Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '@/styles/theme';

export default function TabLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen
        name="chat"
        options={{
          title: 'Chat',
        }}
      />
      <Stack.Screen
        name="profile"
        options={{
          title: 'Profile',
        }}
      />
    </Stack>
  );
}