package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.global.privacy.PiiMaskingService;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class GenerationLogService {

    private final GenerationLogRepository generationLogRepository;
    private final PiiMaskingService piiMaskingService;
    private final Clock clock;

    @Autowired
    public GenerationLogService(GenerationLogRepository generationLogRepository, PiiMaskingService piiMaskingService) {
        this(generationLogRepository, piiMaskingService, Clock.systemUTC());
    }

    GenerationLogService(GenerationLogRepository generationLogRepository, PiiMaskingService piiMaskingService, Clock clock) {
        this.generationLogRepository = generationLogRepository;
        this.piiMaskingService = piiMaskingService;
        this.clock = clock;
    }

    public GenerationLogEntry record(
        String messageId,
        String providerId,
        String modelId,
        int inputTokens,
        int outputTokens,
        int toolCalls,
        String promptRaw
    ) {
        String traceId = requireTraceId();
        String tenantId = requireTenantId();
        String maskedPrompt = piiMaskingService.mask(promptRaw);
        GenerationLogEntry entry = new GenerationLogEntry(
            UUID.randomUUID().toString(),
            tenantId,
            messageId,
            providerId,
            modelId,
            inputTokens,
            outputTokens,
            toolCalls,
            maskedPrompt,
            traceId,
            Instant.now(clock)
        );
        generationLogRepository.save(entry);
        return entry;
    }

    private String requireTraceId() {
        String traceId = TraceContext.getTraceId();
        if (traceId == null || traceId.isBlank()) {
            throw new IllegalStateException("trace_id is required for generation logs");
        }
        return traceId;
    }

    private String requireTenantId() {
        String tenantId = TenantContext.getTenantKey();
        if (tenantId == null || tenantId.isBlank()) {
            throw new IllegalStateException("tenant_key is required for generation logs");
        }
        return tenantId;
    }
}
