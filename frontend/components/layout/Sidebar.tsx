'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Upload, Megaphone, Scissors } from 'lucide-react';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/upload', label: 'New Job', icon: Upload },
  { href: '/campaigns', label: 'Campaigns', icon: Megaphone },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-56 h-screen flex flex-col border-r"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="p-5 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Scissors size={20} style={{ color: 'var(--accent)' }} />
          <span className="font-bold text-lg tracking-tight">ClipOS</span>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
          Whop Clipping Automation
        </p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors"
              style={{
                background: active ? 'rgba(74, 222, 128, 0.1)' : 'transparent',
                color: active ? 'var(--accent)' : 'var(--muted)',
              }}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t" style={{ borderColor: 'var(--border)' }}>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          Phase 1 — Local Build
        </p>
      </div>
    </aside>
  );
}
