"use client";

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from 'wagmi';
import { getDefaultConfig, RainbowKitProvider } from '@rainbow-me/rainbowkit';
import { localhost } from 'wagmi/chains';
import '@rainbow-me/rainbowkit/styles.css';
import { HeroUIProvider } from "@heroui/react";
import UserBetsList from "../../components/UserBetsList";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import SidebarNav from "../../components/SidebarNav";
import ThemeToggle from "../../components/ThemeToggle";
import FaucetButton from "../../components/FaucetButton";

// Import wagmi config from central config
import { WAGMI_CONFIG } from '../../config/contracts';

// Configure Wagmi client
const config = getDefaultConfig({
  appName: WAGMI_CONFIG.APP_NAME,
  projectId: WAGMI_CONFIG.PROJECT_ID,
  chains: [localhost],
  ssr: false,
});

export default function MyBetsPage() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <HeroUIProvider>
            <div className="main-container">
              <SidebarNav />
              <div className="content-area">
                <header className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow">
                  <div className="container mx-auto px-4 py-4 flex justify-between items-center">
                    <h1 className="text-2xl font-bold text-gray-800 dark:text-white">My Bets</h1>
                    <div className="flex items-center gap-4">
                      <FaucetButton />
                      <ThemeToggle />
                      <ConnectButton />
                    </div>
                  </div>
                </header>
                <main className="container mx-auto px-4 py-8">
                  <UserBetsList markets={[]} />
                </main>
              </div>
            </div>
          </HeroUIProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}