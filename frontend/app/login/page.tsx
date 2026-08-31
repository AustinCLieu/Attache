"use client";

// Login and signup share one screen and one form; a toggle switches which
// mutation runs. Two nearly-identical pages would drift apart.

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin, useSignup } from "@/lib/queries";

type Mode = "login" | "signup";

export default function LoginPage() {
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin();
  const signup = useSignup();
  const active = mode === "login" ? login : signup;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Without this the browser does a full page reload on submit.
    event.preventDefault();

    active.mutate(
      { email, password },
      { onSuccess: () => router.push("/") },
    );
  }

  function switchMode(next: Mode) {
    setMode(next);
    // Clear the previous attempt's error so it does not linger on the new tab.
    login.reset();
    signup.reset();
  }

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Attaché</CardTitle>
          <CardDescription>
            {mode === "login"
              ? "Sign in to your account."
              : "Create an account to get started."}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              {mode === "signup" && (
                <p className="text-xs text-muted-foreground">
                  At least 8 characters.
                </p>
              )}
            </div>

            {active.isError && (
              <p role="alert" className="text-sm text-red-600">
                {active.error.message}
              </p>
            )}

            <Button type="submit" disabled={active.isPending}>
              {active.isPending
                ? "Working…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            {mode === "login" ? (
              <>
                No account?{" "}
                <button
                  type="button"
                  className="underline underline-offset-4"
                  onClick={() => switchMode("signup")}
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  className="underline underline-offset-4"
                  onClick={() => switchMode("login")}
                >
                  Sign in
                </button>
              </>
            )}
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
