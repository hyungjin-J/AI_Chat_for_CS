import exec from "k6/execution";
import http from "k6/http";
import { Counter, Rate, Trend } from "k6/metrics";
import { check, sleep } from "k6";

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8080").replace(/\/+$/, "");
const TENANT_KEY = __ENV.TENANT_KEY || "demo-tenant";
const LOGIN_ID = __ENV.LOGIN_ID || "agent1";
const PASSWORD = __ENV.PASSWORD || "agent1-pass";
const CHANNEL_ID = __ENV.CHANNEL_ID || "test";
const TOP_K = Number(__ENV.TOP_K || "3");
const THINK_TIME_MS = Number(__ENV.THINK_TIME_MS || "200");
const REQUEST_TIMEOUT = __ENV.REQUEST_TIMEOUT || "120s";

const SSE_VUS = Number(__ENV.SSE_VUS || "2");
const SSE_DURATION = __ENV.SSE_DURATION || "1m";
const RATE_LIMIT_START_TIME = __ENV.RATE_LIMIT_START_TIME || SSE_DURATION;
const RATE_LIMIT_ITERATIONS = Number(__ENV.RATE_LIMIT_ITERATIONS || "6");
const RATE_LIMIT_EXPECTED_STATUS = Number(__ENV.RATE_LIMIT_EXPECTED_STATUS || "429");
const RATE_LIMIT_EXPECTED_ERROR_CODE = __ENV.RATE_LIMIT_EXPECTED_ERROR_CODE || "API-008-429-SSE";

const firstTokenMs = new Trend("first_token_ms", true);
const doneSuccessRate = new Rate("sse_done_success_rate");
const errorRate = new Rate("sse_error_rate");
const safeResponseRate = new Rate("sse_safe_response_rate");
const streamHttp200Rate = new Rate("sse_http_200_rate");
const messageAcceptedRate = new Rate("message_accepted_202_rate");
const rateLimit429Rate = new Rate("rate_limit_429_rate");
const rateLimitHeadersOkRate = new Rate("rate_limit_headers_ok_rate");
const rateLimitContractOkRate = new Rate("rate_limit_contract_ok_rate");
const sseStreamRequestsTotal = new Counter("sse_stream_requests_total");

export const options = {
    scenarios: {
        sse_stream_load: {
            executor: "constant-vus",
            vus: SSE_VUS,
            duration: SSE_DURATION,
            exec: "sseStreamLoad",
            gracefulStop: "20s",
        },
        rate_limit_probe: {
            executor: "shared-iterations",
            vus: 1,
            iterations: RATE_LIMIT_ITERATIONS,
            startTime: RATE_LIMIT_START_TIME,
            exec: "rateLimitProbe",
        },
    },
    summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "max"],
};

function randomHex(length) {
    let out = "";
    for (let idx = 0; idx < length; idx += 1) {
        out += Math.floor(Math.random() * 16).toString(16);
    }
    return out;
}

function makeUuidV4() {
    const part1 = randomHex(8);
    const part2 = randomHex(4);
    const part3 = `4${randomHex(3)}`;
    const variant = (8 + Math.floor(Math.random() * 4)).toString(16);
    const part4 = `${variant}${randomHex(3)}`;
    const part5 = randomHex(12);
    return `${part1}-${part2}-${part3}-${part4}-${part5}`;
}

function safeJsonParse(text) {
    try {
        return JSON.parse(text);
    } catch (_) {
        return null;
    }
}

function makeHeaders(token, withIdempotency, traceId) {
    const headers = {
        "Content-Type": "application/json",
        "X-Trace-Id": traceId || makeUuidV4(),
        "X-Tenant-Key": TENANT_KEY,
    };
    if (withIdempotency) {
        headers["Idempotency-Key"] = makeUuidV4();
    }
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }
    return headers;
}

