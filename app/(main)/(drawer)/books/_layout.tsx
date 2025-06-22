import React from 'react';
import { TouchableOpacity } from 'react-native';
import { Stack } from 'expo-router';
import { Menu, ArrowLeft } from 'lucide-react-native';
import { useDrawer } from '../_layout';
import { booksData } from '@/data/books';

function MenuButton({ tintColor }: { tintColor?: string }) {
  const { toggleDrawer } = useDrawer();
  
  return (
    <TouchableOpacity
      style={{ padding: 8, marginLeft: 8 }}
      onPress={toggleDrawer}
      activeOpacity={0.7}
    >
      <Menu size={24} color={tintColor} />
    </TouchableOpacity>
  );
}

export default function BooksLayout() {
  return (
    <Stack 
      screenOptions={{
        headerShown: true,
        headerStyle: {
          backgroundColor: 'rgb(255, 255, 255)',
        },
        headerTintColor: '#000000',
        headerTitleStyle: {
          fontWeight: '600',
        },
      }}
    >
      <Stack.Screen 
        name="index" 
        options={{
          title: 'Book Catalog',
          headerLeft: ({ tintColor }) => <MenuButton tintColor={tintColor} />,
        }}
      />
      <Stack.Screen 
        name="[id]" 
        options={({ route }) => {
          const { id } = route.params as { id: string };
          const book = booksData.find((b) => b.id === id);
          return {
            title: book ? book.title : 'Book Details',
            headerTitleStyle: {
              fontWeight: '600',
              fontSize: 16, // Slightly smaller for longer titles
            },
          };
        }}
      />
    </Stack>
  );
}