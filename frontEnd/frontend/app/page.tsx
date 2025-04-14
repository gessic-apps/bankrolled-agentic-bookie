"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider } from '@rainbow-me/rainbowkit';
import '@rainbow-me/rainbowkit/styles.css';
import { HeroUIProvider } from "@heroui/react";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import ThemeToggle from "../components/ThemeToggle";
import FaucetButton from "../components/FaucetButton";
import Link from 'next/link';
import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { SELECTED_NETWORK, WAGMI_CONFIG } from '../config/contracts'; // Import constants AND selected network

// Placeholder image URLs - replace with your actual image paths or URLs
const featureImage1 = "/phones.png"; // Example path
const featureImage2 = "/featureImage2.png"; // Example path
const happyPlayer = "/happyPlayer.png"; // Example path
const featureImage3 = "/rewards.png"; // Example path

// Placeholder avatar URLs - replace with your actual image paths or URLs
const avatarOddsCompiler = "/oddsCompilerAgent.png";
const avatarRiskManager = "/riskManagerAgent.png";
const avatarMarketCreator = "/marketCreationAgent.png";
const avatarLiquidityManager = "/liquidityPoolAgent.png";
const avatarUserBehavior = "/userBehaviorAgent.png";
const avatarEventMonitor = "/eventMonitorAgent.png";
const avatarSettlement = "/settlementAgent.png";
const avatarCompliance = "/complianceAgent.png";
const avatarSecurity = "/securityAgent.png";
const avatarGovernance = "/governanceAgent.png";
const avatarCustomerService = "/customerServiceAgent.png";

// Placeholder Founder Images
const founderChris = "/chris.png"; // Replace with actual path
const founderAbdul = "/abdul.png"; // Replace with actual path

// Helper function for status badge styling
const getStatusClasses = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case 'in progress':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    case 'coming soon':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'; // Default/fallback style
  }
};

