package com.example.infrastructure;

import com.example.domain.PaymentHandoffRepository;

import java.time.LocalDate;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryPaymentHandoffRepository implements PaymentHandoffRepository {

    private final Set<Entry> entries = ConcurrentHashMap.newKeySet();

    @Override
    public void enqueue(String reserveNo, LocalDate paidDate) {
        entries.add(new Entry(reserveNo, paidDate));
    }

    public Set<Entry> entries() {
        return Set.copyOf(entries);
    }

    public record Entry(String reserveNo, LocalDate paidDate) {
    }
}
