package com.example.domain;

public enum RefundStatus {
    WAITING("0", "返金待ち"),
    REFUNDED("1", "返金済");

    private final String code;
    private final String label;

    RefundStatus(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String code() {
        return code;
    }

    public String label() {
        return label;
    }
}
