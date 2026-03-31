import React from 'react';
import { Settings as SettingsIcon, Database, Key, Shield, User, Bell, Save } from 'lucide-react';

export function Settings() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header>
        <h2 className="text-3xl font-bold mb-2">System Settings</h2>
        <p className="text-muted-foreground">Manage your AI configurations and team permissions</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Navigation */}
        <div className="space-y-2">
          {[
            { name: 'General', icon: SettingsIcon },
            { name: 'API Configuration', icon: Key },
            { name: 'Database', icon: Database },
            { name: 'Security', icon: Shield },
            { name: 'User Management', icon: User },
            { name: 'Notifications', icon: Bell },
          ].map((item, i) => (
            <button 
              key={i} 
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 font-medium ${i === 1 ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'}`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.name}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="md:col-span-2 space-y-6">
          <div className="glass-card space-y-6">
            <h3 className="text-xl font-semibold flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-400" /> API Configuration
            </h3>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Google Gemini API Key</label>
                <div className="relative">
                  <input 
                    type="password" 
                    defaultValue="AIzaSyD6kZKH6N83GsgvZ_xnAU-S-v9mHNjRPbw" 
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-mono" 
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded-md border border-green-500/20 font-bold tracking-widest uppercase">Connected</span>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">OpenAI Project Key</label>
                <input 
                  type="password" 
                  defaultValue="sk-proj-**********************************" 
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-mono" 
                />
              </div>

              <div className="space-y-2 pt-4">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Model Preference</label>
                <select className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all">
                  <option className="bg-[#0a0a0b]">Gemini 1.5 Pro (Recommended)</option>
                  <option className="bg-[#0a0a0b]">GPT-4o</option>
                  <option className="bg-[#0a0a0b]">Claude 3.5 Sonnet</option>
                </select>
              </div>
            </div>

            <div className="pt-6 border-t border-white/5">
              <button className="btn-primary w-full flex items-center justify-center gap-2">
                <Save className="w-5 h-5" /> Save Changes
              </button>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-yellow-500/5 border border-yellow-500/20">
            <h4 className="text-sm font-bold text-yellow-500 mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4" /> Security Note
            </h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              API keys are stored in the local environment and are never transmitted to our telemetry servers. 
              Always ensure your <code className="bg-white/5 px-1 rounded">.env</code> file is included in your <code className="bg-white/5 px-1 rounded">.gitignore</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
