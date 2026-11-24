package com.example.infrastructure;

import com.example.domain.CancellationAudit;
import com.example.domain.CancellationAuditRepository;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

public class InMemoryCancellationAuditRepository implements CancellationAuditRepository {

    private final List<CancellationAudit> entries = new CopyOnWriteArrayList<>();

    @Override
    public void record(CancellationAudit entry) {
        entries.add(entry);
    }

    @Override
    public void remove(CancellationAudit entry) {
        entries.remove(entry);
    }

    public List<CancellationAudit> entries() {
        return List.copyOf(entries);
    }
}
