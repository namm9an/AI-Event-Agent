"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getRole, getToken } from "@/lib/session";

export default function HomeRouter() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    const role = getRole();
    if (!token || !role) return;
    router.replace("/dashboard");
  }, [router]);

  return null;
}
