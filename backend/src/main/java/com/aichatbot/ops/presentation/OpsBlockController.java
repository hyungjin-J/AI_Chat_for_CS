package com.aichatbot.ops.presentation;

import com.aichatbot.global.audit.AuditLogService;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.ops.application.OpsBlockService;
import com.aichatbot.ops.application.OpsEventService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/ops/blocks")
public class OpsBlockController {

    private final OpsBlockService opsBlockService;
    private final OpsEventService opsEventService;
    private final AuditLogService auditLogService;

    public OpsBlockController(
        OpsBlockService opsBlockService,
        OpsEventService opsEventService,
        AuditLogService auditLogService
    ) {
        this.opsBlockService = opsBlockService;
        this.opsEventService = opsEventService;
        this.auditLogService = auditLogService;
    }

    @PutMapping("/{block_id}")
    public OpsBlockResponse upsertBlock(
        @PathVariable("block_id") String blockId,
        @Valid @RequestBody OpsBlockRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        String blockValue = (request.blockValue() == null || request.blockValue().isBlank()) ? blockId : request.blockValue();

        opsBlockService.upsert(
            tenantId,
            request.blockType(),
            blockValue,
            request.status(),
            request.reason(),
            request.expiresAt(),
            actorUserId
        );

        opsEventService.append(
            tenantId,
            "OPS_BLOCK_APPLIED",
            "ops_block_applied",
            1L,
            Map.of("block_type", request.blockType(), "block_value", blockValue)
        );

        auditLogService.write(
            tenantId,
            "OPS_BLOCK_APPLIED",
            actorUserId,
            String.join(",", principal.roles()),
            "OPS_BLOCK",
            blockValue,
            null,
            request
        );

        return new OpsBlockResponse("updated", blockValue, TraceGuard.requireTraceId());
    }

    public record OpsBlockRequest(
        @NotBlank
        String blockType,
        String blockValue,
        String status,
        String reason,
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
        Instant expiresAt
    ) {
    }

    public record OpsBlockResponse(
        String result,
        String blockValue,
        String traceId
    ) {
    }
}

