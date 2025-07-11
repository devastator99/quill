import { useWallet } from '@solana/wallet-adapter-react';

export default function WalletConnectButton() {
  const { connect, disconnect, connected, publicKey, signMessage } = useWallet();

  async function handleLogin() {
    if (!publicKey || !signMessage) {
      alert("Please connect your wallet first!");
      return;
    }
    const message = "Login to DocChatApp";
    const signMessageFn = signMessage as (message: Uint8Array) => Promise<Uint8Array>;
    const signature = await signMessageFn(new TextEncoder().encode(message));
    const base64Signature = btoa(String.fromCharCode(...signature));
    const response = await fetch('http://localhost:8000/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        publicKey: publicKey.toString(),
        signature: base64Signature,
      }),
    });
    const data = await response.json();
    console.log(data);
    if (data.token) console.log("Login successful:", data.token);
    else console.error("Login failed");
  }

  return (
    <>
      {connected ? (
        <button onClick={disconnect}>Disconnect Wallet</button>
      ) : (
        <button onClick={connect}>Connect Wallet</button>
      )}
      {connected && <button onClick={handleLogin}>Login with Wallet</button>}
    </>
  );
}