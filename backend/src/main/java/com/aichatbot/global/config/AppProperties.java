package com.aichatbot.global.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private final Jwt jwt = new Jwt();
    private final Security security = new Security();
    private final Trace trace = new Trace();
    private final Answer answer = new Answer();
    private final Rag rag = new Rag();
    private final Budget budget = new Budget();
    private final Llm llm = new Llm();

    public Jwt getJwt() {
        return jwt;
    }

    public Security getSecurity() {
        return security;
    }

    public Trace getTrace() {
        return trace;
    }

    public Answer getAnswer() {
        return answer;
    }

    public Rag getRag() {
        return rag;
    }

    public Budget getBudget() {
        return budget;
    }

    public Llm getLlm() {
        return llm;
    }

    public static class Jwt {
        private String secret;
        private long accessExpirationSec = 3600L;
        private long refreshExpirationSec = 1209600L;

        public String getSecret() {
            return secret;
        }

        public void setSecret(String secret) {
            this.secret = secret;
        }

        public long getAccessExpirationSec() {
            return accessExpirationSec;
        }

        public void setAccessExpirationSec(long accessExpirationSec) {
            this.accessExpirationSec = accessExpirationSec;
        }

        public long getRefreshExpirationSec() {
            return refreshExpirationSec;
        }

        public void setRefreshExpirationSec(long refreshExpirationSec) {
            this.refreshExpirationSec = refreshExpirationSec;
        }
    }

    public static class Security {
        private boolean allowHeaderAuth = true;

        public boolean isAllowHeaderAuth() {
            return allowHeaderAuth;
        }

        public void setAllowHeaderAuth(boolean allowHeaderAuth) {
            this.allowHeaderAuth = allowHeaderAuth;
        }
    }

    public static class Trace {
        private boolean requireHeader = false;

        public boolean isRequireHeader() {
            return requireHeader;
        }

        public void setRequireHeader(boolean requireHeader) {
            this.requireHeader = requireHeader;
        }
    }

    public static class Answer {
        private double evidenceThreshold = 0.7d;

        public double getEvidenceThreshold() {
            return evidenceThreshold;
        }

        public void setEvidenceThreshold(double evidenceThreshold) {
            this.evidenceThreshold = evidenceThreshold;
        }
    }

    public static class Rag {
        private int topKDefault = 3;
        private int topKMax = 5;

        public int getTopKDefault() {
            return topKDefault;
        }

        public void setTopKDefault(int topKDefault) {
            this.topKDefault = topKDefault;
        }

        public int getTopKMax() {
            return topKMax;
        }

        public void setTopKMax(int topKMax) {
            this.topKMax = topKMax;
        }
    }

    public static class Budget {
        private int inputTokenMax = 1500;
        private int outputTokenMax = 1500;
        private int toolCallMax = 3;
        private int sessionBudgetMax = 10000;
        private int sseConcurrencyMaxPerUser = 2;

        public int getInputTokenMax() {
            return inputTokenMax;
        }

        public void setInputTokenMax(int inputTokenMax) {
            this.inputTokenMax = inputTokenMax;
        }

        public int getOutputTokenMax() {
            return outputTokenMax;
        }

        public void setOutputTokenMax(int outputTokenMax) {
            this.outputTokenMax = outputTokenMax;
        }

        public int getToolCallMax() {
            return toolCallMax;
        }

        public void setToolCallMax(int toolCallMax) {
            this.toolCallMax = toolCallMax;
        }

        public int getSessionBudgetMax() {
            return sessionBudgetMax;
        }

        public void setSessionBudgetMax(int sessionBudgetMax) {
            this.sessionBudgetMax = sessionBudgetMax;
        }

        public int getSseConcurrencyMaxPerUser() {
            return sseConcurrencyMaxPerUser;
        }

        public void setSseConcurrencyMaxPerUser(int sseConcurrencyMaxPerUser) {
            this.sseConcurrencyMaxPerUser = sseConcurrencyMaxPerUser;
        }
    }

    public static class Llm {
        private String provider = "ollama";
        private final Ollama ollama = new Ollama();

        public String getProvider() {
            return provider;
        }

        public void setProvider(String provider) {
            this.provider = provider;
        }

        public Ollama getOllama() {
            return ollama;
        }
    }

    public static class Ollama {
        private String baseUrl = "http://localhost:11434";
        private String model = "llama3.2";

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public String getModel() {
            return model;
        }

        public void setModel(String model) {
            this.model = model;
        }
    }
}
