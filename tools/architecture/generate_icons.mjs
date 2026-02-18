import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import * as icons from "simple-icons";

const OUT_DIR = path.resolve("../../docs/architecture/assets/icons");

const iconRequests = [
    { name: "react", titles: ["React"] },
    { name: "redux", titles: ["Redux"] },
    { name: "typescript", titles: ["TypeScript"] },
    { name: "vite", titles: ["Vite"] },
    { name: "mui", titles: ["MUI", "Material UI"] },
    { name: "axios", titles: ["Axios"] },
    { name: "nginx", titles: ["NGINX"] },
    { name: "spring", titles: ["Spring"] },
    { name: "springboot", titles: ["Spring Boot"] },
    { name: "java", titles: ["OpenJDK", "Java"] },
    { name: "postgresql", titles: ["PostgreSQL"] },
    { name: "redis", titles: ["Redis"] },
    { name: "opensearch", titles: ["OpenSearch"] },
    { name: "elasticsearch", titles: ["Elasticsearch"] },
    { name: "opentelemetry", titles: ["OpenTelemetry"] },
    { name: "kibana", titles: ["Kibana"] },
    { name: "logstash", titles: ["Logstash"] },
    { name: "docker", titles: ["Docker"] },
    { name: "ollama", titles: ["Ollama"] },
    { name: "openai", titles: ["OpenAI"] },
    { name: "notion", titles: ["Notion"] },
];

const placeholders = [
    { name: "badge_fail_closed", label: "FC", color: "#ef4444" },
    { name: "badge_pii", label: "PII", color: "#0ea5e9" },
    { name: "badge_trace", label: "TRACE", color: "#22c55e" },
    { name: "badge_rbac", label: "RBAC", color: "#f59e0b" },
    { name: "badge_budget", label: "BUDGET", color: "#8b5cf6" },
    { name: "ticketing", label: "HELP", color: "#6b7280" },
    { name: "webhook", label: "WH", color: "#6b7280" },
    { name: "ocr", label: "OCR", color: "#6b7280" },
    { name: "reranker", label: "RR", color: "#6b7280" },
];

function getAllSimpleIcons() {
    return Object.values(icons).filter((value) => value && typeof value === "object" && "title" in value && "path" in value);
}

function findSimpleIcon(titles) {
    const catalog = getAllSimpleIcons();
    for (const wantedTitle of titles) {
        const found = catalog.find((entry) => entry.title.toLowerCase() === wantedTitle.toLowerCase());
        if (found) {
            return found;
        }
    }
    return null;
}

function createIconSvg(icon) {
    return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n  <path fill="#${icon.hex}" d="${icon.path}"/>\n</svg>`;
}

function createPlaceholderSvg(label, color) {
    const safeLabel = label.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">\n  <rect x="8" y="8" width="112" height="112" rx="20" fill="${color}"/>\n  <circle cx="64" cy="64" r="48" fill="#ffffff" fill-opacity="0.16"/>\n  <text x="64" y="72" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="#ffffff">${safeLabel}</text>\n</svg>`;
}

async function writeSvgAndPng(name, svgContent) {
    const svgPath = path.join(OUT_DIR, `${name}.svg`);
    const pngPath = path.join(OUT_DIR, `${name}.png`);
    await fs.writeFile(svgPath, svgContent, "utf8");
    await sharp(Buffer.from(svgContent))
        .resize(128, 128, { fit: "contain" })
        .png({ compressionLevel: 9 })
        .toFile(pngPath);
}

async function main() {
    await fs.mkdir(OUT_DIR, { recursive: true });

    for (const request of iconRequests) {
        const icon = findSimpleIcon(request.titles);
        if (icon) {
            const svgContent = createIconSvg(icon);
            await writeSvgAndPng(request.name, svgContent);
            console.log(`Generated icon: ${request.name} (${icon.title})`);
        } else {
            const svgContent = createPlaceholderSvg(request.name.toUpperCase().slice(0, 5), "#6b7280");
            await writeSvgAndPng(request.name, svgContent);
            console.log(`Generated placeholder icon: ${request.name}`);
        }
    }

    for (const placeholder of placeholders) {
        await writeSvgAndPng(placeholder.name, createPlaceholderSvg(placeholder.label, placeholder.color));
        console.log(`Generated placeholder badge/icon: ${placeholder.name}`);
    }
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
