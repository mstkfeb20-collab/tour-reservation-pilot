package com.example.infrastructure;

import com.example.domain.Money;
import com.example.domain.Refund;
import com.example.domain.RefundRepository;
import com.example.domain.RefundStatus;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class InMemoryRefundRepository implements RefundRepository {

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;

    private final Map<String, Refund> refundsByNumber = new HashMap<>();
    private final Map<String, Refund> refundsByReservation = new HashMap<>();
    private final Map<LocalDate, Integer> dailySequences = new HashMap<>();

    @Override
    public synchronized Refund register(
        String reserveNo,
        LocalDate cancelDate,
        Money refundAmount,
        Money cancelFee,
        String operator
    ) {
        if (refundsByReservation.containsKey(reserveNo)) {
            throw new IllegalStateException("予約 " + reserveNo + " の返金待ちは登録済みです");
        }
        int sequence = dailySequences.merge(cancelDate, 1, Integer::sum);
        if (sequence > 9999) {
            dailySequences.put(cancelDate, 9999);
            throw new IllegalStateException("返金番号の日次連番が上限に達しました");
        }
        String refundNo = "F" + DATE_FORMAT.format(cancelDate) + "%04d".formatted(sequence);
        LocalDateTime registeredAt = LocalDateTime.now();
        Refund refund = new Refund(
            refundNo,
            reserveNo,
            refundAmount,
            cancelFee,
            RefundStatus.WAITING,
            registeredAt,
            operator,
            registeredAt,
            operator
        );
        refundsByNumber.put(refundNo, refund);
        refundsByReservation.put(reserveNo, refund);
        return refund;
    }

    public synchronized List<Refund> entries() {
        return List.copyOf(refundsByNumber.values());
    }

    @Override
    public synchronized void rollbackRegistration(String reserveNo) {
        Refund removed = refundsByReservation.remove(reserveNo);
        if (removed != null) {
            refundsByNumber.remove(removed.refundNo());
        }
    }
}
