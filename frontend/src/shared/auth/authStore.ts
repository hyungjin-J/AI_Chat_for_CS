import { useSyncExternalStore } from "react";

export type AuthState = {
    tenantKey: string;
    accessToken: string;
    sessionFamilyId: string;
    roles: string[];
    adminLevel: string;
    permissionVersion: number;
    stalePermission401Count: number;
};

const STORAGE_KEY = "aichatbot_auth_state_v1";

let state: AuthState = loadInitialState();
const listeners = new Set<() => void>();

function loadInitialState(): AuthState {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return emptyState();
        }
        const parsed = JSON.parse(raw) as Partial<AuthState>;
        return {
            tenantKey: parsed.tenantKey ?? "",
            accessToken: parsed.accessToken ?? "",
            sessionFamilyId: parsed.sessionFamilyId ?? "",
            roles: Array.isArray(parsed.roles) ? parsed.roles.map(String) : [],
            adminLevel: parsed.adminLevel ?? "",
            permissionVersion: Number(parsed.permissionVersion ?? 0),
            stalePermission401Count: Number(parsed.stalePermission401Count ?? 0),
        };
    } catch {
        return emptyState();
    }
}

function emptyState(): AuthState {
    return {
        tenantKey: "",
        accessToken: "",
        sessionFamilyId: "",
        roles: [],
        adminLevel: "",
        permissionVersion: 0,
        stalePermission401Count: 0,
    };
}

function emit() {
    listeners.forEach((listener) => listener());
}

function persist() {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function getAuthState(): AuthState {
    return state;
}

export function setAuthState(next: Partial<AuthState>) {
    state = { ...state, ...next };
    persist();
    emit();
}

export function clearAuthState() {
    state = emptyState();
    persist();
    emit();
}

export function resetStale401Count() {
    setAuthState({ stalePermission401Count: 0 });
}

export function incrementStale401Count(): number {
    const nextCount = state.stalePermission401Count + 1;
    setAuthState({ stalePermission401Count: nextCount });
    return nextCount;
}

export function hasAnyRole(...targetRoles: string[]): boolean {
    const roleSet = new Set(state.roles.map((role) => role.toUpperCase()));
    return targetRoles.some((role) => roleSet.has(role.toUpperCase()));
}

export function useAuthState(): AuthState {
    return useSyncExternalStore(
        (listener) => {
            listeners.add(listener);
            return () => listeners.delete(listener);
        },
        () => state,
    );
}
