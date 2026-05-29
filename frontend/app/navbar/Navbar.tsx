import Link from "next/link";

export default function NavBar() {
  return (
    <nav className="site-nav">
      <div className="site-nav-inner">
        <Link href="/" className="site-logo">
          <span className="site-logo-icon">♔</span>
          Secure Chess
        </Link>
      </div>
    </nav>
  );
}