function postJson(path, payload, token, withIdempotency, tags) {
    return http.post(`${BASE_URL}${path}`, JSON.stringify(payload), {
        headers: makeHeaders(token, withIdempotency),
        timeout: REQUEST_TIMEOUT,
        tags: tags || {},
    });
}

function createSession(token, tagSuffix) {
    const response = postJson("/v1/sessions", {}, token, true, {
        scenario: tagSuffix,
        endpoint: "create_session",
    });
    const ok = check(response, {
        "create_session_status_201": (res) => res.status === 201,
    });
    if (!ok) {
        return "";
    }
    const payload = safeJsonParse(response.body);
    return payload && typeof payload.session_id === "string" ? payload.session_id : "";
}

function postMessage(token, sessionId, text, tagSuffix) {
    const response = postJson(
        `/v1/sessions/${sessionId}/messages`,
        {
            text: text,
            top_k: TOP_K,
            client_nonce: `perf-${makeUuidV4()}`,
        },
        token,
        true,
        {
            scenario: tagSuffix,
            endpoint: "post_message",
        },
    );
    const accepted = response.status === 202;
    messageAcceptedRate.add(accepted ? 1 : 0);
    check(response, {
        "post_message_status_202": (res) => res.status === 202,
    });
    if (!accepted) {
        return "";
    }
    const payload = safeJsonParse(response.body);
    return payload && typeof payload.id === "string" ? payload.id : "";
}

function streamMessage(token, sessionId, messageId, tagSuffix) {
    const response = http.get(`${BASE_URL}/v1/sessions/${sessionId}/messages/${messageId}/stream`, {
        headers: makeHeaders(token, false),
        timeout: REQUEST_TIMEOUT,
        tags: {
            scenario: tagSuffix,
            endpoint: "sse_stream",
        },
    });
    sseStreamRequestsTotal.add(1);
    const isHttp200 = response.status === 200;
    streamHttp200Rate.add(isHttp200 ? 1 : 0);

    if (!isHttp200) {
        doneSuccessRate.add(0);
        errorRate.add(1);
        safeResponseRate.add(0);
        return;
    }

    const body = response.body || "";
    const hasToken = body.indexOf("event:token") >= 0;
    const hasDone = body.indexOf("event:done") >= 0;
    const hasError = body.indexOf("event:error") >= 0;
    const hasSafeResponse = body.indexOf("event:safe_response") >= 0;

    // k6 does not expose incremental SSE chunks as they arrive. We use TTFB
    // as a deterministic first-token latency proxy.
    if (hasToken) {
        firstTokenMs.add(response.timings.waiting);
    }
    doneSuccessRate.add(hasDone ? 1 : 0);
    errorRate.add(hasError ? 1 : 0);
    safeResponseRate.add(hasSafeResponse ? 1 : 0);
}

function extractErrorCode(text) {
    const payload = safeJsonParse(text || "");
    if (!payload || typeof payload !== "object") {
        return "";
    }
    return typeof payload.error_code === "string" ? payload.error_code : "";
}

function hasHeader(headers, name) {
    const expected = name.toLowerCase();
    const entries = Object.entries(headers || {});
    for (let idx = 0; idx < entries.length; idx += 1) {
        const [key, rawValue] = entries[idx];
        if (String(key).toLowerCase() !== expected) {
            continue;
        }
        if (Array.isArray(rawValue)) {
            return rawValue.length > 0 && String(rawValue[0] || "").trim() !== "";
        }
        return String(rawValue || "").trim() !== "";
    }
    return false;
}

function requiredRateLimitHeadersExist(headers) {
    return (
        hasHeader(headers, "Retry-After") &&
        hasHeader(headers, "X-RateLimit-Limit") &&
        hasHeader(headers, "X-RateLimit-Remaining") &&
        hasHeader(headers, "X-RateLimit-Reset")
    );
}

