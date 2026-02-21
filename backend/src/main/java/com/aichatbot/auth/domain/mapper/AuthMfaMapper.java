package com.aichatbot.auth.domain.mapper;

import com.aichatbot.auth.domain.MfaChallengeRecord;
import com.aichatbot.auth.domain.UserMfaRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface AuthMfaMapper {

    UserMfaRecord findUserMfaByUserId(@Param("userId") UUID userId);

    int upsertUserMfa(@Param("id") UUID id,
                      @Param("tenantId") UUID tenantId,
                      @Param("userId") UUID userId,
                      @Param("mfaType") String mfaType,
                      @Param("secretCiphertext") String secretCiphertext,
                      @Param("enabled") boolean enabled,
                      @Param("enforced") boolean enforced,
                      @Param("verifiedAt") Instant verifiedAt,
                      @Param("updatedAt") Instant updatedAt);

    int insertUserMfa(@Param("id") UUID id,
                      @Param("tenantId") UUID tenantId,
                      @Param("userId") UUID userId,
                      @Param("mfaType") String mfaType,
                      @Param("secretCiphertext") String secretCiphertext,
                      @Param("enabled") boolean enabled,
                      @Param("enforced") boolean enforced,
                      @Param("verifiedAt") Instant verifiedAt,
                      @Param("updatedAt") Instant updatedAt);

    int deleteRecoveryCodes(@Param("tenantId") UUID tenantId,
                            @Param("userId") UUID userId);

    int insertRecoveryCode(@Param("id") UUID id,
                           @Param("tenantId") UUID tenantId,
                           @Param("userId") UUID userId,
                           @Param("codeHash") String codeHash,
                           @Param("expiresAt") Instant expiresAt);

    int consumeRecoveryCode(@Param("tenantId") UUID tenantId,
                            @Param("userId") UUID userId,
                            @Param("codeHash") String codeHash,
                            @Param("usedAt") Instant usedAt);

    int insertMfaChallenge(@Param("id") UUID id,
                           @Param("tenantId") UUID tenantId,
                           @Param("userId") UUID userId,
                           @Param("challengeType") String challengeType,
                           @Param("expiresAt") Instant expiresAt,
                           @Param("traceId") UUID traceId);

    MfaChallengeRecord findMfaChallengeById(@Param("tenantId") UUID tenantId,
                                            @Param("challengeId") UUID challengeId);

    int setMfaChallengeSecret(@Param("tenantId") UUID tenantId,
                              @Param("challengeId") UUID challengeId,
                              @Param("ciphertext") String ciphertext,
                              @Param("updatedAt") Instant updatedAt);

    int incrementChallengeAttempt(@Param("tenantId") UUID tenantId,
                                  @Param("challengeId") UUID challengeId,
                                  @Param("updatedAt") Instant updatedAt);

    int lockChallenge(@Param("tenantId") UUID tenantId,
                      @Param("challengeId") UUID challengeId,
                      @Param("lockedUntil") Instant lockedUntil,
                      @Param("updatedAt") Instant updatedAt);

    int consumeChallenge(@Param("tenantId") UUID tenantId,
                         @Param("challengeId") UUID challengeId,
                         @Param("consumedAt") Instant consumedAt);

    int cleanupExpiredChallenges(@Param("cutoff") Instant cutoff);

    List<String> listRecoveryCodeHashes(@Param("tenantId") UUID tenantId,
                                        @Param("userId") UUID userId,
                                        @Param("nowUtc") Instant nowUtc);
}
