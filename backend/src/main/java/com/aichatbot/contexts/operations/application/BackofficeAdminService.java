package com.aichatbot.contexts.operations.application;

import com.aichatbot.contexts.operations.domain.AdminResourceRow;
import com.aichatbot.contexts.operations.domain.OpsMetricSummaryRow;
import com.aichatbot.contexts.operations.domain.OpsRollbackRow;
import com.aichatbot.contexts.operations.domain.OpsTraceRow;
import com.aichatbot.platform.error.ApiException;
import com.aichatbot.platform.privacy.PiiMaskingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class BackofficeAdminService {

    private static final String TYPE_TEMPLATE = "TEMPLATE";
    private static final String TYPE_POLICY = "POLICY";
    private static final String TYPE_MODEL = "MODEL";
    private static final String TYPE_ROUTING_RULE = "ROUTING_RULE";
    private static final String TYPE_PROVIDER_KEY = "PROVIDER_KEY";
    private static final String TYPE_PROVIDER_CONFIG = "PROVIDER_CONFIG";
    private static final String TYPE_VERSION_BUNDLE = "VERSION_BUNDLE";
    private static final String TYPE_TOOL_ALLOWLIST = "TOOL_ALLOWLIST";
    private static final String TYPE_ERROR_CATALOG = "ERROR_CATALOG";
    private static final String TYPE_DEPLOY_APPROVAL = "DEPLOY_APPROVAL";
    private static final String TYPE_CHANGE_NOTICE = "CHANGE_NOTICE";

    private final BackofficeAdminPort repository;
    private final OpsEventService opsEventService;
    private final PiiMaskingService piiMaskingService;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public BackofficeAdminService(
        BackofficeAdminPort repository,
        OpsEventService opsEventService,
        PiiMaskingService piiMaskingService,
        ObjectMapper objectMapper
    ) {
        this(repository, opsEventService, piiMaskingService, objectMapper, Clock.systemUTC());
    }

    BackofficeAdminService(
        BackofficeAdminPort repository,
        OpsEventService opsEventService,
        PiiMaskingService piiMaskingService,
        ObjectMapper objectMapper,
        Clock clock
    ) {
        this.repository = repository;
        this.opsEventService = opsEventService;
        this.piiMaskingService = piiMaskingService;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    public List<AdminResourceView> listTemplates(UUID tenantId, int limit, int offset) {
        return toViews(repository.listResources(tenantId, TYPE_TEMPLATE, clampLimit(limit), Math.max(0, offset)));
    }

    public AdminResourceView createTemplate(UUID tenantId, UUID actorUserId, String name, String body) {
        String templateId = UUID.randomUUID().toString();
        Map<String, Object> payload = Map.of(
            "name", normalize(name, "template"),
            "body", piiMaskingService.mask(normalize(body, ""))
        );
        return toView(upsertResource(
            tenantId,
            TYPE_TEMPLATE,
            templateId,
            "DRAFT",
            payload,
            false,
            null,
            actorUserId
        ));
    }

    public AdminResourceView approveTemplate(UUID tenantId, UUID actorUserId, String templateId) {
        return toView(changeTemplateState(tenantId, actorUserId, templateId, "APPROVED", false));
    }

    public AdminResourceView deployTemplate(UUID tenantId, UUID actorUserId, String templateId) {
        return toView(changeTemplateState(tenantId, actorUserId, templateId, "DEPLOYED", true));
    }

    public AdminResourceView rollbackTemplate(UUID tenantId, UUID actorUserId, String templateId) {
        return toView(changeTemplateState(tenantId, actorUserId, templateId, "ROLLED_BACK", false));
    }

    public AdminResourceView updatePolicy(UUID tenantId, UUID actorUserId, String policyId, Map<String, Object> payload) {
        return toView(upsertResource(
            tenantId,
            TYPE_POLICY,
            policyId,
            "ACTIVE",
            payload == null ? Map.of() : payload,
            true,
            null,
            actorUserId
        ));
    }

    public List<AdminResourceView> listModels(UUID tenantId, int limit, int offset) {
        return toViews(repository.listResources(tenantId, TYPE_MODEL, clampLimit(limit), Math.max(0, offset)));
    }

    public AdminResourceView createModel(UUID tenantId, UUID actorUserId, String provider, String modelName) {
        String modelId = UUID.randomUUID().toString();
        return toView(upsertResource(
            tenantId,
            TYPE_MODEL,
            modelId,
            "CREATED",
            Map.of("provider", normalize(provider, "unknown"), "model_name", normalize(modelName, "default")),
            false,
            null,
            actorUserId
        ));
    }

    public AdminResourceView activateModel(UUID tenantId, UUID actorUserId, String modelId) {
        AdminResourceRow current = requireResource(tenantId, TYPE_MODEL, modelId);
        repository.deactivateResourcesByType(tenantId, TYPE_MODEL, actorUserId, Instant.now(clock));
        return toView(upsertResource(
            tenantId,
            TYPE_MODEL,
            modelId,
            "ACTIVE",
            parsePayload(current.payloadJson()),
            true,
            null,
            actorUserId
        ));
    }

    public AdminResourceView rollbackModel(UUID tenantId, UUID actorUserId, String modelId) {
        AdminResourceRow current = requireResource(tenantId, TYPE_MODEL, modelId);
        return toView(upsertResource(
            tenantId,
            TYPE_MODEL,
            modelId,
            "ROLLED_BACK",
            parsePayload(current.payloadJson()),
            false,
            null,
            actorUserId
        ));
    }

    public AdminResourceView upsertRoutingRule(
        UUID tenantId,
        UUID actorUserId,
        String ruleId,
        Map<String, Object> payload
    ) {
        return toView(upsertResource(
            tenantId,
            TYPE_ROUTING_RULE,
            ruleId,
            "ACTIVE",
            payload == null ? Map.of() : payload,
            true,
            null,
            actorUserId
        ));
    }

    public RoutingRuleTestView testRoutingRule(UUID tenantId, String prompt, String requestedRuleId) {
        List<AdminResourceRow> rules = repository.listResources(tenantId, TYPE_ROUTING_RULE, 100, 0);
        if (rules.isEmpty()) {
            return new RoutingRuleTestView("NO_RULE", null, normalize(prompt, ""));
        }
        AdminResourceRow selected = requestedRuleId == null || requestedRuleId.isBlank()
            ? rules.get(0)
            : rules.stream().filter(row -> requestedRuleId.equals(row.resourceKey())).findFirst().orElse(rules.get(0));
        return new RoutingRuleTestView("MATCHED", selected.resourceKey(), normalize(prompt, ""));
    }

    public AdminResourceView upsertProviderKey(
        UUID tenantId,
        UUID actorUserId,
        String provider,
        String secretRef
    ) {
        return toView(upsertResource(
            tenantId,
            TYPE_PROVIDER_KEY,
            provider,
            "ACTIVE",
            Map.of("secret_ref", piiMaskingService.mask(normalize(secretRef, "secret://unset"))),
            true,
            null,
            actorUserId
        ));
    }

    public AdminResourceView rotateProviderKey(UUID tenantId, UUID actorUserId, String provider) {
        AdminResourceRow current = requireResource(tenantId, TYPE_PROVIDER_KEY, provider);
        return toView(upsertResource(
            tenantId,
            TYPE_PROVIDER_KEY,
            provider,
            "ROTATED",
            parsePayload(current.payloadJson()),
            true,
            Instant.now(clock),
            actorUserId
        ));
    }

    public AdminResourceView bindProviderSecretRef(
        UUID tenantId,
        UUID actorUserId,
        String providerId,
        String secretRef
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("secret_ref", piiMaskingService.mask(normalize(secretRef, "secret://unset")));
        payload.put("kill_switch", false);
        return toView(upsertResource(
            tenantId,
            TYPE_PROVIDER_CONFIG,
            providerId,
            "CONFIGURED",
            payload,
            true,
            null,
            actorUserId
        ));
    }

    public AdminResourceView setProviderKillSwitch(
        UUID tenantId,
        UUID actorUserId,
        String provider,
        boolean enabled
    ) {
        Optional<AdminResourceRow> existing = repository.findResource(tenantId, TYPE_PROVIDER_CONFIG, provider);
        Map<String, Object> payload = existing
            .map(row -> parsePayload(row.payloadJson()))
            .orElseGet(LinkedHashMap::new);
        payload.put("kill_switch", enabled);
        return toView(upsertResource(
            tenantId,
            TYPE_PROVIDER_CONFIG,
            provider,
            enabled ? "KILL_SWITCH_ON" : "KILL_SWITCH_OFF",
            payload,
            true,
            null,
            actorUserId
        ));
    }

    public List<ProviderHealthView> listProviderHealth(UUID tenantId) {
        List<AdminResourceRow> configs = repository.listResources(tenantId, TYPE_PROVIDER_CONFIG, 100, 0);
        List<AdminResourceRow> keys = repository.listResources(tenantId, TYPE_PROVIDER_KEY, 100, 0);
        List<AdminResourceRow> models = repository.listResources(tenantId, TYPE_MODEL, 100, 0);
        Map<String, ProviderHealthView> merged = new LinkedHashMap<>();

        for (AdminResourceRow row : keys) {
            merged.put(row.resourceKey(), new ProviderHealthView(row.resourceKey(), "healthy", false, row.updatedAt()));
        }
        for (AdminResourceRow row : configs) {
            Map<String, Object> payload = parsePayload(row.payloadJson());
            boolean killSwitch = Boolean.TRUE.equals(payload.get("kill_switch"));
            merged.put(
                row.resourceKey(),
                new ProviderHealthView(
                    row.resourceKey(),
                    killSwitch ? "degraded" : "healthy",
                    killSwitch,
                    row.updatedAt()
                )
            );
        }
        if (merged.isEmpty() && !models.isEmpty()) {
            merged.put("default", new ProviderHealthView("default", "healthy", false, Instant.now(clock)));
        }
        return new ArrayList<>(merged.values());
    }

    public List<AdminResourceView> listVersionBundles(UUID tenantId, int limit, int offset) {
        return toViews(repository.listResources(tenantId, TYPE_VERSION_BUNDLE, clampLimit(limit), Math.max(0, offset)));
    }

    public AdminResourceView activateVersionBundle(UUID tenantId, UUID actorUserId, String bundleId) {
        repository.deactivateResourcesByType(tenantId, TYPE_VERSION_BUNDLE, actorUserId, Instant.now(clock));
        return toView(upsertResource(
            tenantId,
            TYPE_VERSION_BUNDLE,
            bundleId,
            "ACTIVE",
            Map.of("action", "activate"),
            true,
            null,
            actorUserId
        ));
    }

    public AdminResourceView rollbackVersionBundle(UUID tenantId, UUID actorUserId, String bundleId) {
        return toView(upsertResource(
            tenantId,
            TYPE_VERSION_BUNDLE,
            bundleId,
            "ROLLED_BACK",
            Map.of("action", "rollback"),
            false,
            null,
            actorUserId
        ));
    }

    public AdminResourceView upsertToolAllowlist(
        UUID tenantId,
        UUID actorUserId,
        String toolName,
        boolean allowed
    ) {
        return toView(upsertResource(
            tenantId,
            TYPE_TOOL_ALLOWLIST,
            toolName,
            allowed ? "ALLOWED" : "BLOCKED",
            Map.of("allowed", allowed),
            allowed,
            null,
            actorUserId
        ));
    }

    public AdminResourceView upsertErrorCatalog(
        UUID tenantId,
        UUID actorUserId,
        String errorCode,
        String message,
        String severity
    ) {
        return toView(upsertResource(
            tenantId,
            TYPE_ERROR_CATALOG,
            errorCode,
            "UPDATED",
            Map.of(
                "message", piiMaskingService.mask(normalize(message, "Request failed.")),
                "severity", normalize(severity, "normal")
            ),
            true,
            null,
            actorUserId
        ));
    }

    public AdminResourceView createDeployApproval(
        UUID tenantId,
        UUID actorUserId,
        String bundleId,
        String reason
    ) {
        String approvalId = UUID.randomUUID().toString();
        return toView(upsertResource(
            tenantId,
            TYPE_DEPLOY_APPROVAL,
            approvalId,
            "PENDING",
            Map.of(
                "bundle_id", normalize(bundleId, "unknown"),
                "reason", piiMaskingService.mask(normalize(reason, "manual_approval"))
            ),
            false,
            null,
            actorUserId
        ));
    }

    public AdminResourceView actDeployApproval(
        UUID tenantId,
        UUID actorUserId,
        String approvalId,
        String action
    ) {
        AdminResourceRow current = requireResource(tenantId, TYPE_DEPLOY_APPROVAL, approvalId);
        String normalizedAction = normalize(action, "approve").toUpperCase(Locale.ROOT);
        String nextStatus = "REJECT".equals(normalizedAction) ? "REJECTED" : "APPROVED";
        return toView(upsertResource(
            tenantId,
            TYPE_DEPLOY_APPROVAL,
            approvalId,
            nextStatus,
            parsePayload(current.payloadJson()),
            "APPROVED".equals(nextStatus),
            null,
            actorUserId
        ));
    }

    public AdminResourceView publishChangeNotice(
        UUID tenantId,
        UUID actorUserId,
        String noticeId,
        String title,
        String body
    ) {
        return toView(upsertResource(
            tenantId,
            TYPE_CHANGE_NOTICE,
            noticeId,
            "PUBLISHED",
            Map.of(
                "title", piiMaskingService.mask(normalize(title, "notice")),
                "body", piiMaskingService.mask(normalize(body, ""))
            ),
            true,
            null,
            actorUserId
        ));
    }

    public List<OpsTraceView> queryTraces(
        UUID tenantId,
        String keyword,
        Instant fromUtc,
        Instant toUtc,
        int limit,
        int offset
    ) {
        return repository.findOpsTraces(tenantId, keyword, fromUtc, toUtc, clampLimit(limit), Math.max(0, offset))
            .stream()
            .map(row -> new OpsTraceView(
                row.id(),
                row.traceId(),
                row.eventType(),
                row.metricKey(),
                row.metricValue() == null ? 0L : row.metricValue(),
                row.dimensionsJson(),
                row.eventTime()
            ))
            .toList();
    }

    public List<OpsMetricSummaryView> summarizeMetrics(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return repository.findOpsMetricSummary(tenantId, fromUtc, toUtc).stream()
            .map(row -> new OpsMetricSummaryView(row.metricKey(), row.metricValue() == null ? 0L : row.metricValue()))
            .toList();
    }

    public void ingestEvent(
        UUID tenantId,
        String eventType,
        String metricKey,
        long metricValue,
        Map<String, Object> dimensions
    ) {
        opsEventService.append(
            tenantId,
            normalize(eventType, "EVENT_INGEST"),
            normalize(metricKey, "audit_export_requested").toLowerCase(Locale.ROOT),
            Math.max(1L, metricValue),
            dimensions == null ? Map.of() : dimensions
        );
    }

    public OpsRollbackView triggerRollback(
        UUID tenantId,
        UUID actorUserId,
        String targetType,
        String targetRef,
        String reason
    ) {
        Instant nowUtc = Instant.now(clock);
        UUID rollbackId = repository.createRollback(
            tenantId,
            normalize(targetType, "UNKNOWN"),
            normalize(targetRef, "UNKNOWN"),
            piiMaskingService.mask(normalize(reason, "manual_rollback")),
            actorUserId,
            nowUtc
        );
        return new OpsRollbackView(rollbackId, "REQUESTED", nowUtc);
    }

    public List<OpsRollbackListItemView> listRecentRollbacks(UUID tenantId, int limit) {
        return repository.findRecentRollbacks(tenantId, clampLimit(limit)).stream()
            .map(row -> new OpsRollbackListItemView(
                row.id(),
                row.targetType(),
                row.targetId(),
                row.status(),
                row.reason(),
                row.createdAt()
            ))
            .toList();
    }

    public WorkflowReportView workflowReport(UUID tenantId) {
        List<OpsRollbackRow> rollbacks = repository.findRecentRollbacks(tenantId, 50);
        return new WorkflowReportView(rollbacks.size(), rollbacks.stream().limit(5).map(OpsRollbackRow::targetType).toList());
    }

    private AdminResourceRow changeTemplateState(
        UUID tenantId,
        UUID actorUserId,
        String templateId,
        String status,
        boolean active
    ) {
        AdminResourceRow current = requireResource(tenantId, TYPE_TEMPLATE, templateId);
        return upsertResource(
            tenantId,
            TYPE_TEMPLATE,
            templateId,
            status,
            parsePayload(current.payloadJson()),
            active,
            null,
            actorUserId
        );
    }

    private AdminResourceRow upsertResource(
        UUID tenantId,
        String resourceType,
        String resourceKey,
        String status,
        Map<String, Object> payload,
        boolean activeFlag,
        Instant lastRotatedAt,
        UUID actorUserId
    ) {
        Instant nowUtc = Instant.now(clock);
        String payloadJson = toJsonMasked(payload);
        return repository.upsertResource(
            tenantId,
            resourceType,
            resourceKey,
            status,
            payloadJson,
            activeFlag,
            lastRotatedAt,
            actorUserId,
            nowUtc
        );
    }

    private AdminResourceRow requireResource(UUID tenantId, String resourceType, String resourceKey) {
        return repository.findResource(tenantId, resourceType, resourceKey)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Resource was not found"));
    }

    private List<AdminResourceView> toViews(List<AdminResourceRow> rows) {
        return rows.stream().map(this::toView).toList();
    }

    private AdminResourceView toView(AdminResourceRow row) {
        return new AdminResourceView(
            row.resourceKey(),
            row.status(),
            Boolean.TRUE.equals(row.activeFlag()),
            row.payloadJson(),
            row.lastRotatedAt(),
            row.updatedAt()
        );
    }

    private int clampLimit(int limit) {
        return Math.max(1, Math.min(200, limit));
    }

    private String normalize(String rawValue, String fallback) {
        if (rawValue == null || rawValue.isBlank()) {
            return fallback;
        }
        return rawValue.trim();
    }

    private String toJsonMasked(Map<String, Object> payload) {
        try {
            return piiMaskingService.mask(objectMapper.writeValueAsString(payload == null ? Map.of() : payload));
        } catch (JsonProcessingException exception) {
            return "{}";
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parsePayload(String payloadJson) {
        if (payloadJson == null || payloadJson.isBlank()) {
            return new LinkedHashMap<>();
        }
        try {
            Object parsed = objectMapper.readValue(payloadJson, Map.class);
            if (parsed instanceof Map<?, ?> map) {
                return new LinkedHashMap<>((Map<String, Object>) map);
            }
            return new LinkedHashMap<>();
        } catch (Exception exception) {
            return new LinkedHashMap<>();
        }
    }

    public record AdminResourceView(
        String resourceKey,
        String status,
        boolean activeFlag,
        String payloadJson,
        Instant lastRotatedAt,
        Instant updatedAt
    ) {
    }

    public record RoutingRuleTestView(
        String result,
        String matchedRuleId,
        String normalizedPrompt
    ) {
    }

    public record ProviderHealthView(
        String provider,
        String healthStatus,
        boolean killSwitch,
        Instant updatedAt
    ) {
    }

    public record OpsTraceView(
        UUID eventId,
        UUID traceId,
        String eventType,
        String metricKey,
        long metricValue,
        String dimensionsJson,
        Instant eventTime
    ) {
    }

    public record OpsMetricSummaryView(
        String metricKey,
        long metricValue
    ) {
    }

    public record OpsRollbackView(
        UUID rollbackId,
        String status,
        Instant createdAt
    ) {
    }

    public record OpsRollbackListItemView(
        UUID rollbackId,
        String targetType,
        String targetId,
        String status,
        String reason,
        Instant createdAt
    ) {
    }

    public record WorkflowReportView(
        int recentRollbackCount,
        List<String> recentTargets
    ) {
    }
}
