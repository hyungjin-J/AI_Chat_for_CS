import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { activateMfaTotp, enrollMfaTotp, login, verifyMfa } from "../api/authApi";
import { getAuthState } from "../auth/authStore";

export function LoginPage() {
    const navigate = useNavigate();
    const [tenantKey, setTenantKey] = useState("demo-tenant");
    const [loginId, setLoginId] = useState("ops1");
    const [password, setPassword] = useState("ops1-pass");
    const [clientType, setClientType] = useState("web");
    const [mfaStatus, setMfaStatus] = useState<"" | "mfa_required" | "mfa_setup_required">("");
    const [mfaTicketId, setMfaTicketId] = useState("");
    const [totpSecret, setTotpSecret] = useState("");
    const [otpAuthUri, setOtpAuthUri] = useState("");
    const [totpCode, setTotpCode] = useState("");
    const [recoveryCode, setRecoveryCode] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const canSubmit = useMemo(() => {
        return Boolean(tenantKey.trim() && loginId.trim() && password.trim()) && !loading;
    }, [tenantKey, loginId, password, loading]);

    const onSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setError("");
        setLoading(true);
        try {
            const result = await login({ tenantKey, loginId, password, clientType });
            if (result.status === "mfa_required" || result.status === "mfa_setup_required") {
                setMfaStatus(result.status);
                setMfaTicketId(result.mfaTicketId);
                if (result.status === "mfa_setup_required") {
                    const enroll = await enrollMfaTotp(tenantKey, result.mfaTicketId);
                    setTotpSecret(enroll.totp_secret);
                    setOtpAuthUri(enroll.otpauth_uri);
                }
                return;
            }
            const roles = getAuthState().roles.map((role) => role.toUpperCase());
            if (roles.includes("OPS") || roles.includes("ADMIN")) {
                navigate("/admin/dashboard", { replace: true });
                return;
            }
            navigate("/forbidden", { replace: true });
        } catch (caught) {
            const fallback = "Login failed";
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? fallback)
                : fallback;
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const onSubmitMfa = async (event: FormEvent) => {
        event.preventDefault();
        setError("");
        setLoading(true);
        try {
            if (mfaStatus === "mfa_setup_required") {
                await activateMfaTotp(tenantKey, mfaTicketId, totpCode);
            } else {
                await verifyMfa(tenantKey, mfaTicketId, totpCode, recoveryCode || undefined);
            }
            const roles = getAuthState().roles.map((role) => role.toUpperCase());
            if (roles.includes("OPS") || roles.includes("ADMIN")) {
                navigate("/admin/dashboard", { replace: true });
                return;
            }
            navigate("/forbidden", { replace: true });
        } catch (caught) {
            const fallback = "MFA verification failed";
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? fallback)
                : fallback;
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    if (mfaStatus) {
        return (
            <main className="login-page">
                <form className="login-panel" onSubmit={onSubmitMfa}>
                    <h1>MFA Verification</h1>
                    {mfaStatus === "mfa_setup_required" && (
                        <>
                            <p>Scan secret in authenticator app, then enter verification code.</p>
                            <label>
                                TOTP Secret
                                <input value={totpSecret} readOnly />
                            </label>
                            <label>
                                OTPAuth URI
                                <input value={otpAuthUri} readOnly />
                            </label>
                        </>
                    )}
                    {mfaStatus === "mfa_required" && <p>Enter TOTP code or recovery code.</p>}
                    <label>
                        TOTP Code
                        <input value={totpCode} onChange={(event) => setTotpCode(event.target.value)} />
                    </label>
                    <label>
                        Recovery Code (Optional)
                        <input value={recoveryCode} onChange={(event) => setRecoveryCode(event.target.value)} />
                    </label>
                    <button type="submit" disabled={loading}>
                        {loading ? "Verifying..." : "Verify and Login"}
                    </button>
                    {error && <p className="error">{error}</p>}
                </form>
            </main>
        );
    }

    return (
        <main className="login-page">
            <form className="login-panel" onSubmit={onSubmit}>
                <h1>Login</h1>
                <p>Use OPS/ADMIN account to access the console.</p>

                <label>
                    Tenant Key
                    <input value={tenantKey} onChange={(event) => setTenantKey(event.target.value)} />
                </label>
                <label>
                    Login ID
                    <input value={loginId} onChange={(event) => setLoginId(event.target.value)} />
                </label>
                <label>
                    Password
                    <input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                    />
                </label>
                <label>
                    Client Type
                    <input value={clientType} onChange={(event) => setClientType(event.target.value)} />
                </label>

                <button type="submit" disabled={!canSubmit}>
                    {loading ? "Logging in..." : "Login"}
                </button>
                {error && <p className="error">{error}</p>}
            </form>
        </main>
    );
}
