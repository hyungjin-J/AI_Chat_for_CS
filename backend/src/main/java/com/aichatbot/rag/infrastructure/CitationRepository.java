package com.aichatbot.rag.infrastructure;

import com.aichatbot.rag.application.CitationView;
import com.aichatbot.rag.domain.mapper.CitationMapper;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class CitationRepository {

    private final CitationMapper citationMapper;

    public CitationRepository(CitationMapper citationMapper) {
        this.citationMapper = citationMapper;
    }

    public void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, UUID chunkId, int rankNo, String excerptMasked) {
        citationMapper.save(
            UUID.randomUUID(),
            tenantId,
            messageId,
            messageCreatedAt,
            chunkId,
            rankNo,
            excerptMasked
        );
    }

    public List<CitationView> findByMessageId(UUID tenantId, UUID messageId, Integer cursorRankNo, int limit) {
        List<CitationRow> rows = citationMapper.findByMessageId(
            tenantId,
            messageId,
            cursorRankNo,
            limit
        );
        List<CitationView> views = new ArrayList<>(rows.size());
        for (CitationRow row : rows) {
            views.add(new CitationView(
                UUID.fromString(row.id()),
                UUID.fromString(row.tenantId()),
                UUID.fromString(row.messageId()),
                row.chunkId() == null ? null : UUID.fromString(row.chunkId()),
                row.rankNo(),
                row.excerptMasked(),
                row.createdAt()
            ));
        }
        return views;
    }
}
