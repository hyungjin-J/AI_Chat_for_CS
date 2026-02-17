package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.GenerationLogEntry;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.stereotype.Repository;

@Repository
public class GenerationLogRepository {

    private final CopyOnWriteArrayList<GenerationLogEntry> entries = new CopyOnWriteArrayList<>();

    public void save(GenerationLogEntry entry) {
        if (entry.traceId() == null || entry.traceId().isBlank()) {
            throw new IllegalArgumentException("trace_id is required for generation log");
        }
        entries.add(entry);
    }

    public List<GenerationLogEntry> findByTenant(String tenantId) {
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .toList();
    }

    public List<GenerationLogEntry> findByTenantAndDate(String tenantId, LocalDate date) {
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .filter(entry -> entry.createdAt().atZone(ZoneOffset.UTC).toLocalDate().equals(date))
            .toList();
    }

    public List<GenerationLogEntry> findByTenantAndMonth(String tenantId, YearMonth month) {
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .filter(entry -> YearMonth.from(entry.createdAt().atZone(ZoneOffset.UTC)).equals(month))
            .toList();
    }

    public List<GenerationLogEntry> findByDate(LocalDate date) {
        return entries.stream()
            .filter(entry -> entry.createdAt().atZone(ZoneOffset.UTC).toLocalDate().equals(date))
            .toList();
    }

    public List<GenerationLogEntry> findAll() {
        return new ArrayList<>(entries);
    }

    public void clear() {
        entries.clear();
    }
}

