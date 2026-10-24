"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

const REFRESH_EVERY_MS = 4000;

export function LiveRefresh({ active }: { active: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => router.refresh(), REFRESH_EVERY_MS);
    return () => window.clearInterval(timer);
  }, [active, router]);
  return null;
}
