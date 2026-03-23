// app/layout.tsx

import NavBar from "./navbar/Navbar";
import SignupPage from "./authN/SignupPage";
import LoginPage from "./authN/LoginPage";
import "./globals.css";


export const metadata: Metadata = {
  title: "Secure Chess",
  description: "A really fast and secure chess engine",
  icons: { icon: "/vercel.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="h-screen w-screen">
        <NavBar />
        {children}
      </body>
    </html>
  );
}
