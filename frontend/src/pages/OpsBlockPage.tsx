import { useState } from "react";
import type { FormEvent } from "react";
import { upsertBlock } from "../api/adminApi";

export function OpsBlockPage() {
    const [blockType, setBlockType] = useState("ACCOUNT");
    const [blockValue, setBlockValue] = useState("agent1");
    const [reason, setReason] = useState("manual_ops_action");
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    const onSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setMessage("");
        setError("");
        try {
            await upsertBlock(blockValue, { blockType, status: "ACTIVE", reason });
            setMessage("Block updated.");
        } catch (caught) {
            const nextMessage = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Block update failed")
                : "Block update failed";
            setError(nextMessage);
        }
    };

    return (
        <section>
            <h2>Immediate Block Action</h2>
            <form className="inline-form" onSubmit={onSubmit}>
                <label>
                    Block Type
                    <select value={blockType} onChange={(event) => setBlockType(event.target.value)}>
                        <option value="ACCOUNT">ACCOUNT</option>
                        <option value="IP">IP</option>
                    </select>
                </label>
                <label>
                    Block Value
                    <input value={blockValue} onChange={(event) => setBlockValue(event.target.value)} />
                </label>
                <label>
                    Reason
                    <input value={reason} onChange={(event) => setReason(event.target.value)} />
                </label>
                <button type="submit">Apply</button>
            </form>
            {message && <p>{message}</p>}
            {error && <p className="error">{error}</p>}
        </section>
    );
}
