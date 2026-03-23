"use client"
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from "next/link";


export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSubmitting(true);
    setPassword("");
    setError("");

    try {
      const baseUrl = "http://localhost:8000"

      const res = await fetch(`${baseUrl}/auth/signup`, {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      })

      const data = await res.json();

      if (!res.ok) {
        setError("Failed to login");
        return;
      }

      router.push("/home");
    } catch {
      setError("cannot reach server");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex flex-col items-center justify-center">
      <h1 className="text-2xl font-bold">Log In</h1>

      <div className="flex flex-row">
        <p>Don't have an account?</p>
        <Link href="/signup" className="underline">Sign Up</Link>
      </div>

      <form onSubmit={handleSubmit} className="px-auto py-4 justify-center">
        <div>
          <label htmlFor="uname">Username:</label>
          <input
            id="uname"
            name="username"
            type="text"
            value={username}
            onChange={(e) => { setUsername(e.target.value) }}
            className="border rounded p-2"
            required
          />
        </div>

        <div>
          <label htmlFor="password">Password:</label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => { setPassword(e.target.value) }}
            className="border rounded p-2"
            required
          />
        </div>

        {error ? <p className="text-red-600">{error}</p> : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="font-bold border border-black rounded-2xl p-2"
        >
          {isSubmitting ? "Logging in..." : "Log in"}
        </button>

      </form>
    </main>
  );
};
