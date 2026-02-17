package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.AuditLogEntry;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.stereotype.Repository;

@Repository
public class AuditLogRepository {

    private final CopyOnWriteArrayList<AuditLogEntry> entries = new CopyOnWriteArrayList<>();

    public void save(AuditLogEntry entry) {
        entries.add(entry);
    }

    public List<AuditLogEntry> findByTenant(String tenantId) {
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .toList();
    }

    public List<AuditLogEntry> findAll() {
        return new ArrayList<>(entries);
    }

    public void clear() {
        entries.clear();
    }
}

