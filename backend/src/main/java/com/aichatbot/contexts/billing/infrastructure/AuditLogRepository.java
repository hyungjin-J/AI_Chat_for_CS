package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.model.AuditLogEntry;
import com.aichatbot.contexts.billing.domain.mapper.BillingAuditLogMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class AuditLogRepository {

    private final BillingAuditLogMapper billingAuditLogMapper;
    private final String persistenceMode;
    private final CopyOnWriteArrayList<AuditLogEntry> entries = new CopyOnWriteArrayList<>();

    public AuditLogRepository() {
        this.billingAuditLogMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public AuditLogRepository(
        @Autowired(required = false) BillingAuditLogMapper billingAuditLogMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.billingAuditLogMapper = billingAuditLogMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(AuditLogEntry entry) {
        if (useMapperPersistence()) {
            billingAuditLogMapper.insert(
                entry.id(),
                entry.tenantId(),
                entry.actorUserId(),
                entry.actorRole(),
                entry.actionType(),
                entry.targetType(),
                entry.targetId(),
                entry.traceId(),
                entry.beforeJson(),
                entry.afterJson(),
                entry.createdAt()
            );
            return;
        }
        entries.add(entry);
    }

    public List<AuditLogEntry> findByTenant(String tenantId) {
        if (useMapperPersistence()) {
            return billingAuditLogMapper.findByTenant(tenantId);
        }
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .toList();
    }

    public List<AuditLogEntry> findAll() {
        if (useMapperPersistence()) {
            return billingAuditLogMapper.findAll();
        }
        return new ArrayList<>(entries);
    }

    public void clear() {
        if (useMapperPersistence()) {
            billingAuditLogMapper.deleteAll();
            return;
        }
        entries.clear();
    }

    private boolean useMapperPersistence() {
        return billingAuditLogMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }
}


