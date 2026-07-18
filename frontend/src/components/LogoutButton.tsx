"use client";

import { useAuth } from "./AuthProvider";

export default function LogoutButton() {
  const { user, signOut } = useAuth();
  if (!user) return null;
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-500 text-xs hidden sm:block truncate max-w-[180px]">{user.email}</span>
      <button
        onClick={signOut}
        className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700
          hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
      >
        Salir
      </button>
    </div>
  );
}
