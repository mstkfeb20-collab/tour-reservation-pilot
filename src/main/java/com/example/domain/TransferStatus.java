package com.example.domain;

/** 振込状況（RESERVE.TRANSFER）。区分値は既存システムと同じ 0・1・9。 */
public enum TransferStatus {
    UNPAID("0", "未振込"),
    PAID("1", "振込済"),
    CANCELLED("9", "取消");

    private final String code;
    private final String label;

    TransferStatus(String code, String label) {
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
