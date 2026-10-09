import { PortalShell } from "@/components/merchant/PortalShell";

export default function MerchantLayout({ children }: { children: React.ReactNode }) {
  return <PortalShell>{children}</PortalShell>;
}
