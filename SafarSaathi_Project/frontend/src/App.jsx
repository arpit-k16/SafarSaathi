import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Toast from './components/Toast';
import LandingPage from './pages/LandingPage';
import OverviewDashboard from './pages/OverviewDashboard';
import DestinationDigitalTwin from './pages/DestinationDigitalTwin';
import DisasterMode from './pages/DisasterMode';
import WhatIfSimulator from './pages/WhatIfSimulator';
import AuxiliaryView from './pages/AuxiliaryView';

export default function App() {
  const [activeTab, setActiveTab] = useState('landing');
  const [currentSector, setCurrentSector] = useState('Garhwal Arc // Rishikesh Core');
  const [toast, setToast] = useState(null);
  const [lastScenario, setLastScenario] = useState(null);

  // Auto-dismiss toast after 4.5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 4500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = ({ title, message, type = 'success' }) => {
    setToast({ title, message, type });
  };

  const navigateTo = (tab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // If on public Landing Page, render full-bleed landing view
  if (activeTab === 'landing') {
    return (
      <div className="min-h-screen bg-[#080a0f] text-on-surface">
        <LandingPage onNavigate={navigateTo} />
        <Toast toast={toast} onClose={() => setToast(null)} />
      </div>
    );
  }

  // Dashboard layout with Sidebar and Header
  return (
    <div className="min-h-screen bg-surface text-on-surface flex flex-col font-sans">
      {/* 72-Width Command Sidebar */}
      <Sidebar activeTab={activeTab} onSelectTab={navigateTo} />

      {/* Top Command Deck Header */}
      <Header
        currentSector={currentSector}
        onSectorChange={setCurrentSector}
        onNavigateHome={() => navigateTo('landing')}
        onEmergencyEscalate={() => navigateTo('disaster-mode')}
        activeTab={activeTab}
      />

      {/* Main Viewport Content Deck */}
      <main className="pl-72 pt-16 flex-1 w-full bg-surface min-h-screen">
        {activeTab === 'overview' && (
          <OverviewDashboard onNavigate={navigateTo} showToast={showToast} />
        )}
        {activeTab === 'destination-twin' && (
          <DestinationDigitalTwin onNavigate={navigateTo} showToast={showToast} />
        )}
        {activeTab === 'disaster-mode' && (
          <DisasterMode onNavigate={navigateTo} showToast={showToast} lastScenario={lastScenario} />
        )}
        {activeTab === 'what-if-simulator' && (
          <WhatIfSimulator onNavigate={navigateTo} showToast={showToast} lastScenario={lastScenario} onScenario={setLastScenario} />
        )}

        {/* Auxiliary Tab Views */}
        {![
          'overview',
          'destination-twin',
          'disaster-mode',
          'what-if-simulator',
        ].includes(activeTab) && (
          <AuxiliaryView key={activeTab} activeTab={activeTab} onNavigate={navigateTo} lastScenario={lastScenario} />
        )}
      </main>

      {/* Global Toast Overlay */}
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