// Main Landing Page Content Component
function LandingPageContent() {
  return (
    <div className="space-y-16 md:space-y-24">
      {/* Hero Section - Removing background/overlay here, using global layout background */}
      <section className="relative text-center pt-24 pb-20 md:pt-32 md:pb-28 isolate">
        {/* Overlay removed */}
        {/* <div className="absolute inset-0 bg-black/30 dark:bg-black/50 -z-10"></div> */}

        {/* Revert text colors to be theme-aware */}
        <h1 className="text-4xl md:text-6xl font-extrabold mb-4 text-gray-900 dark:text-white leading-tight">
          The Future of Sports Betting is Here.
        </h1>
        <p className="text-lg md:text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-8">
          The world&apos;s first sportsbook run entirely by AI employees. Fair odds, transparent operations, powered by the blockchain.
        </p>
        <Link href="/all-markets">
          <button className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 rounded-md px-8">
             Start Betting
          </button>
        </Link>
      </section>

      {/* Features Section */}
      <section className="space-y-12 md:space-y-16">
        {/* Feature 1: AI-Powered Odds */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
          <div className="order-2 md:order-1">
            <h3 className="text-2xl md:text-3xl font-bold mb-3 text-gray-800 dark:text-white">The Best Odds, Always</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Our autonomous AI agents analyze vast amounts of data in real-time to provide you with the LOWEST odds pricing!
            </p>
            <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
              <li>Constantly learning and improving prices</li>
              <li>Unbiased odds generation</li>
              <li>Faster updates than traditional bookmakers</li>
              <li>Do not bother with line shopping anymore!</li>
            </ul>
          </div>
          <div className="order-1 md:order-2 flex justify-center">
             {/* Replace with next/image if you have local images */}
             <img src={featureImage1} alt="AI Network" className="rounded-lg shadow-lg w-full max-w-3xl h-auto object-cover dark:brightness-90" />
          </div>
        </div>

        {/* Feature 2: True Decentralization */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
          <div className="order-1 md:order-1 flex justify-center">
             <img src={featureImage2} alt="Blockchain Network" className="rounded-lg shadow-lg w-full max-w-md h-auto object-cover dark:brightness-90" />
          </div>
          <div className="order-2 md:order-2">
            <h3 className="text-2xl md:text-3xl font-bold mb-3 text-gray-800 dark:text-white">No more limits or Shady Practices</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              No more limits or shady practices! We are a fully transparent sportsbook, with all operations and prices being visible to everyone. Bet with the sharps!
            </p>
             <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
              <li>Full transparency of operations</li>
              <li>Censorship-resistant platform</li>
              <li>User funds remain in user control</li>
            </ul>
          </div>
        </div>

        {/* Feature 3: Autonomous Operation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
           <div className="order-2 md:order-1">
            <h3 className="text-2xl md:text-3xl font-bold mb-3 text-gray-800 dark:text-white">We Pass our savings to you</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
            As a fully autonomous sportsbook, we have significantly lower overhead - so we pass our savings to you in the form of lower margins and better odds!
            </p>
             <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
              <li>Reduced operational costs</li>
              <li>24/7 availability without human intervention</li>
              <li>Focus on efficiency and user value</li>
            </ul>
          </div>
           <div className="order-1 md:order-2 flex justify-center">
             <img src={happyPlayer} alt="Autonomous Robot" className="rounded-lg shadow-lg w-full max-w-sm h-auto object-cover dark:brightness-90" />
          </div>
        </div>

         {/* Feature 2: True Decentralization */}
         <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
          <div className="order-1 md:order-1 flex justify-center">
             <img src={featureImage3} alt="Blockchain Network" className="rounded-lg shadow-lg w-full max-w-md h-auto object-cover dark:brightness-90" />
          </div>
          <div className="order-2 md:order-2">
            <h3 className="text-2xl md:text-3xl font-bold mb-3 text-gray-800 dark:text-white">Get rewarded for your track record</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              We love consistent bettors, and provides various rewards for those who are able to maintain a consistent track record. Whether winning or losing, your data helps the system get better. 
            </p>
             <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
              <li>Earn loyalty rewards in the form of BANK tokens</li>
              <li>The more you bet, the more rewards you earn</li>
              <li>The more you win, the more your data helps the system get better</li>
            </ul>
          </div>
        </div>



      </section>

      {/* Meet The AI Employees Section - Removing background color here */}
      <section className="py-16 md:py-24">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 text-gray-800 dark:text-white">
            Meet The AI Employees
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Agent Card Template - Repeat for each agent */}
            {[
              { name: "Odds Compiler Agent", role: "Mathematical modeling and market creation", description: "Analyzing data, creating models, generating odds, managing risk parameters.", avatar: avatarOddsCompiler, status: "Completed", details: ["Analyzing historical data, team statistics, player performance, and other relevant factors", "Creating statistical models to generate initial odds and lines", "Continuously monitoring and adjusting odds", "Implementing risk management parameters", "Maintaining proper margin/vigorish", "Providing specialized odds calculations", "Evaluating efficiency of odds models"] },
              { name: "Risk Management Agent", role: "Exposure assessment and limit enforcement", description: "Tracking exposure, setting limits, identifying unusual patterns, balancing books.", avatar: avatarRiskManager, status: "Completed", details: ["Tracking overall exposure across all events and markets", "Setting and adjusting betting limits", "Identifying and flagging unusual betting patterns", "Implementing automatic risk balancing", "Calculating optimal hedging strategies", "Monitoring potential arbitrage opportunities", "Providing real-time risk dashboards"] },
              { name: "Market Creation Agent", role: "Betting market design and implementation", description: "Determining markets, creating bet types, designing props, implementing live betting.", avatar: avatarMarketCreator, status: "Completed", details: ["Determining which events and markets to offer", "Creating diverse bet types (parlays, teasers, etc.)", "Designing specialized proposition bets", "Implementing live betting markets", "Structuring betting markets for engagement and profitability", "Creating unique betting opportunities"] },
              { name: "Liquidity Pool Manager Agent", role: "Capital allocation and liquidity maintenance", description: "Managing liquidity pool, distributing rewards, allocating capital, ensuring settlement liquidity.", avatar: avatarLiquidityManager, status: "Completed", details: ["Manage the decentralized liquidity pool", "Calculate and distribute rewards to LPs", "Determine optimal capital allocation", "Ensure sufficient liquidity for settlement", "Implement protection mechanisms", "Monitor and maintain reserve ratios", "Execute smart contracts for payouts"] },
              { name: "User Behavior Analysis Agent", role: "Customer profiling and experience optimization", description: "Analyzing patterns, profiling users, personalizing recommendations, optimizing UI.", avatar: avatarUserBehavior, status: "Coming Soon", details: ["Analyzing betting patterns of individual users", "Creating user profiles (sharp vs. recreational)", "Personalizing betting recommendations", "Identifying potential problem gambling behavior", "Optimizing user interfaces", "Implementing responsible gambling tools", "Designing loyalty programs"] },
              { name: "Event Monitoring Agent", role: "Real-time sports data ingestion and verification", description: "Connecting to data providers, monitoring live events, verifying results, handling contingencies.", avatar: avatarEventMonitor, status: "In Progress", details: ["Maintaining connections to multiple sports data providers", "Monitoring live sporting events in real-time", "Verifying game results and statistics", "Identifying discrepancies in reported results", "Handling special cases (postponements, injuries)", "Implementing fallback protocols", "Monitoring data integrity"] },
              { name: "Settlement Agent", role: "Bet resolution and payout execution", description: "Verifying results, applying rules, processing payouts via smart contracts, handling disputes.", avatar: avatarSettlement, status: "In Progress", details: ["Verifies final results from multiple sources", "Applies settlement rules to all markets", "Processes payouts through smart contracts", "Handles special settlement cases (pushes, etc.)", "Maintains detailed settlement records", "Resolves settlement disputes via rules", "Implements multi-sig for large payouts"] },
              { name: "Compliance and Regulatory Agent", role: "Legal adherence and responsible gambling enforcement", description: "Implementing KYC/AML, geo-restrictions, age verification, responsible gambling controls.", avatar: avatarCompliance, status: "Coming Soon", details: ["Implementation of KYC/AML where applicable", "Geo-restriction enforcement", "Age verification procedures", "Responsible gambling controls", "Record-keeping for regulatory reporting", "Adapting to changing regulations", "Implementing self-exclusion programs"] },
              { name: "Security Agent", role: "System integrity and fraud prevention", description: "Monitoring vulnerabilities, preventing collusion/fraud, securing data feeds, conducting audits.", avatar: avatarSecurity, status: "Coming Soon", details: ["Monitors for potential security breaches", "Detects and prevents collusion", "Identifies potential match-fixing patterns", "Implements multi-factor authentication", "Secures oracle data feeds", "Conducts regular security audits", "Prevents insider information exploitation"] },
              { name: "Governance Agent", role: "Decentralized decision-making facilitation", description: "Managing voting, implementing decisions, ensuring transparency, facilitating proposals.", avatar: avatarGovernance, status: "Coming Soon", details: ["Manages voting mechanisms for protocol changes", "Implements approved governance decisions", "Ensures transparency in operation", "Facilitates community proposals", "Distributes governance tokens", "Creates and maintains documentation", "Enforces protocol rules"] },
              { name: "Customer Service Agent", role: "User support and issue resolution", description: "Providing automated support, answering questions, assisting with accounts, handling inquiries.", avatar: avatarCustomerService, status: "Coming Soon", details: ["Providing 24/7 automated support", "Answering common questions", "Assisting with account setup/recovery", "Handling deposit/withdrawal inquiries", "Managing bet disputes (escalating complex ones)", "Collecting user feedback", "Providing guided assistance", "Offering multilingual support", "Maintaining knowledge base"] },
            ].map((agent) => (
              <div key={agent.name} className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden p-6 flex flex-col items-center text-center hover:shadow-lg transition-shadow duration-300">
                <img src={agent.avatar} alt={`${agent.name} Avatar`} className="w-24 h-24 rounded-full mb-4 object-cover bg-gray-200 dark:bg-gray-700" />
                <h3 className="text-xl font-semibold mb-1 text-gray-900 dark:text-white">{agent.name}</h3>
                {/* Status Badge */}
                <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium mb-2 ${getStatusClasses(agent.status)}`}>
                  {agent.status}
                </span>
                <p className="text-sm font-medium text-primary dark:text-primary-light mb-3">{agent.role}</p>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">{agent.description}</p>
                 {/* Optional: Add a way to show more details if needed, e.g., a modal or accordion */}
                 {/* <details className="text-left text-xs text-gray-500 dark:text-gray-400 w-full">
                   <summary className="cursor-pointer">More details</summary>
                   <ul className="list-disc list-inside pl-4 mt-2 space-y-1">
                     {agent.details.map((detail, index) => <li key={index}>{detail}</li>)}
                   </ul>
                 </details> */}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Meet the Founders Section */}
      <section className="py-16 md:py-24">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 text-gray-800 dark:text-white">
            Meet the Founders
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20 max-w-4xl mx-auto">
            {/* Founder 1: Chris Brookings - Ensure centered */}
            <div className="flex flex-col items-center text-center">
              <img src={founderChris} alt="Chris Brookings" className="w-32 h-32 rounded-full mb-6 object-cover bg-gray-200 dark:bg-gray-700 shadow-md" />
              {/* Add margin bottom to name */}
              <h3 className="text-2xl font-semibold mb-3 text-gray-900 dark:text-white">Chris Brookings</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Co-founder of RociFi, a Web3 under-collateralized lending platform leveraging ML-powered credit scoring. Chris is a seasoned entrepreneur with deep expertise in Crypto x AI and DeFi. He has led two startups at the intersection of large-scale data systems and ML/AI: a quant hedge fund and RociFi.
              </p>
            </div>

            {/* Founder 2: Abdul Osman - Ensure centered */}
            <div className="flex flex-col items-center text-center">
              <img src={founderAbdul} alt="Abdul Osman" className="w-32 h-32 rounded-full mb-6 object-cover bg-gray-200 dark:bg-gray-700 shadow-md" />
              {/* Add margin bottom to name */}
              <h3 className="text-2xl font-semibold mb-3 text-gray-900 dark:text-white">Abdul Osman</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Co-founder of Gora Network, the leading Algorand-based oracle network. Abdul is a highly technical founder with extensive experience in oracles, data systems, and software development. A former semi-professional sports bettor, he has firsthand insight into the inefficiencies of traditional sportsbooks and prediction markets.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function Home() {
  const [queryClient] = useState(() => new QueryClient());
  // Use the Wagmi config directly from the imported config file -- INCORRECT COMMENT, FIXING SETUP
  // const config = WAGMI_CONFIG.config; // OLD INCORRECT LINE

  // Create the config object using imported constants
  const config = getDefaultConfig({
    appName: WAGMI_CONFIG.APP_NAME,
    projectId: WAGMI_CONFIG.PROJECT_ID,
    chains: [SELECTED_NETWORK],
    ssr: false, // Assuming SSR is false based on all-markets page
  });

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <HeroUIProvider>
            {/* Main container managed by layout.tsx */}
            <div className="absolute top-4 right-4 z-50 flex items-center space-x-2">
                <ConnectButton />
                <FaucetButton />
                <ThemeToggle />
            </div>
            <LandingPageContent />
            {/* Removed <SidebarNav /> from here */}
          </HeroUIProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
