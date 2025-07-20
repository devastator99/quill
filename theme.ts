import { DefaultTheme } from '@react-navigation/native';

export const theme = {
  colors: {
    ...DefaultTheme.colors,
    text: '#000',
    background: '#fff',
    primary: '#6200ee',
    card: '#f5f5f5',
    border: '#e0e0e0',
    notification: '#ff3d00',
  },
  dark: {
    text: '#fff',
    background: '#121212',
    primary: '#bb86fc',
    card: '#1e1e1e',
    border: '#333',
    notification: '#ff8a65',
  }
};

export type AppTheme = typeof theme;
