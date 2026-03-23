import Link from "next/link";

export default function NavBar() {
  return (
    <div className="w-full px-6 py-4 border-b-2 border-b-black">
      <div className="flex flex-row justify-between">
        <Link href="/" className="font-bold text-xl">Secure-Chess</Link>

        <div className="flex items-center gap-4">
          <Link href="/login">Login</Link>
          <Link href="/signup">Signup</Link>
        </div>
      </div>
    </div>
  );
}
