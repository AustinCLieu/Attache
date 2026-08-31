"use client";

// TanStack Query hooks. Components call these instead of `api` directly, so
// caching, loading/error state, and refetch-after-mutation are handled in one
// place rather than repeated in every component.

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ApiError, api } from "./api";
import type { LoginPayload, SignupPayload, User } from "./types";

/** Cache key for the logged-in user. Anything that changes them invalidates it. */
export const currentUserKey = ["currentUser"] as const;

/**
 * The logged-in user, or `null` when nobody is signed in.
 *
 * A 401 is an expected answer here, not a failure — it is the normal response
 * for a signed-out visitor — so it resolves to `null` instead of throwing, and
 * retries are disabled so a signed-out page does not retry three times first.
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: async (): Promise<User | null> => {
      try {
        return await api.get<User>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: LoginPayload) => api.post<User>("/auth/login", payload),

    // The server has set the session cookie by now. Writing the user straight
    // into the cache means the UI updates without a second round trip.
    onSuccess: (user) => queryClient.setQueryData(currentUserKey, user),
  });
}

export function useSignup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SignupPayload) => api.post<User>("/auth/signup", payload),
    onSuccess: (user) => queryClient.setQueryData(currentUserKey, user),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),

    // Drop every cached query, not just the user: whatever else is cached
    // belonged to the account that just signed out.
    onSuccess: () => {
      queryClient.setQueryData(currentUserKey, null);
      queryClient.clear();
    },
  });
}
