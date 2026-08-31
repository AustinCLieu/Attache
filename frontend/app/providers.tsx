"use client";

// TanStack Query needs a QueryClient available to every component that calls a
// hook. The client holds the cache, so it must be created once and shared —
// hence a Client Component wrapper that `layout.tsx` renders around everything.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  // useState with an initializer function, not `new QueryClient()` inline:
  // this runs once per browser session instead of on every re-render, so the
  // cache is never thrown away.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Data is considered fresh for a minute, so moving between pages
            // does not refetch everything immediately.
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
