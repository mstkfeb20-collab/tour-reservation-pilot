package com.example.domain;

public enum TransferImportResultCode {
    SETTLED("10", "消込済"),
    NO_RESERVATION("21", "予約なし"),
    UNDERPAID("22", "不足"),
    OVERPAID("23", "超過"),
    DUPLICATE_PAYMENT("31", "二重振込"),
    PAID_AFTER_CANCELLATION("32", "取消後の入金"),
    REVERSAL("40", "要確認（組戻し）"),
    REVIEW("41", "要確認"),
    CANCELLED_SETTLED("50", "取消で精算済");

    private final String code;
    private final String label;

    TransferImportResultCode(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String code() {
        return code;
    }

    public String label() {
        return label;
    }

    public boolean isRefundTarget() {
        return this == DUPLICATE_PAYMENT || this == PAID_AFTER_CANCELLATION;
    }

    public boolean isMismatch() {
        return this == NO_RESERVATION || this == UNDERPAID || this == OVERPAID || this == REVERSAL || this == REVIEW;
    }
}
