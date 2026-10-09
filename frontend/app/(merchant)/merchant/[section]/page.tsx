import MerchantWorkspace from "@/components/merchant/MerchantWorkspace";

export function generateStaticParams() {
  return ["orders", "catalog", "inventory", "customers", "analytics", "settings"].map((section) => ({ section }));
}

export default function MerchantSectionPage() {
  return <MerchantWorkspace />;
}
