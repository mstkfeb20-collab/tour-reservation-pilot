package com.example.domain;

public enum ClaimStatus {
    WAITING("0"),
    CLAIMED("1");

    private final String code;

    ClaimStatus(String code) {
        this.code = code;
    }

    public String code() {
        return code;
    }
}
