package com.aichatbot.contexts.conversation.message.presentation;

import com.aichatbot.platform.observability.TraceGuard;
import jakarta.validation.constraints.NotBlank;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/attachments")
public class AttachmentController {

    @PostMapping("/presign")
    public ResponseEntity<AttachmentPresignResponse> presign(@RequestBody(required = false) AttachmentPresignRequest request) {
        String attachmentId = UUID.randomUUID().toString();
        String fileName = request == null ? "attachment.bin" : request.fileName();
        AttachmentPresignResponse response = new AttachmentPresignResponse(
            attachmentId,
            "https://upload.local/" + attachmentId + "/" + fileName,
            "accepted",
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/{attachment_id}/complete")
    public AttachmentCompleteResponse complete(@PathVariable("attachment_id") String attachmentId) {
        return new AttachmentCompleteResponse(attachmentId, "completed", TraceGuard.requireTraceId());
    }

    public record AttachmentPresignRequest(
        @NotBlank
        String fileName,
        String contentType
    ) {
    }

    public record AttachmentPresignResponse(
        String attachmentId,
        String uploadUrl,
        String result,
        String traceId
    ) {
    }

    public record AttachmentCompleteResponse(
        String attachmentId,
        String result,
        String traceId
    ) {
    }
}
