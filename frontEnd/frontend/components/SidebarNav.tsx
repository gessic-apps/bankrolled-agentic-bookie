"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
  //@ts-expect-error icon is a JSX.Element
  icon: JSX.Element;
}

export default function SidebarNav() {
  const [isMobile, setIsMobile] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    // Initial check
    handleResize();
    
    // Add event listener
    window.addEventListener('resize', handleResize);
    
    // Clean up
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = () => {
    setExpanded(!expanded);
  };

  const navItems: NavItem[] = [
    {
      label: 'Home',
      href: '/',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
        
      ),
    },
    {
      label: 'All Markets',
      href: '/all-markets',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
        <path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7" />
        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
        <path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4" />
        <path d="M2 7h20" />
        <path d="M22 7v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7" />
      </svg>
      ),
    },
    // {
    //   label: 'Basketball',
    //   href: '/sports/basketball',
    //   icon: (
    //     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
    //       <circle cx="12" cy="12" r="10" />
    //       <path d="M4.93 4.93L19.07 19.07" />
    //       <path d="M14.83 9.17C15.55 7.83 19.44 2 19.44 2" />
    //       <path d="M9.17 14.83C7.83 15.55 2 19.44 2 19.44" />
    //       <path d="M14.83 14.83C11.5 18.17 7.36 19.61 5.73 20.27" />
    //       <path d="M9.17 9.17C3.03 11.29 2.56 19.11 2.56 19.11" />
    //     </svg>
    //   ),
    // },
    // {
    //   label: 'Soccer',
    //   href: '/sports/soccer',
    //   icon: (
    //     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
    //       <circle cx="12" cy="12" r="10" />
    //       <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    //     </svg>
    //   ),
    // },
    {
      label: 'My Bets',
      href: '/my-bets',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
          <polyline points="17 21 17 13 7 13 7 21" />
          <polyline points="7 3 7 8 15 8" />
        </svg>
      ),
    },
    {
      label: 'Agent Reports',
      href: '/agent-reports',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
          <path d="M12 8V4H8V8H6v8h12V8z" />
          <path d="M16 16v-4h4V8h-4V4h-4v4H8v4h4v4z" />
          <path d="M12 16h.01" />
          <path d="M12 20c-2.21 0-4-1.79-4-4h8c0 2.21-1.79 4-4 4z" />
          <path d="M4 16H2v-4h2M22 16h-2v-4h2" />
        </svg>
      ),
    },
  ];

  return (
    <nav 
      className={`sidebar ${isMobile && expanded ? 'sidebar-expanded' : ''} ${isMobile && !expanded ? 'sidebar-collapsed' : ''}`}
    >
      <div className="p-4 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-8 h-8 text-blue-400">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
          {(!isMobile || expanded) && <span className="ml-2 text-xl font-bold sidebar-text">Bankrolled</span>}
        </div>
        {isMobile && (
          <button onClick={toggleSidebar} className="p-1 rounded-md text-gray-400 hover:text-white hover:bg-gray-700">
            {expanded ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        )}
      </div>

      <div className="py-4">
        {navItems.map((item) => (
          <Link 
            key={item.href} 
            href={item.href}
            className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="mr-3">{item.icon}</span>
            {(!isMobile || expanded) && <span className="sidebar-text">{item.label}</span>}
          </Link>
        ))}
      </div>
    </nav>
  );
}