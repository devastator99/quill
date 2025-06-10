import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Drawer } from 'expo-router/drawer';
import { StyleSheet } from 'react-native';
import { BookOpen, Info } from 'lucide-react-native';

export default function DrawerLayout() {
  return (
    <GestureHandlerRootView style={styles.container}>
      <Drawer
        screenOptions={{
          headerStyle: {
            backgroundColor: '#1f2937',
          },
          headerTintColor: '#ffffff',
          headerTitleStyle: {
            fontWeight: '600',
            fontSize: 18,
          },
          drawerStyle: {
            backgroundColor: '#f9fafb',
            width: 280,
          },
          drawerActiveTintColor: '#3b82f6',
          drawerInactiveTintColor: '#6b7280',
          drawerLabelStyle: {
            fontWeight: '500',
            fontSize: 16,
          },
        }}>
        <Drawer.Screen
          name="books"
          options={{
            drawerLabel: 'Book Catalog',
            title: 'Book Catalog',
            drawerIcon: ({ size, color }: { size: number, color: string }) => (
              <BookOpen size={size} color={color} />
            ),
          }}
        />
        <Drawer.Screen
          name="chat"
          options={{
            drawerLabel: 'Chat',
            headerShown: false,
            title: 'Chat',
            drawerIcon: ({ size, color }: { size: number, color: string }) => (
              <Info size={size} color={color} />
            ),
          }}
        />
        <Drawer.Screen
          name="about"
          options={{
            drawerLabel: 'About',
            title: 'About',
            drawerIcon: ({ size, color }: { size: number, color: string }) => (
              <Info size={size} color={color} />
            ),
          }}
        />
      </Drawer>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});