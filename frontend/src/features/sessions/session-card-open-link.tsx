"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { ButtonSpinner } from "@/components/button-spinner";

interface SessionCardOpenLinkProps {
  href: string;
  className?: string;
  children: ReactNode;
}

export function SessionCardOpenLink({
  href,
  className,
  children,
}: SessionCardOpenLinkProps) {
  const [isOpening, setIsOpening] = useState(false);

  return (
    <Link
      href={href}
      onClick={() => setIsOpening(true)}
      aria-busy={isOpening}
      className={className}
    >
      {isOpening && <ButtonSpinner className="h-4 w-4" />}
      {isOpening ? "Membuka Sesi…" : children}
    </Link>
  );
}
