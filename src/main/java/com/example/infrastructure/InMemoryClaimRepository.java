package com.example.infrastructure;

import com.example.domain.Claim;
import com.example.domain.ClaimRepository;
import com.example.domain.ClaimStatus;
import com.example.domain.Money;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class InMemoryClaimRepository implements ClaimRepository {
    private final Map<String, Claim> claims = new HashMap<>();
    private final Map<LocalDate, Integer> dailySequences = new HashMap<>();

    @Override
    public synchronized Claim register(
        String reserveNo, LocalDate cancelDate, Money claimAmount, Money cancelFee, Money paidAmount, String operator
    ) {
        if (claims.containsKey(reserveNo)) {
            throw new IllegalStateException("予約 " + reserveNo + " の請求待ちは登録済みです");
        }
        int sequence = dailySequences.merge(cancelDate, 1, Integer::sum);
        if (sequence > 9999) {
            dailySequences.put(cancelDate, 9999);
            throw new IllegalStateException("請求番号の日次連番が上限に達しました");
        }
        String claimNo = "C" + DateTimeFormatter.BASIC_ISO_DATE.format(cancelDate) + "%04d".formatted(sequence);
        LocalDateTime now = LocalDateTime.now();
        Claim claim = new Claim(claimNo, reserveNo, claimAmount, cancelFee, paidAmount, ClaimStatus.WAITING,
            now, operator, now, operator);
        claims.put(reserveNo, claim);
        return claim;
    }

    public synchronized List<Claim> entries() {
        return List.copyOf(claims.values());
    }

    @Override
    public synchronized void rollbackRegistration(String reserveNo) {
        claims.remove(reserveNo);
    }
}
