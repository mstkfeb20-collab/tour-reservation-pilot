package com.example.domain;

import java.time.LocalDate;
import java.util.Objects;

public record TransferImportRecord(
    LocalDate accountDate,
    String inquiryNo,
    Money amount,
    String payerName,
    String reserveNo,
    TransferImportResultCode result,
    String fileName
) {
    public TransferImportRecord {
        Objects.requireNonNull(accountDate);
        Objects.requireNonNull(inquiryNo);
        Objects.requireNonNull(amount);
        Objects.requireNonNull(payerName);
        Objects.requireNonNull(result);
        Objects.requireNonNull(fileName);
    }
}
