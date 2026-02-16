export function maskSensitiveText(input: string): string {
    if (!input) {
        return input;
    }

    // 왜 필요한가: UI 로그에 원문 PII가 남으면 화면 캡처/운영 로그로 재유출될 수 있다.
    let masked = input;
    masked = masked.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[EMAIL_MASKED]");
    masked = masked.replace(/\b01[0-9]-?\d{3,4}-?\d{4}\b/g, "[PHONE_MASKED]");
    masked = masked.replace(/\b\d{2,3}-\d{2,4}-\d{4}\b/g, "[PHONE_MASKED]");
    masked = masked.replace(/\b\d{6,}\b/g, "[NUMBER_MASKED]");
    return masked;
}
