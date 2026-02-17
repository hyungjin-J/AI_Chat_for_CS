package com.aichatbot.billing.presentation;

import com.aichatbot.billing.application.QuotaService;
import com.aichatbot.billing.application.UsageReportService;
import com.aichatbot.billing.presentation.dto.QuotaUpsertRequest;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.tenant.TenantContext;
import jakarta.validation.Valid;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin/tenants")
public class AdminTenantBillingController {

    private final UsageReportService usageReportService;
    private final QuotaService quotaService;

    public AdminTenantBillingController(UsageReportService usageReportService, QuotaService quotaService) {
        this.usageReportService = usageReportService;
        this.quotaService = quotaService;
    }

    @GetMapping("/{tenant_id}/usage-report")
    public UsageReportResponse usageReport(
        @PathVariable("tenant_id") String tenantId,
        @RequestParam(value = "from", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
        @RequestParam(value = "to", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
        @RequestParam(value = "granularity", required = false, defaultValue = "all") String granularity,
        @RequestParam(value = "include_quota", required = false, defaultValue = "true") boolean includeQuota
    ) {
        validateTenantScope(tenantId);
        UsageReportService.UsageReportPayload payload = usageReportService.getUsageReport(
            tenantId,
            from,
            to,
            granularity,
            includeQuota
        );
        return new UsageReportResponse(
            payload.tenantId(),
            payload.daily(),
            payload.monthly(),
            payload.quota(),
            payload.estimatedCost(),
            payload.traceId()
        );
    }

    @PutMapping("/{tenant_id}/quota")
    public QuotaUpsertResponse upsertQuota(
        @PathVariable("tenant_id") String tenantId,
        @Valid @RequestBody QuotaUpsertRequest request,
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        Authentication authentication
    ) {
        validateTenantScope(tenantId);
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "API-007-IDEMPOTENCY-REQUIRED", "Idempotency-Key is required");
        }

        String actorUserId = authentication == null ? "unknown" : authentication.getName();
        String actorRole = resolveActorRole(authentication);
        QuotaService.QuotaUpsertResult result = quotaService.upsertQuota(
            tenantId,
            new QuotaService.QuotaUpsertCommand(
                request.maxQps(),
                request.maxDailyTokens(),
                request.maxMonthlyCost(),
                request.effectiveFrom(),
                request.effectiveTo(),
                quotaService.parseBreachAction(request.breachAction()),
                actorUserId,
                actorRole
            )
        );
        return new QuotaUpsertResponse(result.result(), result.tenantId(), result.traceId());
    }

    private void validateTenantScope(String tenantId) {
        String tenantScope = TenantContext.getTenantKey();
        if (tenantScope == null || !tenantScope.equals(tenantId)) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                "Tenant scope mismatch"
            );
        }
    }

    private String resolveActorRole(Authentication authentication) {
        if (authentication == null || authentication.getAuthorities() == null) {
            return "UNKNOWN";
        }
        List<String> roles = authentication.getAuthorities().stream()
            .map(grantedAuthority -> grantedAuthority.getAuthority())
            .map(value -> value.startsWith("ROLE_") ? value.substring("ROLE_".length()) : value)
            .map(value -> value.toUpperCase(Locale.ROOT))
            .distinct()
            .toList();
        if (roles.isEmpty()) {
            return "UNKNOWN";
        }
        return String.join(",", roles);
    }

    public record UsageReportResponse(
        String tenantId,
        List<UsageReportService.DailyUsageItem> daily,
        List<UsageReportService.MonthlyUsageItem> monthly,
        UsageReportService.QuotaSnapshot quota,
        BigDecimal estimatedCost,
        String traceId
    ) {
    }

    public record QuotaUpsertResponse(
        String result,
        String tenantId,
        String traceId
    ) {
    }
}
