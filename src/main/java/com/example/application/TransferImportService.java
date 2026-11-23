package com.example.application;

import com.example.domain.BankTransferDetail;
import com.example.domain.BankTransferFile;
import com.example.domain.Money;
import com.example.domain.PaymentAuditRepository;
import com.example.domain.PaymentHandoffRepository;
import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;
import com.example.domain.TransferImportRecord;
import com.example.domain.TransferImportRepository;
import com.example.domain.TransferImportResultCode;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

public class TransferImportService {

    private static final Pattern RESERVE_NO = Pattern.compile("R[0-9]{12}");

    private final ReservationRepository reservations;
    private final TransferImportRepository imports;
    private final PaymentHandoffRepository handoffQueue;
    private final PaymentAuditRepository auditLog;

    public TransferImportService(
        ReservationRepository reservations,
        TransferImportRepository imports,
        PaymentHandoffRepository handoffQueue,
        PaymentAuditRepository auditLog
    ) {
        this.reservations = reservations;
        this.imports = imports;
        this.handoffQueue = handoffQueue;
        this.auditLog = auditLog;
    }

    public synchronized TransferImportOutcome importFile(BankTransferFile file, String fileName) {
        if (imports.hasImportedFile(file.creationDate(), file.details().size(), file.totalAmount())) {
            return new TransferImportOutcome(List.of(), List.of(), List.of(), true);
        }

        List<TransferImportRecord> results = new ArrayList<>();
        List<TransferImportOutcome.PaymentHandoff> handoffs = new ArrayList<>();
        List<TransferImportOutcome.PaymentAudit> auditEntries = new ArrayList<>();
        List<BankTransferDetail> details = file.details().stream()
            .sorted(Comparator.comparing(BankTransferDetail::inquiryNo))
            .toList();

        for (BankTransferDetail detail : details) {
            Optional<TransferImportRecord> prior = imports.findByAccountDateAndInquiryNo(detail.accountDate(), detail.inquiryNo());
            if (prior.isPresent()) {
                if (prior.get().result() == TransferImportResultCode.SETTLED) {
                    recordSettlementSideEffects(prior.get(), handoffs, auditEntries);
                }
                results.add(prior.get());
                continue;
            }

            String reserveNo = extractReserveNo(detail);
            Decision decision = classify(detail, reserveNo);
            TransferImportRecord result = new TransferImportRecord(
                detail.accountDate(),
                detail.inquiryNo(),
                detail.amount(),
                detail.payerName(),
                reserveNo,
                decision.resultCode(),
                fileName
            );
            if (decision.resultCode() == TransferImportResultCode.SETTLED) {
                if (imports.saveSettlement(decision.reservation(), decision.expectedVersion(), decision.latePayment(), result)) {
                    recordSettlementSideEffects(result, handoffs, auditEntries);
                } else {
                    result = new TransferImportRecord(
                        detail.accountDate(),
                        detail.inquiryNo(),
                        detail.amount(),
                        detail.payerName(),
                        reserveNo,
                        TransferImportResultCode.REVIEW,
                        fileName
                    );
                    imports.save(result);
                }
            } else {
                imports.save(result);
            }
            results.add(result);
        }
        imports.saveFileSummary(file.creationDate(), file.details().size(), file.totalAmount());
        return new TransferImportOutcome(results, handoffs, auditEntries, false);
    }

    private void recordSettlementSideEffects(
        TransferImportRecord record,
        List<TransferImportOutcome.PaymentHandoff> handoffs,
        List<TransferImportOutcome.PaymentAudit> auditEntries
    ) {
        handoffs.add(new TransferImportOutcome.PaymentHandoff(record.reserveNo(), record.accountDate()));
        auditEntries.add(new TransferImportOutcome.PaymentAudit("J110", record.inquiryNo(), record.amount()));
        handoffQueue.enqueue(record.reserveNo(), record.accountDate());
        auditLog.record("J110", record.inquiryNo(), record.amount());
    }

    private Decision classify(BankTransferDetail detail, String reserveNo) {
        if (detail.cancellationCode().equals("1")) {
            return Decision.of(TransferImportResultCode.REVERSAL);
        }
        if (reserveNo == null) {
            return Decision.of(TransferImportResultCode.NO_RESERVATION);
        }
        Optional<Reservation> found = reservations.findByReserveNo(reserveNo);
        if (found.isEmpty()) {
            return Decision.of(TransferImportResultCode.NO_RESERVATION);
        }
        Reservation reservation = found.get();
        if (reservation.status() == com.example.domain.TransferStatus.CANCELLED) {
            return Decision.of(TransferImportResultCode.PAID_AFTER_CANCELLATION);
        }
        if (reservation.status() == com.example.domain.TransferStatus.PAID) {
            return Decision.of(TransferImportResultCode.DUPLICATE_PAYMENT);
        }

        int amountComparison = Long.compare(detail.amount().toLong(), reservation.sumPrice().toLong());
        if (amountComparison < 0) {
            return Decision.of(TransferImportResultCode.UNDERPAID);
        }
        if (amountComparison > 0) {
            return Decision.of(TransferImportResultCode.OVERPAID);
        }

        long expectedVersion = reservation.version();
        boolean latePayment = reservation.payDueDate() != null && detail.accountDate().isAfter(reservation.payDueDate());
        return new Decision(TransferImportResultCode.SETTLED, reservation, expectedVersion, latePayment);
    }

    private String extractReserveNo(BankTransferDetail detail) {
        String ediReserveNo = firstThirteen(detail.ediInformation());
        if (RESERVE_NO.matcher(ediReserveNo).matches()) {
            return ediReserveNo;
        }
        String payerReserveNo = firstThirteen(detail.payerName());
        return RESERVE_NO.matcher(payerReserveNo).matches() ? payerReserveNo : null;
    }

    private String firstThirteen(String value) {
        return value.length() < 13 ? "" : value.substring(0, 13);
    }

    private record Decision(
        TransferImportResultCode resultCode,
        Reservation reservation,
        long expectedVersion,
        boolean latePayment
    ) {
        private static Decision of(TransferImportResultCode resultCode) {
            return new Decision(resultCode, null, 0, false);
        }
    }
}
