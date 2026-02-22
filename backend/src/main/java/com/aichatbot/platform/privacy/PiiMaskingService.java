package com.aichatbot.platform.privacy;

import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class PiiMaskingService {

    private static final Pattern EMAIL_PATTERN = Pattern.compile("([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+)");
    private static final Pattern PHONE_PATTERN = Pattern.compile("(\\+?\\d[\\d\\-\\s]{7,}\\d)");
    private static final Pattern ORDER_PATTERN = Pattern.compile("\\b[A-Z]{2,5}-?\\d{4,12}\\b");
    private static final Pattern IPV4_PATTERN = Pattern.compile("\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b");
    private static final Pattern ADDRESS_PATTERN = Pattern.compile(
        "(?i)(\\baddress\\s*[:=]?\\s*)([A-Za-z0-9가-힣\\-\\s,]{6,})"
    );

    public String mask(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }
        String masked = EMAIL_PATTERN.matcher(raw).replaceAll("***@***");
        masked = PHONE_PATTERN.matcher(masked).replaceAll("***-****");
        masked = ORDER_PATTERN.matcher(masked).replaceAll("ORDER-***");
        masked = IPV4_PATTERN.matcher(masked).replaceAll("***.***.***.***");
        // Why: Address-like free text often carries direct PII; keep only prefix and mask body.
        masked = ADDRESS_PATTERN.matcher(masked).replaceAll("$1ADDRESS-***");
        return masked;
    }
}
