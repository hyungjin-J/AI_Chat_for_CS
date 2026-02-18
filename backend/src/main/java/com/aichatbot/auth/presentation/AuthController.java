package com.aichatbot.auth.presentation;

import com.aichatbot.auth.application.AuthService;
import com.aichatbot.auth.presentation.dto.AuthTokenResponse;
import com.aichatbot.auth.presentation.dto.LoginRequest;
import com.aichatbot.auth.presentation.dto.LogoutRequest;
import com.aichatbot.auth.presentation.dto.RefreshRequest;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.idempotency.IdempotencyService;
import com.aichatbot.global.tenant.TenantContext;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final IdempotencyService idempotencyService;

    public AuthController(AuthService authService, IdempotencyService idempotencyService) {
        this.authService = authService;
        this.idempotencyService = idempotencyService;
    }

    @PostMapping("/login")
    public ResponseEntity<AuthTokenResponse> login(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody LoginRequest request
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        AuthTokenResponse response = idempotencyService.execute(
            "auth:login:" + TenantContext.getTenantKey(),
            key,
            () -> authService.login(TenantContext.getTenantKey(), request)
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthTokenResponse> refresh(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody RefreshRequest request
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        AuthTokenResponse response = idempotencyService.execute(
            "auth:refresh:" + TenantContext.getTenantKey(),
            key,
            () -> authService.refresh(TenantContext.getTenantKey(), request)
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody LogoutRequest request
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        idempotencyService.execute(
            "auth:logout:" + TenantContext.getTenantKey(),
            key,
            () -> {
                authService.logout(request);
                return new LogoutResult("accepted");
            }
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(new LogoutResult("accepted"));
    }

    private String requireIdempotencyKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("idempotency_key_required")
            );
        }
        return idempotencyKey.trim();
    }

    private record LogoutResult(String result) {
    }
}
