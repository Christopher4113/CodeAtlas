import React, { Suspense } from "react";
import Link from "next/link";
import { AuthButton } from "./auth-button";

const Navbar = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-black/10 bg-white/80 backdrop-blur-md shadow-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-semibold tracking-tight"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-black text-white text-xs font-bold">
            CA
          </div>
          <span>
            Code<span className="text-black/60">Atlas</span>
          </span>
        </Link>

        {/* Auth */}
        <Suspense
          fallback={
            <div className="h-9 w-24 animate-pulse rounded-md bg-gray-200" />
          }
        >
          <AuthButton />
        </Suspense>

      </div>
    </header>
  );
};

export default Navbar;