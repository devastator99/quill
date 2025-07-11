import React from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useFrameworkReady } from '@/hooks/useFrameworkReady';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { WalletProvider, useWallet } from '@solana/wallet-adapter-react';
import { PhantomWalletAdapter } from '@solana/wallet-adapter-wallets';
import { WalletConnectButton } from '@solana/wallet-adapter-react-ui';

const wallets = [
  new PhantomWalletAdapter(),
]; 

export default function RootLayout() {
  useFrameworkReady();

  return (
    <WalletProvider wallets={wallets} autoConnect>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <WalletConnectButton />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="+not-found" />
        </Stack>
      </SafeAreaProvider>
    </WalletProvider>
  );
}
