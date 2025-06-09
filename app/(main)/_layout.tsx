import { Stack } from 'expo-router';

export default function MainLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen 
        name="purchase-premium" 
        options={{ 
          presentation: 'modal',
          gestureEnabled: true,
        }} 
      />
    </Stack>
  );
}