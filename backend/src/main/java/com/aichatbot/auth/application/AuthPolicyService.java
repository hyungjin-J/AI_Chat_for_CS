package com.aichatbot.auth.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import java.util.List;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class AuthPolicyService {

    private final AppProperties appProperties;

    public AuthPolicyService(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    public boolean isRefreshBodyFallbackAllowed(String clientType) {
        if (isProdMode()) {
            if (appProperties.getAuth().isRefreshBodyFallbackProd()) {
                return true;
            }
            return isAllowedClientType(clientType, appProperties.getAuth().getRefreshBodyFallbackProdClientTypes());
        }
        return appProperties.getAuth().isRefreshBodyFallbackDevTest();
    }

    public void validateCsrfOrigin(String originHeader, String clientType) {
        if (originHeader == null || originHeader.isBlank()) {
            if (isProdMode() && !isAllowedClientType(clientType, appProperties.getAuth().getCsrfOriginMissingAllowClientTypes())) {
                throw new ApiException(
                    HttpStatus.FORBIDDEN,
                    "SEC-002-403",
                    ErrorCatalog.messageOf("SEC-002-403"),
                    List.of("csrf_origin_missing")
                );
            }
            return;
        }

        String origin = originHeader.trim().toLowerCase(Locale.ROOT);
        boolean allowed = appProperties.getAuth().getCsrfOriginAllowlist().stream()
            .map(value -> value == null ? "" : value.trim().toLowerCase(Locale.ROOT))
            .anyMatch(origin::equals);
        if (!allowed) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                ErrorCatalog.messageOf("SEC-002-403"),
                List.of("csrf_origin_not_allowed")
            );
        }
    }

    public boolean isProdMode() {
        return "prod".equalsIgnoreCase(appProperties.getAuth().getRuntimeMode());
    }

    private boolean isAllowedClientType(String clientType, List<String> allowlist) {
        if (clientType == null || clientType.isBlank()) {
            return false;
        }
        String normalized = clientType.trim().toLowerCase(Locale.ROOT);
        return allowlist.stream()
            .map(value -> value == null ? "" : value.trim().toLowerCase(Locale.ROOT))
            .anyMatch(normalized::equals);
    }
}

