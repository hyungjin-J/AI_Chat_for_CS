package com.aichatbot.global.util;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;

public final class UuidParser {

    private UuidParser() {
    }

    public static UUID parseRequired(String raw, String fieldName) {
        try {
            return UUID.fromString(raw);
        } catch (Exception exception) {
            // Why: 컨트롤러 경계에서 UUID 형식을 먼저 검증해야 서비스/DB까지 잘못된 문자열이 내려가지 않습니다.
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of(fieldName + "_invalid")
            );
        }
    }
}
