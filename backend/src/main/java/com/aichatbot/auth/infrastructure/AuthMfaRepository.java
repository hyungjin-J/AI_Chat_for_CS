package com.aichatbot.auth.infrastructure;

import com.aichatbot.auth.domain.MfaChallengeRecord;
import com.aichatbot.auth.domain.UserMfaRecord;
import com.aichatbot.auth.domain.mapper.AuthMfaMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Repository
public class AuthMfaRepository {

    private final AuthMfaMapper authMfaMapper;

    public AuthMfaRepository(AuthMfaMapper authMfaMapper) {
        this.authMfaMapper = authMfaMapper;
    }

    public Optional<UserMfaRecord> findByUserId(UUID userId) {
        return Optional.ofNullable(authMfaMapper.findUserMfaByUserId(userId));
    }

    public void upsertUserMfa(
        UUID id,
        UUID tenantId,
        UUID userId,
        String mfaType,
        String secretCiphertext,
        boolean enabled,
        boolean enforced,
        Instant verifiedAt,
        Instant updatedAt
    ) {
        int updated = authMfaMapper.upsertUserMfa(
            id,
            tenantId,
            userId,
            mfaType,
            secretCiphertext,
            enabled,
            enforced,
            verifiedAt,
            updatedAt
        );
        if (updated > 0) {
            return;
        }

        try {
            authMfaMapper.insertUserMfa(
                id,
                tenantId,
                userId,
                mfaType,
                secretCiphertext,
                enabled,
                enforced,
                verifiedAt,
                updatedAt
            );
        } catch (DuplicateKeyException ignored) {
            authMfaMapper.upsertUserMfa(
                id,
                tenantId,
                userId,
                mfaType,
                secretCiphertext,
                enabled,
                enforced,
                verifiedAt,
                updatedAt
            );
        }
    }

    public void replaceRecoveryCodes(UUID tenantId, UUID userId, List<String> codeHashes, Instant expiresAt) {
        authMfaMapper.deleteRecoveryCodes(tenantId, userId);
        for (String codeHash : codeHashes) {
            authMfaMapper.insertRecoveryCode(UUID.randomUUID(), tenantId, userId, codeHash, expiresAt);
        }
    }

    public boolean consumeRecoveryCode(UUID tenantId, UUID userId, String codeHash, Instant usedAt) {
        return authMfaMapper.consumeRecoveryCode(tenantId, userId, codeHash, usedAt) == 1;
    }

    public UUID createChallenge(UUID tenantId, UUID userId, String challengeType, Instant expiresAt, UUID traceId) {
        UUID challengeId = UUID.randomUUID();
        authMfaMapper.insertMfaChallenge(challengeId, tenantId, userId, challengeType, expiresAt, traceId);
        return challengeId;
    }

    public Optional<MfaChallengeRecord> findChallenge(UUID tenantId, UUID challengeId) {
        return Optional.ofNullable(authMfaMapper.findMfaChallengeById(tenantId, challengeId));
    }

    public void setChallengeSecret(UUID tenantId, UUID challengeId, String ciphertext, Instant updatedAt) {
        authMfaMapper.setMfaChallengeSecret(tenantId, challengeId, ciphertext, updatedAt);
    }

    public void incrementChallengeAttempt(UUID tenantId, UUID challengeId, Instant updatedAt) {
        authMfaMapper.incrementChallengeAttempt(tenantId, challengeId, updatedAt);
    }

    public void lockChallenge(UUID tenantId, UUID challengeId, Instant lockedUntil, Instant updatedAt) {
        authMfaMapper.lockChallenge(tenantId, challengeId, lockedUntil, updatedAt);
    }

    public void consumeChallenge(UUID tenantId, UUID challengeId, Instant consumedAt) {
        authMfaMapper.consumeChallenge(tenantId, challengeId, consumedAt);
    }

    public void cleanupExpiredChallenges(Instant cutoff) {
        authMfaMapper.cleanupExpiredChallenges(cutoff);
    }

    public List<String> listRecoveryCodeHashes(UUID tenantId, UUID userId, Instant nowUtc) {
        return authMfaMapper.listRecoveryCodeHashes(tenantId, userId, nowUtc);
    }
}
