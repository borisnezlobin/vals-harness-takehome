import type { RoleName } from "@/lib/types";

const ROLE_FILL: Record<RoleName, string> = {
  buyer: "fill-buyer",
  seller: "fill-seller",
};

const ROLE_SHAPE: Record<RoleName, string> = {
  buyer: "M5 1 L9.5 9 H0.5 Z",
  seller: "M5 9 L9.5 1 H0.5 Z",
};

export const ROLE_TITLE: Record<RoleName, string> = { buyer: "Buyer", seller: "Seller" };

export function RoleMark({ role, className = "size-2.5" }: { role: RoleName; className?: string }) {
  return (
    <svg viewBox="0 0 10 10" aria-hidden="true" className={`shrink-0 ${className}`}>
      <path d={ROLE_SHAPE[role]} className={ROLE_FILL[role]} />
    </svg>
  );
}

export function RoleLabel({ role }: { role: RoleName }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <RoleMark role={role} />
      {ROLE_TITLE[role]}
    </span>
  );
}
