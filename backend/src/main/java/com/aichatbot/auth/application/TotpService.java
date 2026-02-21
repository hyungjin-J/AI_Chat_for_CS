package com.aichatbot.auth.application;

import java.nio.ByteBuffer;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Component;

@Component
public class TotpService {

    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final int SECRET_BYTES = 20;
    private static final int CODE_DIGITS = 6;
    private static final long TIME_STEP_SECONDS = 30L;
    private static final String RECOVERY_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

    private final SecureRandom secureRandom = new SecureRandom();

    public String generateSecretBase32() {
        byte[] raw = new byte[SECRET_BYTES];
        secureRandom.nextBytes(raw);
        return encodeBase32(raw);
    }

    public String buildOtpAuthUri(String issuer, String accountName, String secretBase32) {
        String safeIssuer = urlEncode(issuer == null || issuer.isBlank() ? "AI_Chatbot" : issuer);
        String safeAccount = urlEncode(accountName == null || accountName.isBlank() ? "unknown" : accountName);
        return "otpauth://totp/" + safeIssuer + ":" + safeAccount
            + "?secret=" + secretBase32
            + "&issuer=" + safeIssuer
            + "&algorithm=SHA1&digits=6&period=30";
    }

    public boolean verifyCode(String secretBase32, String code, Instant nowUtc) {
        if (code == null || !code.matches("\\d{6}")) {
            return false;
        }
        Instant normalized = nowUtc == null ? Instant.now() : nowUtc;
        byte[] secretBytes = decodeBase32(secretBase32);
        long currentStep = normalized.getEpochSecond() / TIME_STEP_SECONDS;
        for (long offset = -1L; offset <= 1L; offset++) {
            if (generateTotp(secretBytes, currentStep + offset).equals(code)) {
                return true;
            }
        }
        return false;
    }

    public List<String> generateRecoveryCodes(int count) {
        List<String> codes = new ArrayList<>();
        int safeCount = Math.max(1, count);
        for (int index = 0; index < safeCount; index++) {
            codes.add(randomRecoveryCode());
        }
        return codes;
    }

    public String hashRecoveryCode(String rawCode) {
        try {
            return Base64.getEncoder().encodeToString(
                java.security.MessageDigest.getInstance("SHA-256")
                    .digest((rawCode == null ? "" : rawCode.trim().toUpperCase(Locale.ROOT))
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8))
            );
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to hash recovery code", exception);
        }
    }

    private String generateTotp(byte[] secret, long counter) {
        try {
            byte[] challenge = ByteBuffer.allocate(8).putLong(counter).array();
            Mac mac = Mac.getInstance("HmacSHA1");
            mac.init(new SecretKeySpec(secret, "HmacSHA1"));
            byte[] hmac = mac.doFinal(challenge);
            int offset = hmac[hmac.length - 1] & 0x0F;
            int binary = ((hmac[offset] & 0x7F) << 24)
                | ((hmac[offset + 1] & 0xFF) << 16)
                | ((hmac[offset + 2] & 0xFF) << 8)
                | (hmac[offset + 3] & 0xFF);
            int otp = binary % (int) Math.pow(10, CODE_DIGITS);
            return String.format("%0" + CODE_DIGITS + "d", otp);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("Unable to generate TOTP code", exception);
        }
    }

    private String randomRecoveryCode() {
        StringBuilder builder = new StringBuilder(10);
        for (int index = 0; index < 10; index++) {
            int charIndex = secureRandom.nextInt(RECOVERY_CODE_CHARS.length());
            builder.append(RECOVERY_CODE_CHARS.charAt(charIndex));
        }
        return builder.toString();
    }

    private String encodeBase32(byte[] bytes) {
        StringBuilder output = new StringBuilder();
        int current = 0;
        int bitsRemaining = 0;
        for (byte value : bytes) {
            current = (current << 8) | (value & 0xFF);
            bitsRemaining += 8;
            while (bitsRemaining >= 5) {
                int index = (current >> (bitsRemaining - 5)) & 0x1F;
                bitsRemaining -= 5;
                output.append(BASE32_ALPHABET.charAt(index));
            }
        }
        if (bitsRemaining > 0) {
            int index = (current << (5 - bitsRemaining)) & 0x1F;
            output.append(BASE32_ALPHABET.charAt(index));
        }
        return output.toString();
    }

    private byte[] decodeBase32(String input) {
        if (input == null || input.isBlank()) {
            return new byte[0];
        }
        String normalized = input.trim().replace("=", "").toUpperCase(Locale.ROOT);
        int buffer = 0;
        int bitsLeft = 0;
        ByteBuffer result = ByteBuffer.allocate((normalized.length() * 5 + 7) / 8);
        for (char ch : normalized.toCharArray()) {
            int value = BASE32_ALPHABET.indexOf(ch);
            if (value < 0) {
                continue;
            }
            buffer = (buffer << 5) | value;
            bitsLeft += 5;
            if (bitsLeft >= 8) {
                bitsLeft -= 8;
                result.put((byte) ((buffer >> bitsLeft) & 0xFF));
            }
        }
        byte[] bytes = new byte[result.position()];
        result.flip();
        result.get(bytes);
        return bytes;
    }

    private String urlEncode(String value) {
        return java.net.URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8);
    }
}
