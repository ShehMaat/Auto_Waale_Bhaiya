"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  const navLinks = [
    { name: "Dashboard", href: "/" },
    { name: "Jobs", href: "/jobs" },
    { name: "Analytics", href: "/analytics" },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <h1 className="text-xl font-bold text-blue-700 tracking-tight">AI Job Agent</h1>
            <nav className="hidden md:flex space-x-6">
              {navLinks.map((link) => {
                // Determine active state: exact match for root, or starts-with for others.
                const isActive = link.href === "/" 
                  ? pathname === "/" 
                  : pathname?.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`font-medium text-sm transition-colors ${
                      isActive ? "text-blue-600 border-b-2 border-blue-600 pb-5 pt-5" : "text-slate-600 hover:text-slate-900 py-5"
                    }`}
                  >
                    {link.name}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div>
            <button
              onClick={handleLogout}
              className="text-sm font-medium text-slate-500 hover:text-red-600 transition-colors"
              aria-label="Logout from account"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Nav */}
      <div className="md:hidden bg-white border-b border-slate-200 px-4 py-2 flex space-x-4 overflow-x-auto">
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`text-sm font-medium whitespace-nowrap px-3 py-1.5 rounded-full ${
              (link.href === "/" ? pathname === "/" : pathname?.startsWith(link.href))
                ? "bg-blue-100 text-blue-700" 
                : "text-slate-600"
            }`}
          >
            {link.name}
          </Link>
        ))}
      </div>

      <main className="flex-1 w-full">
        {children}
      </main>
    </div>
  );
}
