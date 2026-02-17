package com.aichatbot.global.privacy;

import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class PiiMaskingService {

    private static final Pattern EMAIL_PATTERN = Pattern.compile("([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+)");
    private static final Pattern PHONE_PATTERN = Pattern.compile("(\\+?\\d[\\d\\-\\s]{7,}\\d)");
    private static final Pattern ORDER_PATTERN = Pattern.compile("\\b[A-Z]{2,5}-?\\d{4,12}\\b");

    public String mask(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }
        String masked = EMAIL_PATTERN.matcher(raw).replaceAll("***@***");
        masked = PHONE_PATTERN.matcher(masked).replaceAll("***-****");
        masked = ORDER_PATTERN.matcher(masked).replaceAll("ORDER-***");
        return masked;
    }
}

