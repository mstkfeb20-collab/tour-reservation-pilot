package com.example.application;

import com.example.domain.Money;
import com.example.domain.TransferImportRecord;

import java.time.LocalDate;
import java.util.List;

public record TransferImportOutcome(
    List<TransferImportRecord> records,
    List<PaymentHandoff> handoffs,
    List<PaymentAudit> auditEntries,
    boolean duplicateFile
) {
    public TransferImportOutcome {
        records = List.copyOf(records);
        handoffs = List.copyOf(handoffs);
        auditEntries = List.copyOf(auditEntries);
    }

    public boolean hasExceptions() {
        return records.stream().anyMatch(record -> record.result().isMismatch() || record.result().isRefundTarget());
    }

    public record PaymentHandoff(String reserveNo, LocalDate paidDate) {
    }

    public record PaymentAudit(String operator, String inquiryNo, Money amount) {
    }
}
