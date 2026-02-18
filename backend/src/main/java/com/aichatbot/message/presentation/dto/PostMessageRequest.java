package com.aichatbot.message.presentation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

public record PostMessageRequest(
    @NotBlank
    @Size(max = 4000)
    String text,
    List<String> attachments,
    @Size(max = 120)
    String clientNonce,
    Integer topK
) {
}
