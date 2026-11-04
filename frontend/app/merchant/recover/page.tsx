import Link from "next/link";
import { ArrowLeft, ShieldAlert, Store, KeyRound, PhoneCall } from "lucide-react";

export default function MerchantRecoveryPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F6F0E6] px-4 py-12 font-sans text-[#17251e]">
      <section className="w-full max-w-[480px] rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 sm:p-9 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-[#eee9df]">
          <Link
            href="/merchant/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1F5D42] hover:underline"
          >
            <ArrowLeft size={14} />
            Back to sign in / लॉगिन पर लौटें
          </Link>
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#123324]">
            <div className="grid h-6 w-6 place-items-center rounded-lg bg-[#E8A33D] text-[#123324]">
              <Store size={13} />
            </div>
            <span>Dukandaar</span>
          </div>
        </div>

        <div className="mb-6 mt-6 grid h-12 w-12 place-items-center rounded-2xl bg-[#fef3c7] text-[#92400e] border border-[#fde68a]">
          <KeyRound size={22} />
        </div>

        <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#6d756f]">
          Security Policy • सुरक्षा नीति
        </p>
        <h1 className="mt-1.5 text-2xl font-bold font-display tracking-tight text-[#123324]">
          Super Admin Password Reset
        </h1>
        <p className="mt-1 text-xs font-medium text-[#1F5D42]">
          पासवर्ड रीसेट केवल सुपर एडमिन द्वारा संभव है
        </p>

        <div className="mt-5 space-y-3.5 rounded-2xl bg-[#f7f5ed] border border-[#e5dfd2] p-4 text-xs text-[#3a443e] leading-relaxed">
          <p>
            Please contact your platform <strong>Super Admin</strong>. The Super Admin will generate a verified <strong>temporary password</strong> for your shop and provide your login credentials file.
          </p>
          <div className="p-3 bg-white rounded-xl border border-[#ddd6ca] space-y-1.5 text-[11px]">
            <div className="font-bold text-[#123324] flex items-center gap-1.5">
              <PhoneCall size={13} className="text-[#1F5D42]" />
              <span>Next Steps / अगले कदम:</span>
            </div>
            <ol className="list-decimal list-inside space-y-1 text-[#5e665f]">
              <li>Contact your Super Admin with your registered mobile number.</li>
              <li>Super Admin will reset and send you your temporary password.</li>
              <li>Sign in using the temporary password.</li>
              <li>You will automatically be prompted to choose your permanent private password.</li>
            </ol>
          </div>
        </div>

        <Link
          href="/merchant/login"
          className="mt-6 flex h-12 w-full items-center justify-center rounded-xl bg-[#1F5D42] text-sm font-semibold text-white shadow-xs hover:bg-[#164732] transition"
        >
          Return to sign in / लॉगिन पेज पर जाएं
        </Link>
      </section>
    </main>
  );
}
