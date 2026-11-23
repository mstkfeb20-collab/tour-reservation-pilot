package com.example.infrastructure;

import com.example.domain.Money;
import com.example.domain.PaymentAuditRepository;

import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryPaymentAuditRepository implements PaymentAuditRepository {

    private final Set<Entry> entries = ConcurrentHashMap.newKeySet();

    @Override
    public void record(String operator, String inquiryNo, Money amount) {
        entries.add(new Entry(operator, inquiryNo, amount));
    }

    public List<Entry> entries() {
        return List.copyOf(entries);
    }

    public record Entry(String operator, String inquiryNo, Money amount) {
    }
}
