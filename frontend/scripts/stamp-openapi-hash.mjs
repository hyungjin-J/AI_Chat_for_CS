import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const openapiPath = path.resolve(frontendRoot, "..", "openapi", "openapi.yaml");
const generatedTypesPath = path.resolve(frontendRoot, "src", "api", "generated", "openapi.ts");

function normalizeText(text) {
    return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function sha256Hex(text) {
    return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function stripExistingHeader(text) {
    const lines = normalizeText(text).split("\n");
    const filtered = lines.filter((line, idx) => {
        if (idx > 4) {
            return true;
        }
        const lowered = line.trim().toLowerCase();
        if (lowered.startsWith("// auto-generated file")) {
            return false;
        }
        if (lowered.startsWith("// source-openapi-sha256:")) {
            return false;
        }
        return true;
    });
    return filtered.join("\n");
}

async function main() {
    const openapiRaw = await fs.readFile(openapiPath, "utf8");
    const openapiHash = sha256Hex(normalizeText(openapiRaw));

    const generatedRaw = await fs.readFile(generatedTypesPath, "utf8");
    const body = stripExistingHeader(generatedRaw);
    const next = [
        "// AUTO-GENERATED FILE - DO NOT EDIT",
        `// source-openapi-sha256: ${openapiHash}`,
        body.trimStart(),
        "",
    ].join("\n");

    await fs.writeFile(generatedTypesPath, next, "utf8");
    process.stdout.write(`openapi_types_hash_stamped=${openapiHash}\n`);
}

main().catch((error) => {
    process.stderr.write(`${String(error)}\n`);
    process.exit(1);
});

