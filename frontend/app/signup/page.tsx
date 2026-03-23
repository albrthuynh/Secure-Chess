"use client"
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from "next/link";

export default function SignupPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
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
        body: JSON.stringify({ username, email, password }),
      })

      const data = await res.json();

      if (!res.ok) {
        setError("Failed to Signup");
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
      <h1 className="text-2xl font-bold">Create an account</h1>

      <div className="flex flex-row">
        <p>Already have an account?</p>
        <Link href="/login" className="underline">Log in</Link>
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
          <label htmlFor="email">Email:</label>
          <input
            id="email"
            name="email"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value) }}
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
          {isSubmitting ? "Creating Account..." : "Create Account"}
        </button>

      </form>
    </main>
  );
};
