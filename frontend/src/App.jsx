import React, { useState } from 'react'
import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { FileText, Upload, LayoutDashboard, CheckCircle, Shield, FlaskConical, ScrollText, Menu, X, Scissors, Tag, FolderOpen, Database, LogOut, Sun, Moon, BarChart3 } from 'lucide-react'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { useTheme } from './auth/ThemeContext'
import ProtectedRoute from './auth/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import ParsePage from './pages/Parse'
import ExtractPage from './pages/Extract'
import SplitPage from './pages/Split'
import ClassifyPage from './pages/Classify'
import FilesPage from './pages/Files'
import Jobs from './pages/Jobs'
import ReviewQueue from './pages/ReviewQueue'
import Schemas from './pages/Schemas'
import EvalsPage from './pages/Evals'
import Benchmarks from './pages/Benchmarks'
import AuditLog from './pages/AuditLog'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/parse', icon: Upload, label: 'Parse' },
  { to: '/extract', icon: Database, label: 'Extract' },
  { to: '/split', icon: Scissors, label: 'Split' },
  { to: '/classify', icon: Tag, label: 'Classify' },
  { to: '/files', icon: FolderOpen, label: 'Files' },
  { to: '/jobs', icon: FileText, label: 'Jobs' },
  { to: '/review', icon: CheckCircle, label: 'Review' },
  { to: '/schemas', icon: Shield, label: 'Schemas' },
  { to: '/evals', icon: FlaskConical, label: 'Evals' },
  { to: '/benchmarks', icon: BarChart3, label: 'Benchmarks' },
  { to: '/audit', icon: ScrollText, label: 'Audit Log' },
]

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth()

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />
      )}
      <aside className={`
        fixed lg:sticky top-0 left-0 z-50 h-screen
        w-60 bg-zinc-900 border-r border-zinc-800 flex flex-col
        transition-transform duration-200 ease-in-out
        ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              <span className="text-indigo-400">Pix</span>ora
            </h1>
            <p className="text-[11px] text-zinc-500 mt-0.5">Document Intelligence Platform</p>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button onClick={onClose} className="lg:hidden p-1 hover:bg-zinc-800 rounded">
              <X size={16} className="text-zinc-400" />
            </button>
          </div>
        </div>
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-500/10 text-indigo-400 font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-zinc-800 space-y-1">
          {user && (
            <div className="px-3 py-2 text-xs text-zinc-500 truncate">
              {user.email}
            </div>
          )}
          <button onClick={logout} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-red-400 hover:bg-zinc-800 transition-colors">
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>
    </>
  )
}

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-zinc-950">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden sticky top-0 z-30 bg-zinc-900/80 backdrop-blur border-b border-zinc-800 px-4 py-3 flex items-center gap-3">
          <button onClick={() => setSidebarOpen(true)} className="p-1 hover:bg-zinc-800 rounded">
            <Menu size={20} className="text-zinc-400" />
          </button>
          <h1 className="text-sm font-bold">
            <span className="text-indigo-400">Pix</span>ora
          </h1>
        </header>
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/parse" element={<ParsePage />} />
            <Route path="/extract" element={<ExtractPage />} />
            <Route path="/split" element={<SplitPage />} />
            <Route path="/classify" element={<ClassifyPage />} />
            <Route path="/files" element={<FilesPage />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/review" element={<ReviewQueue />} />
            <Route path="/schemas" element={<Schemas />} />
            <Route path="/evals" element={<EvalsPage />} />
            <Route path="/benchmarks" element={<Benchmarks />} />
            <Route path="/audit" element={<AuditLog />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Protected routes */}
        <Route path="/*" element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        } />
      </Routes>
    </AuthProvider>
  )
}
