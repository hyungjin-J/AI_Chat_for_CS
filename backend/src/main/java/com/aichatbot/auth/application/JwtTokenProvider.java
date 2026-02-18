package com.aichatbot.auth.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.security.UserPrincipal;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Component;

@Component
public class JwtTokenProvider {

    private final AppProperties appProperties;
    private final SecretKey secretKey;

    public JwtTokenProvider(AppProperties appProperties) {
        this.appProperties = appProperties;
        this.secretKey = Keys.hmacShaKeyFor(normalizeSecret(appProperties.getJwt().getSecret()));
    }

    public String generateAccessToken(UserPrincipal principal, String traceId) {
        Instant now = Instant.now();
        Instant expiry = now.plusSeconds(appProperties.getJwt().getAccessExpirationSec());
        return Jwts.builder()
            .setSubject(principal.userId())
            .claim("tenant_id", principal.tenantId())
            .claim("login_id", principal.loginId())
            .claim("roles", principal.roles())
            .claim("token_type", "access")
            .claim("trace_id", traceId)
            .setIssuedAt(Date.from(now))
            .setExpiration(Date.from(expiry))
            .signWith(secretKey, SignatureAlgorithm.HS256)
            .compact();
    }

    public String generateRefreshToken(UserPrincipal principal, String traceId) {
        Instant now = Instant.now();
        Instant expiry = now.plusSeconds(appProperties.getJwt().getRefreshExpirationSec());
        return Jwts.builder()
            .setSubject(principal.userId())
            .claim("tenant_id", principal.tenantId())
            .claim("login_id", principal.loginId())
            .claim("roles", principal.roles())
            .claim("token_type", "refresh")
            .claim("trace_id", traceId)
            .setIssuedAt(Date.from(now))
            .setExpiration(Date.from(expiry))
            .signWith(secretKey, SignatureAlgorithm.HS256)
            .compact();
    }

    public Claims parseClaims(String token) {
        return Jwts.parser()
            .setSigningKey(secretKey)
            .build()
            .parseClaimsJws(token)
            .getBody();
    }

    public UserPrincipal toPrincipal(Claims claims) {
        String userId = claims.getSubject();
        String tenantId = claims.get("tenant_id", String.class);
        String loginId = claims.get("login_id", String.class);
        List<String> roles = claims.get("roles", List.class);
        return new UserPrincipal(userId, tenantId, loginId, roles == null ? List.of() : List.copyOf(roles));
    }

    public String hashToken(String rawToken) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(rawToken.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hash);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 not available", exception);
        }
    }

    private byte[] normalizeSecret(String rawSecret) {
        String secret = rawSecret == null ? "" : rawSecret;
        if (secret.length() < 32) {
            StringBuilder builder = new StringBuilder(secret);
            while (builder.length() < 32) {
                builder.append('x');
            }
            secret = builder.toString();
        }
        return secret.getBytes(StandardCharsets.UTF_8);
    }
}
