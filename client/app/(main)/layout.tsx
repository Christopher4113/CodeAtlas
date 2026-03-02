import Navbar from "@/components/navbar";
import React from "react";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen w-full">
      <Navbar />
      <main className="w-full">{children}</main>
    </div>
  );
}