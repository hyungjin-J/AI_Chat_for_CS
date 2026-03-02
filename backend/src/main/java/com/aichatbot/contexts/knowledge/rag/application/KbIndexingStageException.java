package com.aichatbot.contexts.knowledge.rag.application;

public class KbIndexingStageException extends RuntimeException {

    private final String errorCode;
    private final boolean parserError;

    public KbIndexingStageException(String errorCode, String message, boolean parserError) {
        super(message);
        this.errorCode = errorCode;
        this.parserError = parserError;
    }

    public KbIndexingStageException(String errorCode, String message, boolean parserError, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.parserError = parserError;
    }

    public String errorCode() {
        return errorCode;
    }

    public boolean parserError() {
        return parserError;
    }
}
