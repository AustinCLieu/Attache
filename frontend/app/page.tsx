"use client";

// The "/" route. For M1 it is a signed-in landing page: it shows who you are
// (proving the whole auth round trip works end to end) and lets you sign out.
// M2 replaces this with a redirect into the inbox.

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/lib/queries";

export default function HomePage() {
  const router = useRouter();
  const { data: user, isPending } = useCurrentUser();
  const logout = useLogout();

  // Bounce signed-out visitors to the login page. This runs in an effect
  // because redirecting during render is not allowed in React.
  useEffect(() => {
    if (!isPending && !user) {
      router.replace("/login");
    }
  }, [isPending, user, router]);

  if (isPending) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    );
  }

  // Rendered for the instant between "we know there is no user" and the
  // redirect taking effect.
  if (!user) return null;

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Attaché</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Signed in as <span className="font-medium">{user.email}</span>
        </p>
      </div>

      <Button
        variant="outline"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        {logout.isPending ? "Signing out…" : "Sign out"}
      </Button>
    </main>
  );
}