export function setup() {
    const loginResponse = postJson(
        "/v1/auth/login",
        {
            login_id: LOGIN_ID,
            password: PASSWORD,
            channel_id: CHANNEL_ID,
            client_nonce: `perf-login-${makeUuidV4()}`,
        },
        "",
        true,
        {
            scenario: "setup",
            endpoint: "auth_login",
        },
    );
    check(loginResponse, {
        "login_status_201": (res) => res.status === 201,
    });
    const loginPayload = safeJsonParse(loginResponse.body);
    const token = loginPayload && typeof loginPayload.access_token === "string" ? loginPayload.access_token : "";
    if (!token) {
        throw new Error("setup_login_failed");
    }

    const probeSessionId = createSession(token, "setup");
    const probeMessageId = postMessage(token, probeSessionId, "perf probe for rate-limit contract", "setup");
    if (!probeSessionId || !probeMessageId) {
        throw new Error("setup_probe_session_or_message_failed");
    }

    return {
        token: token,
        probe_session_id: probeSessionId,
        probe_message_id: probeMessageId,
    };
}

export function sseStreamLoad(data) {
    const token = data.token;
    const sessionId = createSession(token, "sse_stream_load");
    if (!sessionId) {
        return;
    }
    const messageId = postMessage(
        token,
        sessionId,
        `sse load iteration vu=${exec.vu.idInTest} iter=${exec.scenario.iterationInTest}`,
        "sse_stream_load",
    );
    if (!messageId) {
        return;
    }
    streamMessage(token, sessionId, messageId, "sse_stream_load");
    if (THINK_TIME_MS > 0) {
        sleep(THINK_TIME_MS / 1000);
    }
}

export function rateLimitProbe(data) {
    const token = data.token;
    const sessionId = createSession(token, "rate_limit_probe");
    if (!sessionId) {
        rateLimit429Rate.add(0);
        rateLimitHeadersOkRate.add(0);
        rateLimitContractOkRate.add(0);
        return;
    }

    const messageId = postMessage(token, sessionId, "trigger sse concurrency policy", "rate_limit_probe");
    if (!messageId) {
        rateLimit429Rate.add(0);
        rateLimitHeadersOkRate.add(0);
        rateLimitContractOkRate.add(0);
        return;
    }

    const streamUrl = `${BASE_URL}/v1/sessions/${sessionId}/messages/${messageId}/stream`;
    const responses = http.batch([
        [
            "GET",
            streamUrl,
            null,
            {
                headers: makeHeaders(token, false, makeUuidV4()),
                timeout: REQUEST_TIMEOUT,
                tags: { scenario: "rate_limit_probe", endpoint: "sse_stream_a" },
            },
        ],
        [
            "GET",
            streamUrl,
            null,
            {
                headers: makeHeaders(token, false, makeUuidV4()),
                timeout: REQUEST_TIMEOUT,
                tags: { scenario: "rate_limit_probe", endpoint: "sse_stream_b" },
            },
        ],
        [
            "GET",
            streamUrl,
            null,
            {
                headers: makeHeaders(token, false, makeUuidV4()),
                timeout: REQUEST_TIMEOUT,
                tags: { scenario: "rate_limit_probe", endpoint: "sse_stream_c" },
            },
        ],
    ]);

    let throttledResponse = null;
    for (let idx = 0; idx < responses.length; idx += 1) {
        if (responses[idx].status === RATE_LIMIT_EXPECTED_STATUS) {
            throttledResponse = responses[idx];
            break;
        }
    }

    const sawExpected429 = throttledResponse !== null;
    rateLimit429Rate.add(sawExpected429 ? 1 : 0);

    if (!sawExpected429) {
        rateLimitHeadersOkRate.add(0);
        rateLimitContractOkRate.add(0);
        return;
    }

    const headersOk = requiredRateLimitHeadersExist(throttledResponse.headers);
    const errorCode = extractErrorCode(throttledResponse.body);
    const contractOk = headersOk && errorCode === RATE_LIMIT_EXPECTED_ERROR_CODE;
    rateLimitHeadersOkRate.add(headersOk ? 1 : 0);
    rateLimitContractOkRate.add(contractOk ? 1 : 0);
}

