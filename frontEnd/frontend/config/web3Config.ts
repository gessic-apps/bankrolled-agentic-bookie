"use client";

import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { QueryClient } from '@tanstack/react-query';
import { WAGMI_CONFIG, SELECTED_NETWORK } from './contracts';

// Create the Wagmi config
export const wagmiConfig = getDefaultConfig({
  appName: WAGMI_CONFIG.APP_NAME,
  projectId: WAGMI_CONFIG.PROJECT_ID,
  chains: [SELECTED_NETWORK],
  ssr: false,
});

// Create a QueryClient for React Query
export const queryClient = new QueryClient();