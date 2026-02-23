package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.GenerationLogMapper;
import com.aichatbot.contexts.billing.domain.model.GenerationLogEntry;
import com.aichatbot.contexts.billing.domain.model.GenerationLogRow;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class GenerationLogRepository {

    private final GenerationLogMapper generationLogMapper;
    private final String persistenceMode;
    private final CopyOnWriteArrayList<GenerationLogEntry> entries = new CopyOnWriteArrayList<>();

    public GenerationLogRepository() {
        this.generationLogMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public GenerationLogRepository(
        @Autowired(required = false) GenerationLogMapper generationLogMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.generationLogMapper = generationLogMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(GenerationLogEntry entry) {
        if (entry.traceId() == null || entry.traceId().isBlank()) {
            throw new IllegalArgumentException("trace_id is required for generation log");
        }
        if (useMapperPersistence()) {
            generationLogMapper.insert(
                entry.id(),
                entry.tenantId(),
                entry.messageId(),
                entry.providerId(),
                entry.modelId(),
                entry.inputTokens(),
                entry.outputTokens(),
                entry.toolCalls(),
                entry.promptMasked(),
                entry.traceId(),
                entry.createdAt()
            );
            return;
        }
        entries.add(entry);
    }

    public List<GenerationLogEntry> findByTenant(String tenantId) {
        if (useMapperPersistence()) {
            return generationLogMapper.findByTenant(tenantId).stream().map(this::toDomain).toList();
        }
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .toList();
    }

    public List<GenerationLogEntry> findByTenantAndDate(String tenantId, LocalDate date) {
        if (useMapperPersistence()) {
            return generationLogMapper.findByTenantAndDate(tenantId, date).stream().map(this::toDomain).toList();
        }
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .filter(entry -> entry.createdAt().atZone(ZoneOffset.UTC).toLocalDate().equals(date))
            .toList();
    }

    public List<GenerationLogEntry> findByTenantAndMonth(String tenantId, YearMonth month) {
        if (useMapperPersistence()) {
            return generationLogMapper.findByTenantAndMonth(
                tenantId,
                month.atDay(1),
                month.plusMonths(1).atDay(1)
            ).stream().map(this::toDomain).toList();
        }
        return entries.stream()
            .filter(entry -> Objects.equals(entry.tenantId(), tenantId))
            .filter(entry -> YearMonth.from(entry.createdAt().atZone(ZoneOffset.UTC)).equals(month))
            .toList();
    }

    public List<GenerationLogEntry> findByDate(LocalDate date) {
        if (useMapperPersistence()) {
            return generationLogMapper.findByDate(date).stream().map(this::toDomain).toList();
        }
        return entries.stream()
            .filter(entry -> entry.createdAt().atZone(ZoneOffset.UTC).toLocalDate().equals(date))
            .toList();
    }

    public List<GenerationLogEntry> findAll() {
        if (useMapperPersistence()) {
            return generationLogMapper.findAll().stream().map(this::toDomain).toList();
        }
        return new ArrayList<>(entries);
    }

    public void clear() {
        if (useMapperPersistence()) {
            generationLogMapper.deleteAll();
            return;
        }
        entries.clear();
    }

    private boolean useMapperPersistence() {
        return generationLogMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }

    private GenerationLogEntry toDomain(GenerationLogRow row) {
        if (row == null) {
            return null;
        }
        return new GenerationLogEntry(
            row.id(),
            row.tenantId(),
            row.messageId(),
            row.providerId(),
            row.modelId(),
            row.inputTokens(),
            row.outputTokens(),
            row.toolCalls(),
            row.promptMasked(),
            row.traceId(),
            row.createdAt()
        );
    }
}


