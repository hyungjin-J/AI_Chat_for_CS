package com.aichatbot.message.presentation.dto;

import java.util.List;

public record MessageListResponse(
    List<MessageItem> items,
    int total,
    String traceId
) {
    public record MessageItem(
        String messageId,
        String role,
        String messageText,
        String createdAt,
        String traceId
    ) {
    }
}
